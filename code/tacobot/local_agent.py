import datetime
import os
import uuid
from collections import defaultdict
import time
from typing import Dict

import jsonpickle

from tacobot.annotators.neuralintent import NeuralIntent
from tacobot.annotators.nounphrases import NounPhrases
from tacobot.annotators.questiontype import QuestionType
from tacobot.annotators.recipesearch import RecipeSearch
from tacobot.annotators.taskfilter import Taskfilter
from tacobot.annotators.taskname import Taskname
from tacobot.annotators.tasksearch import TaskSearch
from tacobot.annotators.tasktype import TaskType
from tacobot.annotators.template import Template



from tacobot.handler import Handler
from tacobot.state_manager import State
import logging

logger = logging.getLogger('tacologger')


class LocalAgent:

    def __init__(self):
        self.session_id = uuid.uuid4().hex
        self.state_store = {}
        self.user_id = "1"
        self.user_store = defaultdict(dict)
        self.new_session = True
        self.last_state_creation_time = None

    def fetch_dialog_state(self, session_id, creation_date_time):
        if session_id is None:
            return None
        try:
            item = None
            start_time = time.time()
            timeout = 2 #second
            while (item is None and time.time() < start_time + timeout):
                a = list(self.state_store.keys())[0]
                Q = '"'
                return self.state_store[(Q + session_id + Q, creation_date_time)]
            if item is None:
                #logger.error(
                #    f"Timed out when fetching last state\nfor session {session_id}, creation_date_time {creation_date_time} from table {self.table_name}.")
                pass
            else:
                return item
        except:
            logger.error("Exception when fetching last state")
            return None

    def save_dialog_state(self, state: Dict):
        logger.info('Using StateTable to persist state! Persisting to state_store')
        logger.info('session_id: {}'.format(state['session_id']))
        logger.info('creation_date_time: {}'.format(state['creation_date_time']))
        try:
            assert 'session_id' in state
            assert 'creation_date_time' in state
            self.state_store[(state['session_id'], state['creation_date_time'])] = state
            return True
        except:
            logger.error("Exception when persisting state to state_store", exc_info=True)
            return False

    def fetch_user_state(self, user_id):
        logger.debug(
            f"user_table fetching last state for user {user_id} from user_store")
        if user_id is None:
            return None
        try:
            item = None
            start_time = time.time()
            timeout = 2  # second
            while (item is None and time.time() < start_time + timeout):
                item = self.user_store[user_id]
            if item is None:
                logger.error(
                    f"Timed out when fetching user attributes\nfor user_id {user_id} from user_store.")
            else:
                return item
        except:
            logger.error("Exception when fetching user attributes from user_store", exc_info=True)
            return None

    def save_user_state(self, user_attributes: Dict) -> None:
        """
        This will take the provided user_preferences object and persist it to DynamoDB. It does this by creating
                a dictionary representing the DynamoDB item to push consisting of user_id and a dictionary representing all of
                the user preferences.
        :param user_attributes: input UserAttributes object
        :return: None
        """
        try:
            assert 'user_id' in user_attributes
            self.user_store[user_attributes['user_id']] = user_attributes
            return True
        except:
            logger.error("Exception when persisting state to user_store", exc_info=True)
            return False

    def get_state_attributes(self, user_utterance):
        state_attributes = {}
        state_attributes['creation_date_time'] = str(datetime.datetime.utcnow().isoformat())
        pipeline = os.environ.get('PIPELINE')
        state_attributes['pipeline'] = pipeline if pipeline is not None else ''
        commit_id = os.environ.get('COMMITID')
        state_attributes['commit_id'] = commit_id if commit_id is not None else ''
        state_attributes['session_id'] = self.session_id
        state_attributes['user_id'] = self.user_id
        state_attributes['text'] = user_utterance
        state_attributes = {k: jsonpickle.encode(v) for k, v in state_attributes.items()}
        return state_attributes

    def get_last_state(self): # figure out new session and session_id
        if not self.new_session:
            last_state = self.fetch_dialog_state(self.session_id, self.last_state_creation_time)
        else:
            last_state = None
        return last_state

    def get_user_attributes(self):
        user_attributes = self.fetch_user_state(self.user_id)
        user_attributes['user_id'] = self.user_id
        # user_attributes['user_timezone'] = None
        user_attributes = {k: jsonpickle.encode(v) for k, v in user_attributes.items()}
        return user_attributes

    def should_end_session(self, turn_result):
        return turn_result.should_end_session

    def create_handler(self, timeout):
        return Handler(session_id=self.session_id,
                 annotator_classes=[NeuralIntent, NounPhrases, QuestionType, RecipeSearch, Taskfilter, Taskname, TaskSearch, TaskType, Template],
                 response_generator_classes=[],
                 timeout=timeout,
                 save_before_response=False)


    def process_utterance(self, user_utterance):
        handler = self.create_handler(timeout=1000000)

        current_state = self.get_state_attributes(user_utterance)
        user_attributes = self.get_user_attributes()
        last_state = self.get_last_state()

        turn_result = handler.execute(current_state, user_attributes, last_state)
        response = turn_result.response

        if self.new_session:
            self.new_session = False

        self.last_state_creation_time = current_state['creation_date_time']
        deserialized_current_state = {k: jsonpickle.decode(v) for k, v in turn_result.current_state.items()}

        return response, deserialized_current_state


def main():
    user_id = "user_001",
    conversation_id = "conversation_001",
    session_id = "session_001",
    intent = "LaunchRequest",

    local_agent = LocalAgent()
    user_input = ""
    while user_input != "bye":
        user_input = input()
        response, deserialized_current_state = local_agent.process_utterance(user_input)
        print(response)



if __name__=='__main__':
    main()