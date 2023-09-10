import logging

from taco.core.response_generator import *
from taco.response_generators.aliens.state import State, ConditionalState
from taco.response_generators.aliens.aliens_responses import MONOLOGUES
from taco.core.response_generator_datatypes import ResponsePriority

from taco.core.response_generator_datatypes import ResponseGeneratorResult, AnswerType
logger = logging.getLogger('tacologger')


class FirstTurnTreelet(Treelet):
    name = "aliens_first_turn"

    def get_response(self, priority=ResponsePriority.STRONG_CONTINUE, **kwargs):
        state, utterance, response_types = self.get_state_utterance_response_types()
        response = MONOLOGUES[1]
        conditional_state = ConditionalState(prev_treelet_str=self.name,
                                             next_treelet_str=self.rg.second_turn_treelet.name)
        return ResponseGeneratorResult(text=response, priority=priority, needs_prompt=False, state=state,
                                       cur_entity=None, conditional_state=conditional_state,
                                       answer_type=AnswerType.STATEMENT)
