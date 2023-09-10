"""
    Trenton Chang, Caleb Chiam - Nov. 2020
    ending_treelet.py

    The following treelet is a core component in the personal issues response generator. This treelet is intended to provide a natural
    way for taco to end this phase of the conversation with the user, and should be used when the conversation has reached its end
    NOT due to negative navigational intent. Subsequent turns may change the subject, or continue talking about the user's personal issue.


"""

from taco.core.response_generator import Treelet
from taco.response_generators.personal_issues.state import State, ConditionalState
from taco.response_generators.personal_issues.response_templates.ending_response_template import \
    EndingResponseTemplate
from taco.core.response_generator_datatypes import ResponseGeneratorResult
from taco.response_generators.personal_issues.personal_issues_helpers import ResponseType

import logging
from typing import Set  # NOQA
logger = logging.getLogger('tacologger')

class EndingTreelet(Treelet):
    """
    Provides an option to naturally end the conversation.
    """
    name = "personal_issues_ending"

    def get_response(self, priority):
        """Generates a ResponseGeneratorResult containing that treelet's response to the user.

        Args:
            state (State): representation of the RG's internal state; see state.py for definition.
            utterance (str): what the user just said
            response_types (Set[ResponseType]): type of response given by the user; see ...personal_issues/personal_issues_utils.py
                for a full definition of the ResponseTypes enum.
            priority (ResponsePriority): five-level response priority tier.

        Returns:
            ResponseGeneratorResult: an object encapsulating the textual response given by the RG, and some metadata.
        """
        state, utterance, response_types = self.get_state_utterance_response_types()
        template = EndingResponseTemplate()
        response = template.sample()
        conditional_state = ConditionalState(prev_treelet_str=self.name,
                                             next_treelet_str='transition')
        return ResponseGeneratorResult(text=response, priority=priority, needs_prompt=True, state=state,
                                       cur_entity=None, conditional_state=conditional_state)
