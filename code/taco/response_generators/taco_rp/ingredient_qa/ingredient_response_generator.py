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
from taco.response_generators.taco_rp.ingredient_qa.treelets.ingredicent_treelet import IngredientTreelet

from taco.response_generators.taco_rp.ingredient_qa.treelets.ingredicent_substitude import IngredientSubstituteTreelet

# treelets
from taco.response_generators.taco_rp.ingredient_qa.state import *

from taco.core.offensive_classifier.offensive_classifier import OffensiveClassifier
from taco.core.response_generator.response_type import add_response_types, ResponseType


NAME2TREELET = {treelet.__name__: treelet for treelet in [IngredientTreelet, IngredientSubstituteTreelet]}


# response type
ADDITIONAL_RESPONSE_TYPES = ['NEEDED_INGREDIENT']
ResponseType = add_response_types(ResponseType, ADDITIONAL_RESPONSE_TYPES)
        
logger = logging.getLogger('tacologger')

class INGREDIENT_Generator(ResponseGenerator):
    name='INGREDIENT'

    def __init__(self, state_manager) -> None:
        self.Ingredient_treelet = IngredientTreelet(self)

        logger.taco_merge(f'{self.name} TREELET =  {NAME2TREELET}')
        
        treelets = {
            treelet.name: treelet for treelet in [self.Ingredient_treelet]
        }
        super().__init__(state_manager, treelets=treelets, intent_templates=[], can_give_prompts=True,
                         state_constructor=State,
                         conditional_state_constructor=ConditionalState,
                         trigger_words=["ingredient_needed"])

    def handle_default_post_checks(self) -> Optional[ResponseGeneratorResult]:
        
        response = self.treelets[self.state.cur_treelet_str].get_response(self.state_manager)
        logger.primary_info(f"Response is: {response}")
        return response

    def identify_response_types(self, utterance):
        response_types = super().identify_response_types(utterance)
        response_types.add(ResponseType.NEEDED_INGREDIENT)
        return response_types

    def update_state_if_chosen(self, state: State, conditional_state: Optional[ConditionalState]) -> BaseState:
        assert conditional_state is not None, "conditional_state should not be None if the response/prompt was chosen"
        self.treelets[conditional_state.prev_treelet_str].treet_update_current_state(self.state_manager, conditional_state)
        state = super().update_state_if_chosen(state, conditional_state)
        return state
