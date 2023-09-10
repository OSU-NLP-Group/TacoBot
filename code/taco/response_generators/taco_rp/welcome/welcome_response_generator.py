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
from taco.response_generators.taco_rp.welcome.treelets.lanuch_treelet import WELCOME_Treelet
from taco.response_generators.taco_rp.welcome.state import *

from taco.core.response_generator.response_type import add_response_types, ResponseType


NAME2TREELET = {treelet.__name__: treelet for treelet in [WELCOME_Treelet]}


# response type
ADDITIONAL_RESPONSE_TYPES = ['NEEDED_LANUCH']
ResponseType = add_response_types(ResponseType, ADDITIONAL_RESPONSE_TYPES)
        
logger = logging.getLogger('tacologger')


# logger.taco_merge('NAME2TREELET = ')
# logger.taco_merge('NAME2TREELET = ', NAME2TREELET)
# taco_merge

class Lanuch_Generator(ResponseGenerator):
    name='WELCOME'

    def __init__(self, state_manager) -> None:


        self.lanuch_treelet = WELCOME_Treelet(self)
        
        # logger.taco_merge(f'{self.name} TREELET =  {NAME2TREELET}')

        treelets = {
            treelet.name: treelet for treelet in [self.lanuch_treelet]
        }
        super().__init__(state_manager, treelets=treelets, intent_templates=[], can_give_prompts=True,
                         state_constructor=State,
                         conditional_state_constructor=ConditionalState,
                         trigger_words=["welcome"])

    def handle_default_pre_checks(self):
        return self.treelets[self.state.cur_treelet_str].get_response(self.state_manager)

    def init_state(self) -> State:
        # if state_manager says it's first turn, set next_treelet to be FirstTurnTreelet
        if self.state_manager.last_state is None:
            return State(cur_treelet_str=self.lanuch_treelet.name)

        # if state_manager says it's not first turn, then we're running init_state because LAUNCH failed.
        # set to OFF so that we don't start the launch sequence again.
        else:
            return State(cur_treelet_str=None)

    def identify_response_types(self, utterance):
        response_types = super().identify_response_types(utterance)
        response_types.add(ResponseType.NEEDED_LANUCH)

        return response_types

    def update_state_if_chosen(self, state: State, conditional_state: Optional[ConditionalState]) -> BaseState:
        assert conditional_state is not None, "conditional_state should not be None if the response/prompt was chosen"
        self.treelets[conditional_state.prev_treelet_str].treet_update_current_state(self.state_manager, conditional_state)
        state = super().update_state_if_chosen(state, conditional_state)
        return state

    # def update_state_if_not_chosen(self, state: State, conditional_state: Optional[ConditionalState]) -> BaseState:
    #     state = super().update_state_if_not_chosen(state, conditional_state)
    #     state.next_treelet_str = None
    #     return state
