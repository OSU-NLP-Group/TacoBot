import logging
from typing import Optional

from taco.core.response_generator import ResponseGenerator
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.response_generator_datatypes import emptyResult, ResponseGeneratorResult, PromptResult, emptyPrompt, \
    UpdateEntity, AnswerType
from taco.core.regex.regex_template import RegexTemplate
from taco.core.regex.response_lists import RESPONSE_TO_THATS, RESPONSE_TO_DIDNT_KNOW
from taco.core.regex.util import OPTIONAL_TEXT_PRE, OPTIONAL_TEXT_POST

# treelets
from taco.response_generators.taco_rp.utils.treelets.taco_repeat import TacoRepeat
from taco.response_generators.taco_rp.utils.treelets.taco_stop import TacoStop

from taco.response_generators.taco_rp.welcome.state import State, ConditionalState

from taco.core.response_generator.response_type import add_response_types, ResponseType


NAME2TREELET = {treelet.__name__: treelet for treelet in [TacoRepeat, TacoStop]}

# print('NAME2TREELET = ', NAME2TREELET)

# response type
ADDITIONAL_RESPONSE_TYPES = ['NEEDED_utils']
ResponseType = add_response_types(ResponseType, ADDITIONAL_RESPONSE_TYPES)
        
logger = logging.getLogger('tacologger')

class utils_Generator(ResponseGenerator):
    name='utils_intent'

    def __init__(self, state_manager) -> None:
        self.TacoRepeat = TacoRepeat(self)
        self.TacoStop = TacoStop(self)
        
        treelets = {
            treelet.name: treelet for treelet in [self.TacoRepeat, self.TacoStop]
        }
        super().__init__(state_manager, treelets=treelets, intent_templates=[], can_give_prompts=True,
                         state_constructor=State,
                         conditional_state_constructor=ConditionalState,
                         trigger_words=["utils"])


    def handle_default_post_checks(self) -> Optional[ResponseGeneratorResult]:
        response = self.treelets[self.state.cur_treelet_str].get_response(self.state_manager)
        logger.primary_info(f"Response is: {response}")
        return response

    def identify_response_types(self, utterance):
        response_types = super().identify_response_types(utterance)
        response_types.add(ResponseType.NEEDED_utils)
        return response_types
