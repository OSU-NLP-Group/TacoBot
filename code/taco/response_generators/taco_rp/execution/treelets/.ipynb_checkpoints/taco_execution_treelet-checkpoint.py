import logging
from taco.core.regex.regex_template import RegexTemplate
from taco.response_generators.food.regex_templates import DoubtfulTemplate
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.core.entity_linker.entity_groups import EntityGroupsForExpectedType
from taco.core.util import infl
from cobot_core.service_module import ToolkitServiceModule
from cobot_core.service_module import LocalServiceModule

from ask_sdk_model.services.service_exception import ServiceException
from cobot_core.alexa_list_management import AlexaListManagement
from taco.response_generators.taco_rp.taco_intent_by_rule import TacoIntentByRule
from taco.response_generators.taco_rp.choice.treelets.utils.general import get_and_list_prompt
import json

import random

from cobot_core.service_module import LocalServiceModule
from taco.response_generators.taco_rp.execution.treelets.taco_recipe_show_steps import taco_recipe_show_steps
from taco.response_generators.taco_rp.execution.treelets.taco_wikihow_details import taco_wikihow_details, taco_wikihow_tips
from taco.response_generators.taco_rp.execution.treelets.taco_wikihow_show_steps import taco_wikihow_show_steps
from taco.response_generators.taco_rp.execution.treelets.template_manager import DETAIL_TIP_TEMPLATES

from taco.response_generators.taco_rp.execution.state import State, ConditionalState

logger = logging.getLogger('tacologger')


def get_taco_execution_response(current_state, last_state, user_attributes):
    is_wikihow = getattr(user_attributes, 'is_wikihow', None)

    if is_wikihow:
        return taco_wikihow_show_steps(current_state, last_state, user_attributes)
    else:
        return taco_recipe_show_steps(current_state, last_state, user_attributes)


def get_taco_details_response(current_state, last_state, user_attributes):
    is_wikihow = getattr(user_attributes, 'is_wikihow', None)

    if is_wikihow:
        return taco_wikihow_details(current_state, last_state, user_attributes)
    else:
        return {'response': random.choice(DETAIL_TIP_TEMPLATES['recipe']), 
            'shouldEndSession': False}


def get_taco_tips_response(current_state, last_state, user_attributes):
    is_wikihow = getattr(user_attributes, 'is_wikihow', None)

    if is_wikihow:
        return taco_wikihow_tips(current_state, last_state, user_attributes)
    else:
        return {'response': random.choice(DETAIL_TIP_TEMPLATES['recipe']),
            'shouldEndSession': False}


def select_execution_response(current_state, last_state, user_attributes):
    intent = getattr(current_state, 'final_intent', '')
    is_wikihow = getattr(user_attributes, 'is_wikihow', False)
    taco_state = getattr(user_attributes, 'taco_state', None)

    
    
    if intent == 'DetailRequestIntent' and not is_wikihow: 
        return {'response': random.choice(DETAIL_TIP_TEMPLATES['recipe']),
            'shouldEndSession': False}
    elif 'tipNo' in taco_state or True:                  # modify here
        return get_taco_tips_response(current_state, last_state, user_attributes)
    elif current_state.final_intent != None and 'Detail' in current_state.final_intent or 'Detail' in taco_state:
        return get_taco_details_response(current_state, last_state, user_attributes)
    elif 'Instruction' in taco_state:
        return get_taco_execution_response(current_state, last_state, user_attributes) 



class Taco_execution_Treelet(Treelet):
    name = "Taco_execution_Treelet"
    

    def classify_user_response(self):
        assert False, "This should never be called."


    def get_response(self, state_manager, priority=ResponsePriority.WEAK_CONTINUE, **kwargs) -> ResponseGeneratorResult:
        """ Returns the response. """
        
        state, utterance, response_types = self.get_state_utterance_response_types()

        current_state = state_manager.current_state
        last_state = state_manager.last_state
        user_attributes = state_manager.user_attributes
        
        response_state = select_execution_response(
            current_state, 
            last_state, 
            user_attributes
        )
        
        response = response_state['response']

        return ResponseGeneratorResult(text=response, priority=priority,
                                       needs_prompt=False, state=state, cur_entity=None,
                                       conditional_state=ConditionalState(
                                           prompt_treelet=self.name,))

    def get_best_candidate_user_entity(self, utterance, cur_food):
        def condition_fn(entity_linker_result, linked_span, entity):
            return EntityGroupsForExpectedType.food_related.matches(entity) and entity.name != cur_food
        entity = self.rg.state_manager.current_state.entity_linker.top_ent(condition_fn) or self.rg.state_manager.current_state.entity_linker.top_ent()
        if entity is not None:
            user_answer = entity.talkable_name
            plural = entity.is_plural
        else:
            nouns = self.rg.state_manager.current_state.corenlp['nouns']
            if len(nouns):
                user_answer = nouns[-1]
                plural = True
            else:
                user_answer = utterance.replace('i like', '').replace('my favorite', '').replace('i love', '')
                plural = True

        return user_answer, plural

