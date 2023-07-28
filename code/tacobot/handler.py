from tacobot.state import State
from tacobot.state_manager import StateManager
from tacobot.user_attributes import UserAttributes
from tacobot.model_serving.model_manager import Annotator, ResponseGenerator, run_anotators_multithreaded
from typing import List, Optional, Type, Dict
import logging

logger = logging.getLogger('tacologger')


class TurnResult:
    response: str
    should_end_session: bool
    current_state: Dict[str, str]
    user_attributes: Dict[str, str]


class Handler:
    def __init__(self,
                 session_id,
                 annotator_classes: List[Type[Annotator]],
                 response_generator_classes: List[Type[ResponseGenerator]],
                 save_before_response=True,
                 timeout=3,
                 name='tacobot'):
        self.session_id = session_id
        self.annotator_classes = annotator_classes
        self.response_generator_classes = response_generator_classes
        self.save_before_response = save_before_response
        self.timeout = timeout
        self.name = name

    def execute(self, current_state: dict, user_attributes: dict, last_state: Optional[dict]=None) -> TurnResult:
        current_state = State.deserialize(current_state)
        user_attributes = UserAttributes.deserialize(user_attributes)
        if last_state:
            last_state = State.deserialize(last_state)
            current_state.update_from_last_state(last_state)
        state_manager = StateManager(current_state, user_attributes, last_state)

        response_generators = ResponseGenerator(state_manager, self.response_generator_classes)
        annotators = [c(state_manager) for c in self.annotator_classes]

        logger.info('Running the NLP pipeline...')
        result = run_anotators_multithreaded(annotators, 'execute', self.timeout)

        ####


        logger.info('Finished running the NLP pipeline.')
        return result


