import logging
import random
from typing import Optional

from taco.core.response_generator import ResponseGenerator
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.response_generator_datatypes import emptyResult, ResponseGeneratorResult, PromptResult, emptyPrompt, \
    UpdateEntity, AnswerType
from taco.core.regex.regex_template import RegexTemplate
from taco.core.regex.response_lists import RESPONSE_TO_THATS, RESPONSE_TO_DIDNT_KNOW
from taco.response_generators.food.regex_templates import *
from taco.core.regex.util import OPTIONAL_TEXT_PRE, OPTIONAL_TEXT_POST

# treelets
from taco.core.offensive_classifier.offensive_classifier import OffensiveClassifier

from taco.core.response_generator.response_type import add_response_types, ResponseType

# treelets
from taco.response_generators.taco_rp.execution.treelets.taco_execution_treelet import Taco_execution_Treelet
from taco.response_generators.taco_rp.execution.treelets.taco_pak_treelet import Taco_pak_Treelet

from taco.response_generators.taco_rp.execution.state import *
NAME2TREELET = {treelet.__name__: treelet for treelet in [Taco_execution_Treelet, Taco_pak_Treelet]}


# response type
ADDITIONAL_RESPONSE_TYPES = ['NEEDED_execution']
ResponseType = add_response_types(ResponseType, ADDITIONAL_RESPONSE_TYPES)
        
logger = logging.getLogger('tacologger')


class execution_Generator(ResponseGenerator):
    name='execution_INTERNT'

    def __init__(self, state_manager) -> None:
        self.Taco_execution_Treelet = Taco_execution_Treelet(self)
        self.Taco_pak_Treelet = Taco_pak_Treelet(self)

        logger.taco_merge(f'{self.name} TREELET =  {NAME2TREELET}')
        
        treelets = {
            treelet.name: treelet for treelet in [self.Taco_execution_Treelet, self.Taco_pak_Treelet]
        }
        super().__init__(state_manager, treelets=treelets, intent_templates=[], can_give_prompts=True,
                         state_constructor=State,
                         conditional_state_constructor=ConditionalState,
                         trigger_words=["execution_response"])

    def handle_default_post_checks(self) -> Optional[ResponseGeneratorResult]:
        
        response = self.treelets[self.state.cur_treelet_str].get_response(self.state_manager)
        logger.primary_info(f"Response is: {response}")
        return response

    def identify_response_types(self, utterance):
        response_types = super().identify_response_types(utterance)
        response_types.add(ResponseType.NEEDED_execution)
        return response_types


    def get_prompt(self, state) -> Optional[PromptResult]:
        """
        If this treelet has a starter question, returns a prompt asking the starter question.
        Otherwise, returns None.

        If for_launch, will give version of starter question that's appropriate for launch sequence.
        """
        return self.treelets['Taco_pak_prompt_Treelet'].get_prompt(self.state_manager, state)

        # treeletname2promptresult = {treelet_name: name2initializedtreelet[treelet_name].get_prompt(state) for treelet_name in unused_treelet_names}
        # Taco_pak_prompt_Treelet

        # people_also_a_q = self.state_manager.user_attributes.people_also_ask_question
        # random.shuffle(people_also_a_q)

        # self.state_manager.user_attributes.PAK_selected_ans = people_also_a_q[-1][-1] 

        # starter_question = 'By the way, show you a fun fact. Are you interested in this question? ' +  people_also_a_q[-1][0]
        
        # starter_question = starter_question + ' If you are not interested, you can say next to skip it :)'
        # if len(self.state_manager.user_attributes.people_also_ask_question) > 1:
        #     self.state_manager.user_attributes.people_also_ask_question.pop()

        # taco_state = getattr(self.state_manager.current_state, 'status', None)
        # if 'Instruction' in taco_state:
        #     prompt_priority = PromptType.CURRENT_TOPIC
        # else:
        #     prompt_priority = PromptType.NO
        # # return PromptResult(text=starter_question, prompt_type=PromptType.FORCE_START)

        # return PromptResult(text=starter_question,
        #                     prompt_type=prompt_priority, state=state, cur_entity=None,
        #                     conditional_state=ConditionalState(used_people_also_ask=state.used_people_also_ask+1),
        #                     answer_type=AnswerType.ENDING)

    def update_state_if_chosen(self, state: State, conditional_state: Optional[ConditionalState]) -> BaseState:
        assert conditional_state is not None, "conditional_state should not be None if the response/prompt was chosen"
        self.treelets[conditional_state.prev_treelet_str].treet_update_current_state(self.state_manager, conditional_state)
        state = super().update_state_if_chosen(state, conditional_state)
        return state