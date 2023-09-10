import logging

from taco.core.callables import Annotator
from taco.core.state_manager import StateManager

logger = logging.getLogger('tacologger')


class NounPhrases(Annotator):
    name="nounphrases"
    def __init__(self, state_manager: StateManager, timeout=3, url=None, input_annotations = []):
        super().__init__(state_manager=state_manager, timeout=timeout, url=url, input_annotations=input_annotations)

    def get_default_response(self, input_data = None):
        return None

    def execute(self, input_data=None):
        """
            nounphrase extractor for tacobot
        """
        user_utterances = [self.state_manager.current_state.text]
        last_state_response = None
        # last_state_response = self.state_manager.last_state_response
        bot_responses = ["hi how are you today", "i will help you cook a dish today!"]
        if last_state_response is not None:
            bot_responses.append(last_state_response)
        if input_data is None:
            input_data = {'text': user_utterances, 'response': bot_responses}

        if not input_data['text']:
            return self.get_default_response()

        logger.debug(f'Calling Noun Phrase Annotator Remote module with utterances="{user_utterances}"')

        nounphrases_output = self.remote_call(input_data)
        if nounphrases_output is None:
            default_response = self.get_default_response()
            logger.info(f'{type(self).__name__} using default response: {default_response}')
            return default_response

        return nounphrases_output
