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

from cobot_core.service_module import LocalServiceModule, ToolkitServiceModule

from taco.response_generators.taco_rp.choice.treelets import template_manager
from taco.response_generators.taco_rp.choice.treelets.taco_choice_compare import taco_recipe_compare, taco_wikihow_compare
from taco.response_generators.taco_rp.choice.treelets.taco_data_manager import manage_search_data
from taco.response_generators.taco_rp.choice.treelets.taco_wikihow_choice import taco_wikihow_choice
from taco.response_generators.taco_rp.choice.treelets.taco_recipe_choice import taco_recipe_choice
from taco.response_generators.taco_rp.choice.treelets.utils.general import get_and_list_prompt

from taco.response_generators.taco_rp.choice.state import State, ConditionalState

logger = logging.getLogger('tacologger')

def get_choice_compare_response(current_state, last_state, user_attributes, toolkit_service_client):
    is_wikihow = getattr(user_attributes, 'is_wikihow', None)

    if is_wikihow:
        return taco_wikihow_compare(current_state, last_state, user_attributes, toolkit_service_client)
    else:
        return taco_recipe_compare(current_state, last_state, user_attributes, toolkit_service_client)


def get_choice_catalog_response(current_state, last_state, user_attributes, toolkit_service_client):
    is_wikihow = getattr(user_attributes, 'is_wikihow', None)

    if is_wikihow:
        return taco_wikihow_choice(current_state, last_state, user_attributes, toolkit_service_client)
    else:
        return taco_recipe_choice(current_state, last_state, user_attributes, toolkit_service_client)


def get_clarification_question_response(current_state, last_state, user_attributes, toolkit_service_client):
    query = getattr(user_attributes, 'query', '')
    recipesearch = getattr(current_state, 'recipesearch', None)
    attributes_to_clarify = recipesearch['attributes_to_clarify']
    request_dict = recipesearch['request']
    setattr(user_attributes, 'search_request', request_dict)

    speakout = template_manager.help_with_query(recipe=True, has_query=bool(query)).substitute(query=query)
    if 'diets' in attributes_to_clarify:
        attr_str = get_and_list_prompt(attributes_to_clarify['diets'])
        speakout += 'Do you have any diet constraints? Such as ' + attr_str + '. '
    else:
        attr_str = get_and_list_prompt(attributes_to_clarify['cuisines'])
        speakout += 'Do you have any preference on cuisines? Such as ' + attr_str + '. '
    
    return speakout


def select_choice_response(current_state, last_state, user_attributes, toolkit_service_client):
    intent = getattr(current_state, 'final_intent', None)
    query_result = getattr(user_attributes, 'query_result', None)
    query_result = None


    if intent in ['TaskRequestIntent', 'RecommendIntent', 'UserEvent', 'ClarifyIntent'] or query_result is None:
#         print('manage_search_data')
        manage_search_data(current_state, last_state, user_attributes, toolkit_service_client)
        
    if 'Comparison' in user_attributes.taco_state or True:
        return get_choice_compare_response(current_state, last_state, user_attributes, toolkit_service_client)
    elif 'Catalog' in user_attributes.taco_state:
        return get_choice_catalog_response(current_state, last_state, user_attributes, toolkit_service_client)
    elif 'Clarification' in user_attributes.taco_state:
        return get_clarification_question_response(current_state, last_state, user_attributes, toolkit_service_client)



class Taco_choice_Treelet(Treelet):
    name = "Taco_choice_Treelet"

    def classify_user_response(self):
        assert False, "This should never be called."


    def get_response(self, state_manager, priority=ResponsePriority.WEAK_CONTINUE, **kwargs) -> ResponseGeneratorResult:
        """ Returns the response. """
        
        state, utterance, response_types = self.get_state_utterance_response_types()

        name_ToolkitServiceModule = ToolkitServiceModule
        current_state = state_manager.current_state
        last_state = state_manager.last_state
        user_attributes = state_manager.user_attributes
        toolkit_service_client = name_ToolkitServiceModule.toolkit_service_client
        
        response_state = select_choice_response(
            current_state, 
            last_state, 
            user_attributes, 
            toolkit_service_client
        )
        try:
            response = response_state['response']
        except:
            response = ''
        
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

