import logging
from taco.core.regex.regex_template import RegexTemplate
from taco.response_generators.food.regex_templates import DoubtfulTemplate
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.core.entity_linker.entity_groups import EntityGroupsForExpectedType
from taco.core.util import infl
from cobot_core.service_module import ToolkitServiceModule
from cobot_core.service_module import LocalServiceModule

from ask_sdk_model.services.service_exception import ServiceException
from cobot_core.alexa_list_management import AlexaListManagement
# from taco.taco_intent_by_rule import TacoIntentByRule
# from taco.response_modules.choice.utils.general import get_and_list_prompt

from taco.response_generators.taco_rp.taco_intent_by_rule import TacoIntentByRule
from taco.response_generators.taco_rp.choice.treelets.utils.general import get_and_list_prompt
import json

import random

from cobot_core.service_module import LocalServiceModule
from taco.response_generators.taco_rp.exception.state import State, ConditionalState
from taco.response_generators.taco_rp.exception.treelets.template_manager import select_help_template


logger = logging.getLogger('tacologger')


class Taco_excet_help_Treelet(Treelet):
    name = "Taco_excet_error_Treelet"

    def classify_user_response(self):
        assert False, "This should never be called."


    def get_response(self, state_manager, priority=ResponsePriority.WEAK_CONTINUE, **kwargs) -> ResponseGeneratorResult:
        """ Returns the response. """
        state, utterance, response_types = self.get_state_utterance_response_types()
        
        last_taco_state = state_manager.user_attributes.taco_state
        speak_output = select_help_template(last_taco_state, state_manager.user_attributes)
        
        response = speak_output

        return ResponseGeneratorResult(text=response, priority=priority,
                                       needs_prompt=False, state=state, cur_entity=None,
                                       conditional_state=ConditionalState(
                                           prompt_treelet=self.name,))

    def get_best_candidate_user_entity(self, utterance, cur_food):
        def condition_fn(entity_linker_result, linked_span, entity):
            return EntityGroupsForExpectedType.food_related.matches(entity) and entity.name != cur_food
        entity = self.rg.state_manager.current_state.entity_linker.top_ent(condition_fn) or self.rg.state_manager.current_state.entity_linker.top_ent()
        if entity is not None:
            user_answer = entity.talkable_name
            plural = entity.is_plural
        else:
            nouns = self.rg.state_manager.current_state.corenlp['nouns']
            if len(nouns):
                user_answer = nouns[-1]
                plural = True
            else:
                user_answer = utterance.replace('i like', '').replace('my favorite', '').replace('i love', '')
                plural = True

        return user_answer, plural

