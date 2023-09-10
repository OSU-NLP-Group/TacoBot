import logging
import json
import random

from taco.core.regex.regex_template import RegexTemplate
from taco.response_generators.food.regex_templates import DoubtfulTemplate
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.core.entity_linker.entity_groups import EntityGroupsForExpectedType
from taco.core.util import infl

from taco.response_generators.taco_rp.welcome.treelets import template_manager
from taco.response_generators.taco_rp import apl

from taco.response_generators.taco_rp.welcome.state import State, ConditionalState

logger = logging.getLogger('tacologger')


CONTINUE_INTENTS = ['LaunchRequestIntent']
RESTART_INTENTS  = ['AcknowledgeIntent', 'NegativeAcknowledgeIntent', 'CancelIntent', 'GoBackIntent', 'GOBACKMAINTASKINENT']


class WELCOME_Treelet(Treelet):

    def __init__(self, rg):
        super().__init__(rg)
        self.name = 'welcome_Treelet'

        self.cache = json.load(open('./taco/response_generators/taco_rp/welcome/data/example_cache.json'))   

        self.pre_task   = None
        self.pre_recipe = None

    def classify_user_response(self):
        assert False, "This should never be called."


    def get_response(self, state_manager, priority=ResponsePriority.STRONG_CONTINUE, **kwargs) -> ResponseGeneratorResult:
        """ Returns the response. """
        state, utterance, response_types = self.get_state_utterance_response_types()
        parsed_intent = state_manager.current_state.parsed_intent

        logger.taco_merge(f'parsed_intent = {parsed_intent} {parsed_intent in CONTINUE_INTENTS}')
        # input()

        speak_out = None
        task = None
        recipe = None

        if parsed_intent in CONTINUE_INTENTS:
            speak_out, task, recipe = template_manager.select_template()
        elif parsed_intent in RESTART_INTENTS:
            speak_out, task, recipe = template_manager.select_template(revisited=True)
        else:
            logger.taco_merge("Intent was not valid. [parsed_intent: %s]", parsed_intent)
            speak_out = f'parsed_intent = {parsed_intent}'
            priority =  ResponsePriority.NO
        

        task_img_url = self._get_cached_url(task=task)
        recipe_img_url = self._get_cached_url(recipe=recipe)

        # directives = [build_directive(task, task_img_url, recipe, recipe_img_url)]
        # setattr(state_manager.user_attributes, 'welcome_task', task.lower()) 
        # setattr(state_manager.user_attributes, 'welcome_recipe', recipe.lower()) 

        return ResponseGeneratorResult(text=speak_out, priority=priority,
                                       needs_prompt=False, state=state, cur_entity=None,
                                       conditional_state=ConditionalState(
                                           prev_treelet_str=self.name,
                                           sampled_task = task,
                                           sampled_recipe = recipe))
        
    def _get_cached_url(self, *, task=None, recipe=None):
        if task is not None:
            key = task
            cache = self.cache['welcome_tasks']
        elif recipe is not None:
            key = recipe
            cache = self.cache['welcome_recipes']
        else:
            # self.logger.warning("Didn't request a task or a recipe.")
            return apl.Urls.default_task_image

        if key not in cache:
            # self.logger.warning(
            #     "Key not in image cache. [key: '%s', cache: '%s']",
            #     key,
            #     ", ".join(cache.keys()),
            # )
            return apl.Urls.default_task_image

        return cache[key]
    
    def treet_update_current_state(self, state_manager, conditional_state):
        assert state_manager is not None, "state_manager should not be None for updating the current state"
        assert conditional_state is not None, "conditional_state should not be None if the response/prompt was chosen"
        self.restart(state_manager.user_attributes)
        # input()
        setattr(state_manager.user_attributes, 'welcome_task', conditional_state.sampled_task.lower()) 
        setattr(state_manager.user_attributes, 'welcome_recipe', conditional_state.sampled_recipe.lower()) 


    def restart(self, user_attributes):
        setattr(user_attributes, 'current_step_details', None)
        setattr(user_attributes, 'query', '')
        setattr(user_attributes, 'query_result', None)
        setattr(user_attributes, 'use_evi', False)
        setattr(user_attributes, 'choice_start_idx', 0)
        setattr(user_attributes, 'cont_reqs', 0)
        setattr(user_attributes, 'current_task', None)
        setattr(user_attributes, 'list_item_selected', -1)
        setattr(user_attributes, 'list_item_rec', -1)
        setattr(user_attributes, 'current_step', None)
        setattr(user_attributes, 'started_cooking', None)
        setattr(user_attributes, 'task_started', False)
        setattr(user_attributes, 'wikihow_summary', '')

