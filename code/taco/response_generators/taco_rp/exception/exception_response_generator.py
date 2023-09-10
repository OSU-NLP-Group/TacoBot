import logging
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
from taco.response_generators.taco_rp.exception.treelets.taco_exception_bad_treelet import Taco_excet_bad_Treelet
from taco.response_generators.taco_rp.exception.treelets.taco_exception_error_treelet import Taco_excet_error_Treelet
from taco.response_generators.taco_rp.exception.treelets.taco_exception_help_treelet import Taco_excet_help_Treelet

from taco.response_generators.taco_rp.exception.state import State, ConditionalState

NAME2TREELET = {treelet.__name__: treelet for treelet in [Taco_excet_bad_Treelet, Taco_excet_error_Treelet, Taco_excet_help_Treelet]}


# response type
ADDITIONAL_RESPONSE_TYPES = ['NEEDED_execution']
ResponseType = add_response_types(ResponseType, ADDITIONAL_RESPONSE_TYPES)
        
logger = logging.getLogger('tacologger')


class Exception_ResponseGenerator(ResponseGenerator):
    name='exception_INTERNT'

    def __init__(self, state_manager) -> None:
        self.Taco_excet_bad_Treelet = Taco_excet_bad_Treelet(self)
        self.Taco_excet_error_Treelet = Taco_excet_error_Treelet(self)
        self.Taco_excet_help_Treelet = Taco_excet_help_Treelet(self)
        
        # logger.taco_merge(f'{self.name} TREELET =  {NAME2TREELET}')
        treelets = {
            treelet.name: treelet for treelet in [self.Taco_excet_bad_Treelet, self.Taco_excet_error_Treelet, self.Taco_excet_help_Treelet]
        }
        super().__init__(state_manager, treelets=treelets, intent_templates=[], can_give_prompts=True,
                         state_constructor=State,
                         conditional_state_constructor=ConditionalState,
                         trigger_words=["execution_response"])

    def identify_response_types(self, utterance):
        response_types = super().identify_response_types(utterance)
        response_types.add(ResponseType.NEEDED_execution)
 
        return response_types

    def handle_default_post_checks(self) -> Optional[ResponseGeneratorResult]:
        
        name2initializedtreelet = {treelet_name: treelet_class(self) for treelet_name, treelet_class in NAME2TREELET.items()}


        candidate_treelets = self.state_manager.current_state.response_generator_states[self.name].candidate_treelets

        bad_response = ''
        help_response = ''
        error_response = ''


        if "Taco_excet_bad_Treelet" in candidate_treelets:
            bad_response =   self.treelets['Taco_excet_bad_Treelet'].get_response(self.state_manager)
            if bad_response.text != '':
                self.state_manager.current_state.response_generator_states[self.name].cur_treelet_str = "Taco_excet_bad_Treelet"
                return bad_response
        if "Taco_excet_help_Treelet" in candidate_treelets: 
            help_response =  self.treelets['Taco_excet_help_Treelet'].get_response(self.state_manager)
            if  help_response.text != '':
                self.state_manager.current_state.response_generator_states[self.name].cur_treelet_str = "Taco_excet_help_Treelet"
                return help_response

        # if "Taco_excet_error_Treelet" in candidate_treelets:
        error_response = self.treelets['Taco_excet_error_Treelet'].get_response(self.state_manager)
        self.state_manager.current_state.response_generator_states[self.name].cur_treelet_str = "Taco_excet_error_Treelet"
        return error_response

        # taco_state = getattr(self.state_manager.current_state, 'status', None)
        # parsed_intent = getattr(current_state, 'parsed_intent', None)

        # execute_tweet = self.state_manager.current_state.response_generator_states[self.name].cur_treelet_str

        # logger.taco_merge(f'execute_tweet = {execute_tweet}')

        
        # treelet = name2initializedtreelet[execute_tweet]
        # response = treelet.get_response(self.state_manager, force=True)
        # logger.primary_info(f"Response is: {response}")
        # return response
    

    def handle_rejection_response(self, prefix='', main_text=None, suffix='',
                                  priority=ResponsePriority.STRONG_CONTINUE, needs_prompt=True,
                                  conditional_state=None, answer_type=AnswerType.ENDING):
        return super().handle_rejection_response(
            prefix="I'm sorry. I might've said something weird.",
            main_text=main_text,
            suffix=suffix,
            priority=priority,
            needs_prompt=needs_prompt,
            conditional_state=conditional_state,
            answer_type=answer_type
        )


    def get_prompt(self, state):
        self.state = state
        self.response_types = self.get_cache(f'{self.name}_response_types')
        return self.emptyPrompt()
