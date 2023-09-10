import logging

from taco.core.callables import Annotator
from taco.core.state_manager import StateManager
logger = logging.getLogger('tacologger')


class TaskType(Annotator):
    name="tasktype"
    def __init__(self, state_manager: StateManager, timeout=3, url=None, input_annotations=[]):
        super().__init__(state_manager=state_manager, timeout=timeout, url=url, input_annotations=input_annotations)

    def get_default_response(self, input_data = None):
        return None

    def execute(self, input_data=None):
        """
            tasktype annotator for tacobot
        """
        user_utterances = [self.state_manager.current_state.text]
        taco_state = self.state_manager.current_state.status
        task_started = getattr(self.state_manager.user_attributes, 'task_started', None)
        selected_task = None
        proposed_tasks = None

        if input_data is None:
            input_data = {'text': user_utterances, 'task_started': task_started,
                          'selected_task': selected_task, 'proposed_tasks': proposed_tasks}

        if not input_data['text']:
            return self.get_default_response(input_data)

        logger.debug(f'Calling Tasktype Annotator Remote module with utterances="{user_utterances}"')

        if task_started != True and 'clarification' not in taco_state and 'chat' not in taco_state and self.check_user_said_chatty() == False:
            output = self.remote_call(input_data)
        else:
            output = False
        if output is None:
            default_response = self.get_default_response(input_data)
            logger.info(f'{type(self).__name__} using default response: {default_response}')
            return default_response

        return output
