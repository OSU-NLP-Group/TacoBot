from concurrent.futures import ThreadPoolExecutor, wait, as_completed
from datetime import datetime

from .taco_logger import LoggerFactory
from .taco_state_manager import StateManager
from injector import inject
from typing import List

from .taco_service_module_manager import ServiceModuleManager

class CallModules(object):
    """
         Base class to create modules by looking up module names in ServiceModules.py and run each module in parallel.
    """
    @inject
    def __init__(self,
                 service_module_manager: ServiceModuleManager,
                 state_manager: StateManager,
                 save_mode=True):
        """
        Constructor
        :param state_manager: state manager
        :param module_config_key: module config key in the service_module_config.py
        :param save_mode: whether to save the result to state manager, by default it's set to True
        """
        self.service_module_manager = service_module_manager
        self.state_manager = state_manager
        self.save_mode = save_mode

        self.logger = LoggerFactory.setup(self)

    def run(self, module_names: List[str], save_mode: bool):
        start = datetime.now()
        module_classes = self.service_module_manager.get_module_classes(module_names)
        self.logger.info('Starting CallModules')
        result = self.execute(module_classes, save_mode)
        end = datetime.now()
        self.logger.info("Finished CallModules, latency: {}ms, result: {}".format((end - start).total_seconds() * 1000,
                                                                       result if result is not None else 'None'))
        return result

    def execute(self, module_classes, save_mode):
        raise NotImplementedError('Not Implemented')


def run_module(module, save_mode):
    if save_mode:
        task = module.execute_and_save()
    else:
        task = module.execute()
    return task


class CallModulesWithThreadPool(CallModules):
    """
         Extended class to call many modules in parallel using concurrent.futures.ThreadPoolExecutor.
    """
    def execute(self, module_classes, save_mode):
        with ThreadPoolExecutor() as executor:
            result = {}
            future_to_module_name = {executor.submit(run_module, module, save_mode): module.module_name for module
                                     in module_classes}

            for future in as_completed(future_to_module_name):
                module_name = future_to_module_name[future]
                try:
                    future_result = future.result()
                    result[module_name] = future_result
                except Exception:
                    self.logger.error("Exception when running task {}".format(module_name), exc_info=True)
            return result


class NLPPipeline():
    @inject
    def __init__(self,
                 service_module_manager: ServiceModuleManager,
                 call_modules: CallModulesWithThreadPool,
                 save_mode=True):
        self.service_module_manager = service_module_manager
        self.call_modules = call_modules
        self.save_mode = save_mode

    def run(self):
        for step in self.service_module_manager.nlp:
            self.call_modules.run(step, self.save_mode)


class ResponseGeneratorsRunner():
    @inject
    def __init__(self,
                 service_module_manager: ServiceModuleManager,
                 call_modules: CallModulesWithThreadPool,
                 save_mode=True):
        self.service_module_manager = service_module_manager
        self.call_modules = call_modules
        self.save_mode = save_mode

    def run(self, module_names=None):
        if module_names is None:
            module_names = self.service_module_manager.response_generator_names
        return self.call_modules.run(module_names, self.save_mode)



