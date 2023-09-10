import logging
import json
import re
import random

from taco.core.regex.regex_template import RegexTemplate
from taco.response_generators.food.regex_templates import DoubtfulTemplate
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.core.entity_linker.entity_groups import EntityGroupsForExpectedType
from taco.core.util import infl

from taco.response_generators.taco_rp.welcome.state import State, ConditionalState
from taco.response_generators.taco_rp.utils.state import *

logger = logging.getLogger('tacologger')


class TacoRepeat(Treelet):
    """
    If the user has an ongoing task, ask if they want to continue or complete it.
    Otherwise, share suggestions for what the user should try.
    """

    name = "TacoRepeat_Treelet"

    def classify_user_response(self):
        assert False, "This should never be called."


    def get_response(self, state_manager, priority=ResponsePriority.CAN_START, **kwargs) -> ResponseGeneratorResult:
        state, utterance, response_types = self.get_state_utterance_response_types()
        last_state_dict = state_manager.last_state

        print('last_state_dict = ', last_state_dict)
        last_response = ''
        if last_state_dict:
            last_response = getattr(last_state_dict, 'response', None)
        else:
            # Use StateTable as backup. NOTE It may be erroneous!
            last_response = (
                state_manager.last_state.get("response", None) if state_manager.last_state is not None else ""
            )
        last_response = re.sub(r"&amp;", ' and ', last_response)
        last_response = re.sub("&quot;", '"', last_response)
        last_response = re.sub("&apos;", "'", last_response)
        # last_response = re.sub(r'<.*?>', '', last_response)
        # Repeat slowly
        return ResponseGeneratorResult(text=last_response, priority=priority,
                                       needs_prompt=False, state=state, cur_entity=None,
                                       conditional_state=ConditionalState(
                                           prompt_treelet=self.name,))
