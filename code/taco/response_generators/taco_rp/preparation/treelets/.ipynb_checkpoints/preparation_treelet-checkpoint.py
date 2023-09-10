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

from taco.response_generators.taco_rp.preparation.state import State, ConditionalState


logger = logging.getLogger('tacologger')


def get_taco_preparation_response(current_state, last_state, user_attributes):
    is_wikihow = getattr(user_attributes, 'is_wikihow', False)

    if is_wikihow:
        return taco_wikihow_preparation(current_state, last_state, user_attributes)
    else:
        return taco_recipe_preparation(current_state, last_state, user_attributes)


def select_prep_response(current_state, last_state, user_attributes):
#     20220928 modify
    current_state.final_intent = ''
    if current_state.final_intent == 'ReadIngredientIntent' or True:
        response = "The ingredients are: " + getattr(user_attributes, 'current_task_ingredients', '')
        if 'Prep' in user_attributes.taco_state or True:
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


    def get_response(self, state_manager, priority=ResponsePriority.WEAK_CONTINUE, **kwargs) -> ResponseGeneratorResult:
        """ Returns the response. """
        state, utterance, response_types = self.get_state_utterance_response_types()
        
        current_state = state_manager.current_state
        last_state = state_manager.last_state
        user_attributes = state_manager.user_attributes
        
        
        response_state = select_prep_response(current_state, last_state, user_attributes)
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

