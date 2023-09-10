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

from taco.response_generators.taco_rp.halt.treelets.taco_intent_by_rule import TacoIntentByRule
from taco.response_generators.taco_rp.halt.treelets import template_manager

from taco.response_generators.taco_rp.halt.state import State, ConditionalState


def execute(current_state, user_attributes):
    _, _, total_steps, current_step_num = TacoIntentByRule.parse_step_nums(current_state.status)
    confirmed_complete = user_attributes.confirmed_complete
    if (not confirmed_complete) and (current_step_num < total_steps - 1):
        setattr(user_attributes, 'confirmed_complete', True)
        return {
            'response': 'I think we are not at the last step of this task. ' +
            'If you want to end here, say complete. ' +
            'If you want to continue, say next. ',
            'shouldEndSession': False,
        }

    restart(user_attributes)
    utterance = template_manager.utterance()

    return {
        'response': utterance,
        'shouldEndSession': True
    }


def restart(user_attributes):
    setattr(user_attributes, 'current_step_details', []) 
    setattr(user_attributes, 'query', '')
    setattr(user_attributes, 'use_evi', False)
    setattr(user_attributes, 'choice_start_idx', 0)
    setattr(user_attributes, 'started_cooking', None)


logger = logging.getLogger('tacologger')


class Taco_halt_Treelet(Treelet):
    name = "Taco_halt_Treelet"
    

    def classify_user_response(self):
        assert False, "This should never be called."


    def get_response(self, state_manager, priority=ResponsePriority.CAN_START, **kwargs) -> ResponseGeneratorResult:
        """ Returns the response. """
        state, utterance, response_types = self.get_state_utterance_response_types()
        
        response_state = execute(state_manager.current_state, state_manager.user_attributes)
        response = response_state['response']

        return ResponseGeneratorResult(text=response, priority=priority,
                                       needs_prompt=False, state=state, cur_entity=None,
                                       should_end_session=True,
                                       conditional_state=ConditionalState(
                                           prev_treelet_str=self.name,
                                           ))
