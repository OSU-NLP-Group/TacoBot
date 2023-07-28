from injector import inject
from .taco_state_manager import StateManager
from .taco_prompt_constants import Prompt


class GlobalIntentHandler(object):
    """
    Handle mandatory global intents, such as AMAZON.StopIntent, as well as special handling logic for LaunchRequest
    """

    @inject
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    def execute(self, event) -> (str, bool):
        request_type = self.state_manager.current_state.request_type
        intent = self.state_manager.current_state.intent
        output = None
        should_end_session = False

        if request_type == 'LaunchRequest':
            output = Prompt.welcome_prompt
            should_end_session = False

        if intent in ['AMAZON.StopIntent', 'AMAZON.CancelIntent']:
            output = Prompt.goodbye_prompt
            should_end_session = True

        return output, should_end_session
