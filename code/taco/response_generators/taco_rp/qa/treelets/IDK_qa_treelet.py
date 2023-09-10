import logging
from taco.core.regex.regex_template import RegexTemplate
from taco.response_generators.food.regex_templates import DoubtfulTemplate
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.core.entity_linker.entity_groups import EntityGroupsForExpectedType
from taco.core.util import infl

from taco.response_generators.taco_rp.qa.state import State, ConditionalState

import random

from taco.response_generators.taco_rp.templates import Template
from taco.response_generators.taco_rp import vocab
from taco.response_generators.taco_rp.taco_intent_by_rule import TacoIntentByRule

logger = logging.getLogger('tacologger')


FAILURE_TEMPLATE = [
    Template("I heard, ${text}, but I don’t know. "),
    Template("I heard, ${text}, but I’m not sure. "),
]

IMPROVEMENT_TEMPLATE = [
    Template("I’ll ask around after this chat. "),
    Template("I can check the books after this chat. "),
]


def has_details(user_attributes):
    docparse =  getattr(user_attributes, 'current_task_docparse', None)
    method_idx, N_methods, total_steps, current_step = TacoIntentByRule.parse_step_nums(user_attributes.taco_state)

    return (
        getattr(user_attributes, 'is_wikihow', False) and
        getattr(user_attributes, 'task_started', False) and
        docparse[method_idx][current_step]['detail']
    )


class IDK_qa_Treelet(Treelet):
    name = "IDK_qa_treelet"

    def classify_user_response(self):
        assert False, "This should never be called."


    def get_response(self, state_manager, priority=ResponsePriority.WEAK_CONTINUE, **kwargs) -> ResponseGeneratorResult:
        """ Returns the response. """
        state, utterance, response_types = self.get_state_utterance_response_types()
        
        user_attributes = state_manager.user_attributes
        text = state_manager.current_state.text

        inst = ''

        if has_details(user_attributes):
            inst = 'But you can ask me to tell you more details about this step. '
        elif getattr(user_attributes, 'task_started', False):
            inst = getattr(user_attributes, 'current_step_speak', '')
        else:
            inst = 'If you want to start a new search, say cancel. '

        response = f"{random.choice(vocab.SAD_EXCLAMATIONS)}! {random.choice(FAILURE_TEMPLATE).substitute(text=text)} {random.choice(IMPROVEMENT_TEMPLATE).substitute()} {inst} "
        
        
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
