import json
import logging
import os
import threading
from concurrent import futures
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime
import time

import yaml
import os

from tacobot import config
from tacobot.state_manager import StateManager
from typing import List, Dict, Any, Optional, Set

import requests

from tacobot.utils import killable

logger = logging.getLogger('tacologger')


with open(os.path.join("model_serving", "model_config.yaml"), "r") as f:
    model_config = yaml.safe_load(f)


def get_url(name):
    # config file should store the urls
    container_url = model_config["annotators"]["url"]
    port = model_config["annotators"]["ports"][name]
    url = ":".join([container_url, port])
    # url = "http://192.168.0.2:5001/"
    logger.debug(f"For callable: {name} got remote url: {url}")
    return url


class ModelManager:
    def __init__(self,
                 url: str, timeout: float = config.inf_timeout, name: str = None):
        self.url = url
        self.timeout = timeout
        self.name = name
        self.thread = threading.currentThread()
        self.killable = getattr(self.thread, "killable", False)
        if self.killable:
            logger.info(f"RemoteCallable {self.name} running in a killable thread.")

    @killable
    def __serve__(self, input_data):
        start = datetime.now()
        logger.info("Executing: %s", self.name)
        logger.info("url: %s, data: %s", self.url, json.dumps(input_data))

        # response = requests.post(self.url,
        #                          json=input_data,
        #                          headers={'content-type': 'application/json'},
        #                          timeout=self.timeout / 1000.0)
        response = requests.post(self.url,
                                 json=input_data,
                                 headers={'content-type': 'application/json'})


        end = datetime.now()
        logger.info("Finished: {}, result: {}, latency: {}ms".format(self.name, response.json(),
                                                                     (end - start).total_seconds() * 1000))
        return response.json()


class Annotator(ModelManager):
    def __init__(self, state_manager: StateManager, timeout: float, url: str = None,
                 input_annotations: List[str] = [], name: str = None):
        self.name = name
        if url is None:
            url = get_url(self.name)
        super().__init__(url=url, timeout=timeout, name=name)
        self.state_manager = state_manager
        self.input_annotations = input_annotations

    def save_to_state(self, value):
        setattr(self.state_manager.current_state, self.name, value)

    def remote_call(self, *args, **kwargs):
        return super().__serve__(*args, **kwargs)

    def default_fn(self, input_data):
        return self.get_default_response(input_data)

    def execute(self, input_data):
        raise NotImplementedError

    def get_default_response(self, input_data):
        raise NotImplementedError


