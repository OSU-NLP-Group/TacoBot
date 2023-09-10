import logging
from typing import Optional, Tuple, List

from taco.core.util import get_user_datetime, get_user_dayofweek
from taco.response_generators.neural_chat.treelets.abstract_treelet import Treelet
from taco.response_generators.neural_chat.state import State
from taco.core.response_generator_datatypes import PromptType
from taco.core.response_generator.response_type import *

logger = logging.getLogger('tacologger')


THIS_OR_THAT_PREFIX = "Here's a fun question to get things started. "

GO_BACK_PROMPT_request_stop = [
    "Now is the moment to shift our attention and return to our primary objective.",
    "It is high time that we redirect our attention and diligently return to our primary task.",
    "Ok guys, it's time to get back to our main task and focus on it.",
    "It is imperative that we redirect our attention and endeavor to diligently apply ourselves to the main objective at hand."
]


GO_BACK_PROMPT = [
    # Ideally triggers PERSONAL_ISSUES
    "Oh ops. I totally forget we have an ongoing task. Now is the moment to shift our attention and return to our primary objective.",
    "Oh dear, it appears that I have completely forgotten about our ongoing assignment. It is high time that we redirect our attention and diligently return to our primary task.",
    "Oh man, I totally forgot about the task we're supposed to be working on. It's time to get back on track and focus on what we need to do.",
    "Regrettably, I appear to have overlooked the fact that we are currently engaged in an ongoing task. It is imperative that we redirect our attention and endeavor to diligently apply ourselves to the main objective at hand."
]


class GO_BACK_Treelet(Treelet):
    """go back to instruction"""
    name = "GO_BACK_Treelet"

    _launch_appropriate = True
    fallback_response = "That was interesting! That's why I love talking to people."

    def get_starter_question_and_labels(self, state: State, for_response: bool = False, for_launch: bool = False) -> Tuple[Optional[str], List[str]]:
        """
        Inputs:
            response: if True, the provided starter question will be used to make a response. Otherwise, used to make a prompt.

        Returns a tuple of:
            - A starter question (str), or None (if it's not appropriate for this treelet to ask a starter question at this time).
            - Labels for the starter question, that should go in the state.
            - priority: ResponsePriority or PromptType
        """
        candiate_prompt = GO_BACK_PROMPT

        if ResponseType.REQUEST_STOP in state.response_types:
             candiate_prompt = GO_BACK_PROMPT_request_stop
        
        response_text = self.choose(candiate_prompt)
        response_text += "You can say ok or next to move on"

        if for_response:
            return None, [], None
        return response_text, [], PromptType.FORCE_START

    @property
    def return_question_answer(self) -> str:
        """Gives a response to the user if they ask the "return question" to our starter question"""
        
        # DEPRECATED -- No need w/ blenderbot
        raise NotImplementedError