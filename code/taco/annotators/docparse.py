import logging

from taco.core.callables import Annotator
from taco.core.state_manager import StateManager

logger = logging.getLogger('tacologger')


class Docparse(Annotator):
    name="docparse"
    def __init__(self, state_manager: StateManager, timeout=3, url=None, input_annotations = []):
        super().__init__(state_manager=state_manager, timeout=timeout, url=url, input_annotations=input_annotations)

    def get_default_response(self, input_data = None):
        return None

    def execute(self, input_data=None):
        """
            nounphrase extractor for tacobot
        """
        user_utterances = [self.state_manager.current_state.text]
        taco_state = self.state_manager.current_state.status
        current_task_docparse = getattr(self.state_manager.user_attributes, 'current_task_docparse', None)
        query_result = getattr(self.state_manager.user_attributes, 'query_result', None)
        list_item_selected = getattr(self.state_manager.user_attributes, 'list_item_selected', None)
        is_wikihow = getattr(self.state_manager.user_attributes, 'is_wikihow', None)

        input_data = {'text': user_utterances, 'taco_state': taco_state, 'current_task_docparse': current_task_docparse,
                      'query_result': query_result, 'list_item_selected': list_item_selected, 'is_wikihow': is_wikihow}

        if not input_data['text']:
            return self.get_default_response(input_data)

        logger.debug(f'Calling Recipe Search Annotator Remote module with utterances="{user_utterances}"')

        output = self.remote_call(input_data)
        if output is None:
            default_response = self.get_default_response(input_data)
            logger.info(f'{type(self).__name__} using default response: {default_response}')
            return default_response

        return output