def run_anotators_multithreaded(annotator: List[Annotator],
                                function_name: str,
                                timeout: Optional[float] = None,
                                args_list: Optional[List[List]] = None,
                                kwargs_list: Optional[List[Dict]] = None):
    max_workers = len(annotator)
    if max_workers == 0:
        return {}
    logger.debug(f'Initializing ThreadPoolExecutor with max_workers={max_workers}')
    executor = ThreadPoolExecutor(max_workers=max_workers)
    result = {}
    args_list = args_list or [[] for _ in annotator]
    kwargs_list = kwargs_list or [{} for _ in annotator]

    # List of modules names which have some response (includes default responses)
    succeeded_modules = set()

    # Set of module names which have completely failed
    failed_modules = set()

    # Dictionary from module instances to argument list
    module_2_args = {annotator: (args_list, kwargs_list) for annotator, args_list, kwargs_list in
                     zip(annotator, args_list, kwargs_list)}

    # Initialize list of unexecuted module instances with all the modules
    unexecuted_annotators = list(module_2_args.keys())

    # Dictionary from future to module name, initialized to be empty
    future_to_module = {}
    begin_time = time.perf_counter_ns()
    while unexecuted_annotators or future_to_module:
        # Get modules that can be executed
        executable_modules, unexecuted_annotators, failed_modules = \
            get_ready_callables(succeeded_modules, failed_modules, unexecuted_annotators)

        # Schedule executable modules to run
        future_to_module.update({executor.submit(run_model, module, function_name,
                                                 module_2_args[module][0],
                                                 module_2_args[module][1]): module
                                 for module in executable_modules})

        time_elapsed = ((time.perf_counter_ns() - begin_time) / 1000000000)
        next_timeout = timeout and timeout - time_elapsed

        remaining_modules = set([m.name for m in future_to_module.values()])
        logging.info(f"Remaining modules: {remaining_modules}")

        # If there is no time remaining, get default response for all remaining modules and break out of the loop
        if next_timeout <= 0:
            logger.error(f"NLP pipeline hit overall timeout in {time_elapsed} "
                         f"seconds. ")

            for module in unexecuted_annotators + list(future_to_module.values()):
                try:
                    default_response = module.get_default_response()
                    result[module.name] = default_response
                    # Add the result to state_manager so that it can be used by subsequent annotators
                    module.save_to_state(default_response)
                    logger.info(f"Using default response for {module.name}: {result[module.name]}")
                    succeeded_modules.add(module.name)
                except:
                    logger.error(f"ServiceModule encountered an error when running {module.name}'s "
                                 f"get_default_response function", exc_info=True)
                    failed_modules.add(module.name)

            # Cancel futures in case they happen to have not been scheduled
            for future in future_to_module:
                future.cancel()

            break

        # Wait till the first future is complete, it'll come as done. If timeout is hit, done is empty
        done, not_done = futures.wait(future_to_module, timeout=next_timeout, return_when=futures.FIRST_COMPLETED)

        for future in done:
            # Get the module name and remove it from the list of futures we will wait on in the future
            module = future_to_module.pop(future)
            annotator_name = module.name

            try:
                future_result = future.result()
                result[annotator_name] = future_result
                # Add the result to state_manager so that it can be used by subsequent annotators
                module.save_to_state(future_result)

                print(f"Succesfully executed {annotator_name}")

                logger.info(f"Succesfully executed {annotator_name}")
                succeeded_modules.add(annotator_name)
            except Exception:
                logger.warning(f"Failed to execute {annotator_name}", exc_info=True)
                failed_modules.add(annotator_name)

        # set of succeeded and failed modules have been updated.
        # Repeat the loop and re-evaulate which un-executed modules can be scheduled next
    logger.info("CallModules summary: \n" +
                (f"MODULES WITH SOME RESPONSE: {', '.join(succeeded_modules)}\n"
                 if succeeded_modules else '') +
                (f"FAILED MODULES: {', '.join(failed_modules)}"
                 if failed_modules else ''))

    return result


class ResponseGenerator:
    def __init__(self,  state_manager: StateManager, rg_classes):
        self.name_to_class = {rg_class.name: rg_class for rg_class in rg_classes}
        self.state_manager = state_manager


def get_ready_callables(succeeded_modules: Set[str], failed_modules: Set[str], unexecuted_modules: List[Annotator]):
    """ Get unexecuted modules which can be executed, based on whether their requirements are satisfied.
        If their requirements have failed, then add them to failed modules as well.

    Args:
        succeeded_modules (Set[str]): Set of modules names which have successfully completed
        failed_modules (Set[str]): Set of module names which have failed (errored out or timed out)
        unexecuted_modules (List[Module]: List of modules yet to be executed

    Returns:
        executable_modules (List[Module]): Modules whose requirements are met and are ready to be executed
        unexecutable_modules (List[Module]): Modules whose requirements are unmet but might be met in the future
        failed_modules (Set[string]): Module names for modules which have failed by themselves
                                        or because their requirements have failed

    """
    executable_modules = []
    unexecutable_modules = []
    for module in unexecuted_modules:
        requirements = module.input_annotations
        if len(set(requirements) - succeeded_modules) == 0:
            executable_modules.append(module)
            logger.info(f"Ready to execute {module.name} as its module requirements = {requirements} are satisfied")
        elif len(set(requirements) - (succeeded_modules | failed_modules)) == 0:
            failed_modules.add(module.name)
            logger.info(f"Failed to execute {module.name} as its module requirements "
                        f"{failed_modules & set(requirements)} also failed to execute")
        else:
            unexecutable_modules.append(module)
    return executable_modules, unexecutable_modules, failed_modules


def run_model(module, function_name, args: List = [], kwargs: Dict = {}):
    task = getattr(module, function_name)(*args, **kwargs)
    return task


def initialize_model(module_class, args: List = [], kwargs: Dict = {}):
    initialized_module = module_class(*args, **kwargs)
    return initialized_module
