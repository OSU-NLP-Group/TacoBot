import logging
from taco.core.regex.regex_template import RegexTemplate
from taco.response_generators.food.regex_templates import DoubtfulTemplate
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.core.entity_linker.entity_groups import EntityGroupsForExpectedType
from taco.core.util import infl
from taco.response_generators.taco_rp.taco_intent_by_rule import TacoIntentByRule
from taco.response_generators.taco_rp.choice.treelets.utils.general import get_and_list_prompt
import json

import random

from taco.response_generators.taco_rp.execution.treelets.taco_recipe_show_steps import taco_recipe_show_steps
from taco.response_generators.taco_rp.execution.treelets.taco_wikihow_details import taco_wikihow_details, taco_wikihow_tips
from taco.response_generators.taco_rp.execution.treelets.taco_wikihow_show_steps import taco_wikihow_show_steps
from taco.response_generators.taco_rp.execution.treelets.template_manager import DETAIL_TIP_TEMPLATES

from taco.core.state import State as Cur_State
from taco.core.user_attributes import UserAttributes as Cur_UserAttributes
from taco.response_generators.taco_rp.execution.state import *


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


def get_people_also_ask(current_state, last_state, user_attributes):
    # is_wikihow = getattr(user_attributes, 'is_wikihow', None)
    starter_question = 'Sure, ' +  user_attributes.PAK_selected_ans + ' '
    return {'response': starter_question, 'shouldEndSession': False}

def select_execution_response(current_state, last_state, user_attributes):
    intent = getattr(current_state, 'parsed_intent', '')
    is_wikihow = getattr(user_attributes, 'is_wikihow', False)
    taco_state = getattr(current_state, 'status', None)
    needs_prompt = False

    if intent == 'DetailRequestIntent' and not is_wikihow: 
        return {'response': random.choice(DETAIL_TIP_TEMPLATES['recipe']),
            'shouldEndSession': False}
    elif 'PAK' in taco_state:
        # test neural responder
        needs_prompt = True
        return get_people_also_ask(current_state, last_state, user_attributes), needs_prompt
    elif 'tipNo' in taco_state:
        return get_taco_tips_response(current_state, last_state, user_attributes), needs_prompt
    elif current_state.parsed_intent != None and 'Detail' in current_state.parsed_intent or 'Detail' in taco_state:
        return get_taco_details_response(current_state, last_state, user_attributes), needs_prompt
    elif 'Instruction' in taco_state: # current status
        current_step_num = getattr(user_attributes, 'current_step_num', 0)
        print('current_step_num = ', current_step_num)
        if current_step_num != None and current_step_num > 0 and random.random() > 0.5:
            needs_prompt = True  # we ask pak question if user interests and we would go to PAK and allows user to chitchat
        return get_taco_execution_response(current_state, last_state, user_attributes), needs_prompt

class Taco_execution_Treelet(Treelet):
    name = "Taco_execution_Treelet"
    

    def classify_user_response(self):
        assert False, "This should never be called."


    def get_response(self, state_manager, priority=ResponsePriority.CAN_START, **kwargs) -> ResponseGeneratorResult:
        """ Returns the response. """
        
        state, utterance, response_types = self.get_state_utterance_response_types()

        current_state = state_manager.current_state
        last_state = state_manager.last_state
        user_attributes = state_manager.user_attributes
        
        n_current_state = Cur_State.deserialize(current_state.serialize(logger_print=False))
        n_user_attributes = Cur_UserAttributes.deserialize(user_attributes.serialize(logger_print=False))
        # print('n_user_attributes = ', n_user_attributes)

        response_state, needs_prompt = select_execution_response(
            n_current_state, 
            last_state, 
            n_user_attributes
        )

        # print('response_state = ', response_state)

        response = response_state['response']

        return ResponseGeneratorResult(text=response, priority=priority,
                                       needs_prompt=needs_prompt, state=state, cur_entity=None,
                                       conditional_state=ConditionalState(
                                           prev_treelet_str=self.name,
                                           n_current_state=n_current_state,
                                           n_user_attributes=n_user_attributes))



    def get_prompt(self, state: State, for_launch: bool = False) -> Optional[PromptResult]:
        """
        If this treelet has a starter question, returns a prompt asking the starter question.
        Otherwise, returns None.

        If for_launch, will give version of starter question that's appropriate for launch sequence.
        """
        starter_question, starter_question_labels, priority = self.get_starter_question_and_labels(state, for_response=False, for_launch=for_launch)
        if starter_question is None:
            return None
        conditional_state = ConditionalState(self.name, self.name, '', [], starter_question, starter_question_labels)
        return PromptResult(text=starter_question, prompt_type=priority, state=state, cur_entity=None,
                            conditional_state=conditional_state, expected_type=self.starter_question_expected_type,
                            answer_type=AnswerType.QUESTION_HANDOFF if self.is_handoff else AnswerType.QUESTION_SELFHANDLING)



    def treet_update_current_state(self, state_manager, conditional_state):
        assert state_manager is not None, "state_manager should not be None for updating the current state"
        assert conditional_state is not None, "conditional_state should not be None if the response/prompt was chosen"

        # user_attributes
        for k in ['confirmed_complete', 'current_step_num', 'task_started', 'has_prompted_commands', 'has_prompted_details', 'has_prompted_repeat', 'has_prompted_timer',
            'current_step', 'resume_task', 'current_step_num', 'current_step_details'
        ]:
            v = getattr(conditional_state.n_user_attributes, k, None)
            if v != None:
                setattr(state_manager.user_attributes, k, v)


        conditional_state.n_current_state = None
        conditional_state.n_user_attributes = None