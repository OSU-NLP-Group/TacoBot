from injector import singleton, inject
from typing import List, Dict, Any
from .taco_logger import LoggerFactory
from .taco_service_module_config import ServiceModuleConfig
from .taco_state_manager import StateManager


@singleton
class ServiceModuleManager(object):
    """
        Class to manage service modules by add/update/get each module and
        manage nlp pipeline creation.
    """

    @inject
    def __init__(self,
                 state_manager: StateManager):
        self.state_manager = state_manager
        self.modules = dict()
        self.response_generator_names = set()
        self.nlp = [[]]
        self.nlp_flattened = set()
        self.logger = LoggerFactory.setup(self)

    # initialize module class
    def get_module(self, module_name) -> object:
        if module_name in self.modules.keys():
            service_module_config = self.modules.get(module_name)
            module_class= self.modules.get(module_name).clazz(self.state_manager, module_name, service_module_config)
            return module_class
        else:
            self.logger.error("Module not found in map: %s", module_name)

    def module_exist(self, module_name=str) -> bool:
        return module_name in self.modules.keys()

    def upsert_module(self, module=Dict):
        self.modules[module['name']] = ServiceModuleConfig(module)

    def add_response_generator_module(self, module=Dict[str, Any]):
        self.upsert_module(module)
        self.response_generator_names.add(module['name'])

    def get_response_generator_classes(self) -> List[object]:
        return self.get_module_classes(list(self.response_generator_names))

    def get_module_classes(self, module_names: List[str]) -> List[object]:
        result = []
        for module_name in module_names:
            try:
                new_module = self.get_module(module_name)
                result.append(new_module)
            except:
                self.logger.error('Exception when creating {} module'.format(module_name), exc_info=True)
        return result

    def create_nlp_pipeline(self, nlp_def: List[List[str]]):
        for step_modules in nlp_def:
            for module_name in step_modules:
                if not self.module_exist(module_name):
                    raise Exception("Module not found in map: ", module_name)
                self.nlp_flattened.add(module_name)
        self.nlp = nlp_def
        self.logger.info('NLP pipeline: %s', self.nlp_flattened)

    def get_nlp_pipeline_names(self):
        return self.nlp_flattened
