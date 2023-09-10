import logging
from taco.core.regex.regex_template import RegexTemplate
from taco.response_generators.food.regex_templates import DoubtfulTemplate
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.core.entity_linker.entity_groups import EntityGroupsForExpectedType
from taco.core.util import infl

from taco.response_generators.taco_rp.preparation.treelets.taco_recipe_preparation import taco_recipe_preparation
from taco.response_generators.taco_rp.preparation.treelets.taco_wikihow_preparation import taco_wikihow_preparation
from taco.response_generators.taco_rp.preparation.treelets import template_manager

import random

from taco.core.state import State as Cur_State
from taco.core.user_attributes import UserAttributes as Cur_UserAttributes
from taco.response_generators.taco_rp.preparation.state import State, ConditionalState
from fuzzywuzzy import fuzz

import json

f = open('taco/data/people_also_ask_data.json')
people_also_ask_data = json.load(f)


logger = logging.getLogger('tacologger')


def get_taco_preparation_response(current_state, last_state, user_attributes):
    is_wikihow = getattr(user_attributes, 'is_wikihow', False)

    if is_wikihow:
        return taco_wikihow_preparation(current_state, last_state, user_attributes)
    else:
        return taco_recipe_preparation(current_state, last_state, user_attributes)


def select_prep_response(current_state, last_state, user_attributes):
    if current_state.parsed_intent == 'ReadIngredientIntent':
        response = "The ingredients are: " + getattr(user_attributes, 'current_task_ingredients', '')
        if 'Prep' in current_state.status:
            response += (
                random.choice(template_manager.RECIPE_PREP_TEMPLATES['add']) +
                random.choice(template_manager.RECIPE_PREP_TEMPLATES['start']).substitute(start_question=random.choice(template_manager.START_QUESTION))
            )

        return {
            'response': response,
            'shouldEndSession': False
        }
    else:
        return get_taco_preparation_response(current_state, last_state, user_attributes)


class Taco_Prepration_Treelet(Treelet):
    name = "Taco_Prepration_Treelet"
    
    def classify_user_response(self):
        assert False, "This should never be called."


    def get_response(self, state_manager, priority=ResponsePriority.STRONG_CONTINUE, **kwargs) -> ResponseGeneratorResult:
        """ Returns the response. """
        state, utterance, response_types = self.get_state_utterance_response_types()
        
        current_state = state_manager.current_state
        last_state = state_manager.last_state
        user_attributes = state_manager.user_attributes
        
        
        n_current_state = Cur_State.deserialize(current_state.serialize(logger_print=False))
        n_user_attributes = Cur_UserAttributes.deserialize(user_attributes.serialize(logger_print=False))

        response_state = select_prep_response(n_current_state, last_state, n_user_attributes)
        response = response_state['response']
        
        return ResponseGeneratorResult(text=response, priority=priority,
                                       needs_prompt=False, state=state, cur_entity=None,
                                       conditional_state=ConditionalState(
                                           prev_treelet_str=self.name,
                                           n_current_state=n_current_state,
                                           n_user_attributes=n_user_attributes
                                           ))

    def treet_update_current_state(self, state_manager, conditional_state):
        assert state_manager is not None, "state_manager should not be None for updating the current state"
        assert conditional_state is not None, "conditional_state should not be None if the response/prompt was chosen"

        logger.taco_merge(f'choice treet_update_current_state and user_attributes')

        # user_attributes
        for k in ['card_sent', 'current_step_speak', 'all_total_steps', 'has_parts', 'total_steps', 'current_task', 
            'list_item_selected', 'current_step_details', 'current_task_ingredients', 'people_also_ask_question']:
            v = getattr(conditional_state.n_user_attributes, k, None)
            if v != None:
                setattr(state_manager.user_attributes, k, v)

        conditional_state.n_current_state = None
        conditional_state.n_user_attributes = None