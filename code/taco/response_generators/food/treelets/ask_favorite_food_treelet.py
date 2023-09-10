import logging
from taco.core.regex.regex_template import RegexTemplate
from taco.core.regex.util import OPTIONAL_TEXT, NONEMPTY_TEXT, OPTIONAL_TEXT_PRE, OPTIONAL_TEXT_POST, \
    OPTIONAL_TEXT_MID
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, emptyResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.response_generators.food.food_helpers import *
from taco.response_generators.food.state import State, ConditionalState

import inflect
engine = inflect.engine()

logger = logging.getLogger('tacologger')


class AskFavoriteFoodTreelet(Treelet):
    name = "ask_favorite_food_treelet"

    def get_response(self, priority=ResponsePriority.STRONG_CONTINUE, **kwargs):
        """ Returns the response.
        :param **kwargs:
        """
        return ResponseGeneratorResult(text="Sure! What's your favorite food?", priority=ResponsePriority.CAN_START,
                                       needs_prompt=False, state=State(),
                                       cur_entity=None,
                                       answer_type=AnswerType.QUESTION_SELFHANDLING,
                                       conditional_state=ConditionalState(
                                           next_treelet_str="food_introductory_treelet",
                                           cur_food=None),
                                       expected_type=ENTITY_GROUPS_FOR_EXPECTED_TYPE.food_related
                                       )
