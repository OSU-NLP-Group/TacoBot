import logging

from taco.core.callables import Annotator
from taco.core.state_manager import StateManager

logger = logging.getLogger('tacologger')


class NeuralIntent(Annotator):
    name="neuralintent"
    def __init__(self, state_manager: StateManager, timeout=3, url=None, input_annotations = []):
        super().__init__(state_manager=state_manager, timeout=timeout, url=url, input_annotations=input_annotations)

    def get_default_response(self, input_data = None):
        return None

    def execute(self, input_data=None):
        """
            template annotator for tacobot
        """
        user_utterances = [self.state_manager.current_state.text]

        if input_data is None:
            input_data = {'text': user_utterances}

        if not input_data['text']:
            return self.get_default_response(input_data)

        logger.debug(f'Calling Neural Intent Annotator Remote module with utterances="{user_utterances}"')

        output = self.remote_call(input_data)
        if output is None:
            default_response = self.get_default_response(input_data)
            logger.info(f'{type(self).__name__} using default response: {default_response}')
            return default_response

        return output