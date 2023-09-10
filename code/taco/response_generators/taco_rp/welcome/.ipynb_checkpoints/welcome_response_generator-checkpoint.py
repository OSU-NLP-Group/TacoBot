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
from taco.response_generators.taco_rp.welcome.state import State, ConditionalState

from taco.core.response_generator.response_type import add_response_types, ResponseType


NAME2TREELET = {treelet.__name__: treelet for treelet in [WELCOME_Treelet]}

print('NAME2TREELET = ', NAME2TREELET)

# response type
ADDITIONAL_RESPONSE_TYPES = ['NEEDED_LANUCH']
ResponseType = add_response_types(ResponseType, ADDITIONAL_RESPONSE_TYPES)
        
logger = logging.getLogger('tacologger')

class Lanuch_Generator(ResponseGenerator):
    name='WELCOME'

    def __init__(self, state_manager) -> None:
        self.lanuch_treelet = WELCOME_Treelet(self)
        
        treelets = {
            treelet.name: treelet for treelet in [self.lanuch_treelet]
        }
        super().__init__(state_manager, treelets=treelets, intent_templates=[], can_give_prompts=True,
                         state_constructor=State,
                         conditional_state_constructor=ConditionalState,
                         trigger_words=["welcome"])

    def identify_response_types(self, utterance):
        response_types = super().identify_response_types(utterance)
        response_types.add(ResponseType.NEEDED_LANUCH)

        return response_types

    def handle_default_post_checks(self) -> Optional[ResponseGeneratorResult]:
        
        name2initializedtreelet = {treelet_name: treelet_class(self) for treelet_name, treelet_class in NAME2TREELET.items()}

        treelet = name2initializedtreelet['WELCOME_Treelet']
        response = treelet.get_response(self.state_manager, force=True)
        logger.primary_info(f"Response is: {response}")
        return response


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
