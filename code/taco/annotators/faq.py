import logging

from taco.core.callables import Annotator
from taco.core.state_manager import StateManager


logger = logging.getLogger('tacologger')


class FAQ_response(Annotator):
    name='faq'
    def __init__(self, state_manager: StateManager, timeout=10, url=None, input_annotations = []):
        super().__init__(state_manager=state_manager, timeout=timeout, url=url, input_annotations=input_annotations)

    def get_default_response(self, input_data = None):
        return None

    def execute(self, input_data=None):
        """
            nounphrase extractor for tacobot
        """
        user_utterances = [self.state_manager.current_state.text]
        last_state_response = None

        input_data = {'text': user_utterances}

        # if not input_data['text']:
        #     return self.get_default_response(input_data)

        logger.debug(f'Calling MRC_response Remote module with utterances="{user_utterances}"')

        FAQ_rp_output = self.remote_call(input_data)
        if FAQ_rp_output is None:
            default_response = self.get_default_response(input_data)
            logger.info(f'{type(self).__name__} using default response: {default_response}')
            return default_response

        return FAQ_rp_output
