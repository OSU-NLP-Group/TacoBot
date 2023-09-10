import logging
import json
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

logger = logging.getLogger('tacologger')

class TacoStop(Treelet):
    
    """
    If the user has an ongoing task, ask if they want to continue or complete it.
    Otherwise, share suggestions for what the user should try.
    """
    name = "TacoStop_Treelet"
    
    def classify_user_response(self):
        assert False, "This should never be called."

        
    def get_response(self, state_manager, priority=ResponsePriority.WEAK_CONTINUE, **kwargs) -> ResponseGeneratorResult:
        """ Returns the response. """
        state, utterance, response_types = self.get_state_utterance_response_types()
        
        user_attributes = state_manager.user_attributes
        text = state_manager.current_state.text
        
        current_task = getattr(
            state_manager.user_attributes, "current_task", None
        )  # Properly stop the bot before TaskExecution
        if current_task is None:
            setattr(state_manager.user_attributes, "query_result", None)
            setattr(state_manager.user_attributes, "current_task", None)
            setattr(state_manager.user_attributes, "current_step", None)
            setattr(state_manager.user_attributes, "list_item_selected", None)
            setattr(state_manager.user_attributes, "started_cooking", None)
            setattr(state_manager.user_attributes, "taco_state", None)
            setattr(state_manager.user_attributes, 'query_wikihow', None)
            setattr(state_manager.user_attributes, 'query_recipe', None)
            setattr(state_manager.user_attributes, 'confirmed_query', None)
            setattr(state_manager.user_attributes, 'confirmed_complete', None)

        
        return ResponseGeneratorResult(text='DUMMY_STOP', priority=priority,
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
