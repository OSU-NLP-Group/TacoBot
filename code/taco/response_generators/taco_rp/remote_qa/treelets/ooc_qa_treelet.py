import logging
from taco.core.regex.regex_template import RegexTemplate
from taco.response_generators.food.regex_templates import DoubtfulTemplate
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.core.entity_linker.entity_groups import EntityGroupsForExpectedType
from taco.core.util import infl
import threading
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from taco.response_generators.taco_rp.remote_qa.state import *
from taco.annotators.ooc import OOC_response

import random

logger = logging.getLogger('tacologger')


class OOC_qa_Treelet(Treelet):
    name = "OOC_qa_treelet"

    def classify_user_response(self):
        assert False, "This should never be called."


    def get_response(self, state_manager, priority=ResponsePriority.CAN_START, **kwargs) -> ResponseGeneratorResult:
        """ Returns the response. """
        state, utterance, response_types = self.get_state_utterance_response_types()
        
        def execute_neural():
            responses = OOC_response(state_manager).execute()
            return responses

        ### BEGIN THREADING ###
        thread = threading.currentThread()
        should_kill = getattr(thread, "killable", False)
        if should_kill:
            logger.primary_info(f"Infiller interior call detected to be running in a killable thread.")
        is_done = getattr(thread, "isKilled", False)

        def initializer(killable: bool):
            threading.currentThread().killable = killable
            threading.currentThread().isKilled = is_done

        with futures.ThreadPoolExecutor(max_workers=2, initializer=initializer, initargs=(should_kill,)) as executor:
            neural_future = executor.submit(execute_neural)

        acknowledgements = neural_future.result()

        logger.taco_merge(f'remote result = {acknowledgements}')
        text = acknowledgements['response']
        if len(text) == 0:
            text = "Sorry, I can't find the good answer for your question."
            priority = ResponsePriority.NO

        return ResponseGeneratorResult(text=text, priority=priority,
                                       needs_prompt=False, state=state, cur_entity=None,
                                       conditional_state=ConditionalState(
                                           prev_treelet_str=self.name,
                                           ))