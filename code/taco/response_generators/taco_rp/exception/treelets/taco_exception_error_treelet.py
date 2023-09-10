import logging
from taco.core.regex.regex_template import RegexTemplate
from taco.response_generators.food.regex_templates import DoubtfulTemplate
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.core.entity_linker.entity_groups import EntityGroupsForExpectedType
from taco.core.util import infl

from taco.response_generators.taco_rp.taco_intent_by_rule import TacoIntentByRule
from taco.response_generators.taco_rp.choice.treelets.utils.general import get_and_list_prompt
import json

import random

from taco.response_generators.taco_rp.exception.state import State, ConditionalState
from taco.response_generators.taco_rp.exception.treelets.template_manager import select_error_template

detect_keyword = lambda x, k: (k in x) if ' ' in k else (k in x.split())

logger = logging.getLogger('tacologger')


class Taco_excet_error_Treelet(Treelet):
    name = "Taco_excet_error_Treelet"

    def classify_user_response(self):
        assert False, "This should never be called."


    def get_response(self, state_manager, priority=ResponsePriority.WEAK_CONTINUE, **kwargs) -> ResponseGeneratorResult:
        """ Returns the response. """
        state, utterance, response_types = self.get_state_utterance_response_types()

        # need_cancel = state_manager.current_state.need_cancel
#         20220928 comment it
#         need_cancel = state_manager.current_state.need_cancel
        # need_cancel = True
    
        # if need_cancel:
        #     response = 'I\'m so sorry that I messed up! I\'ll learn to do better next time. Would you please say, cancel, to start over? Or you can say, stop. '
        #     shouldEndSession = False
        # else:

        text = state_manager.current_state.text
        parsed_intent = state_manager.current_state.parsed_intent
        last_state = state_manager.last_state

        last_parsed_intent = None
        if last_state:
            if 'parsed_intent' in last_state.__dict__:
                last_parsed_intent = last_state.parsed_intent
        # else:
        #     # Use StateTable as backup. NOTE It may be erroneous!
        #     last_parsed_intent = (
        #         state_manager.last_state.get('parsed_intent', '') if state_manager.last_state is not None else ''
        #     )
        
        response = select_error_template(text, parsed_intent, last_parsed_intent)
            
        if 'I think you said cancel multiple times' in response:
            priority = ResponsePriority.STRONG_CONTINUE

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

