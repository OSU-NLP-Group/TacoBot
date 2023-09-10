from collections import defaultdict

import datetime
import jsonpickle
import logging
import os
import uuid
import time
import json
from typing import Dict

from taco.response_generators.launch.launch_response_generator import LaunchResponseGenerator
from taco.response_generators.fallback.fallback_response_generator import FallbackResponseGenerator
from taco.response_generators.wiki2.wiki_response_generator import WikiResponseGenerator
from taco.response_generators.food.food_response_generator import FoodResponseGenerator
from taco.response_generators.opinion2.opinion_response_generator import OpinionResponseGenerator2
from taco.response_generators.neural_chat.neural_chat_response_generator import NeuralChatResponseGenerator
from taco.response_generators.categories.categories_response_generator import CategoriesResponseGenerator
from taco.response_generators.neural_fallback.neural_fallback_response_generator import NeuralFallbackResponseGenerator
from taco.response_generators.closing_confirmation.closing_confirmation_response_generator import ClosingConfirmationResponseGenerator

from taco.response_generators.acknowledgment.acknowledgment_response_generator import AcknowledgmentResponseGenerator
from taco.response_generators.personal_issues.personal_issues_response_generator import PersonalIssuesResponseGenerator
from taco.response_generators.aliens.aliens_response_generator import AliensResponseGenerator
from taco.response_generators.transition.transition_response_generator import TransitionResponseGenerator

from taco.annotators.corenlp import CorenlpModule
from taco.annotators.navigational_intent.navigational_intent import NavigationalIntentModule
from taco.annotators.stanfordnlp import StanfordnlpModule
from taco.annotators.coref import CorefAnnotator
from taco.annotators.emotion import EmotionAnnotator
from taco.annotators.g2p import NeuralGraphemeToPhoneme
from taco.annotators.gpt2ed import GPT2ED
from taco.annotators.question import QuestionAnnotator
from taco.annotators.blenderbot import BlenderBot
import taco.core.flags as flags
from taco.core.util import get_function_version_to_display
from taco.annotators.dialogact import DialogActAnnotator
from taco.core.entity_linker.entity_linker import EntityLinkerModule

import taco.core.flags as flags
from taco.core.latency import log_events_to_dynamodb, measure, clear_events
from taco.core.regex.templates import StopTemplate
from taco.core.handler import Handler
from taco.core.logging_utils import setup_logger, update_logger, PROD_LOGGER_SETTINGS

########################################################################################

from taco.annotators.neuralintent import NeuralIntent
from taco.annotators.nounphrases import NounPhrases
from taco.annotators.questiontype import QuestionType
from taco.annotators.recipesearch import RecipeSearch
from taco.annotators.taskfilter import Taskfilter
from taco.annotators.docparse import Docparse
from taco.annotators.tasksearch import TaskSearch
from taco.annotators.tasktype import TaskType
from taco.annotators.template import Template


from taco.core.user_attributes import TMP_DOCUMENT_DATA, TMP_STEP_DATA

from taco.response_generators.taco_rp.welcome.welcome_response_generator import Lanuch_Generator
from taco.response_generators.taco_rp.preparation.preparation_response_generator import preparation_Generator
from taco.response_generators.taco_rp.list.list_response_generator import list_Generator
from taco.response_generators.taco_rp.qa.qa_response_generator import QA_Generator
from taco.response_generators.taco_rp.ingredient_qa.ingredient_response_generator import INGREDIENT_Generator
from taco.response_generators.taco_rp.halt.halt_response_generator import halt_Generator
from taco.response_generators.taco_rp.execution.execution_response_generator import execution_Generator
from taco.response_generators.taco_rp.exception.exception_response_generator import Exception_ResponseGenerator
from taco.response_generators.taco_rp.choice.choice_response_generator import choice_ResponseGenerator
from taco.response_generators.taco_rp.remote_qa.qa_response_generator import Remote_QA_Generator
from taco.response_generators.taco_rp.utils.utils_response_generator import utils_Generator


########################################################################################

# Timeout at the highest level, as close as possible to 10 seconds. Do nothing after, just create an apologetic
# response and send it over
OVERALL_TIMEOUT = 9.75 if flags.use_timeouts else flags.inf_timeout  # seconds

# Timeout for final_response function. Set at 9.35 seconds to comfortably log the latencies
FINAL_RESPONSE_TIMEOUT = 9.35 if flags.use_timeouts else flags.inf_timeout  #seconds

# Timeout for progressive response
PROGRESSIVE_RESPONSE_TIMEOUT = 10 if flags.use_timeouts else flags.inf_timeout  #seconds

# Timeout for NLP Pipeline
NLP_PIPELINE_TIMEOUT = 1000 if flags.use_timeouts else flags.inf_timeout  #seconds

LATENCY_EXPERIMENT = False
LATENCY_BINS = [0, 1, 1.5, 2, 2.5]

DEFAULT_REPROMPT = "Sorry, I don't think I understood. Could you repeat that please?".strip()

logger = logging.getLogger('tacologger')


apology_string = 'Sorry, I\'m having a really hard time right now. ' + \
'I have to go, but I hope you enjoyed our conversation so far. ' + \
'Have a good day!'

state_store = {}
user_store = defaultdict(dict)

class StateTable:
    def __init__(self,session_id,  debug = False):
        self.session_id = session_id
        self.table_name = 'StateTable'
        debug = False
        self.debug = debug
        self.c_step = 0

    def fetch(self, session_id, creation_date_time):

        if session_id is None:
            return None
        try:
            item = None
            start_time = time.time()
            timeout = 2 #second

            while (item is None and time.time() < start_time + timeout):
                a = list(state_store.keys())[0]
                Q = '"'
                return state_store[(Q + session_id + Q, creation_date_time)]
            if item is None:
                pass
            else:
                return item
        except:
            logger.error("Exception when fetching last state")
            return None

    def persist(self, state: Dict):
        self.c_step += 1

        n_state = {}
        for k in state:
            if k in ['status', 'last_status', 'recipe_rec_cat', 'clarify', 'is_rec', 'response_generator_states', 'selected_response_rg',
                    'search_timeout', 'no_result', 'selected_prompt_rg', 'text', 'response', 'response_results', 'active_rg', 'entity_tracker']:
                n_state[k] = state[k]

        global state_store
        state_store[(state['session_id'], state['creation_date_time'])] = n_state
        return True


class UserTable():
    def __init__(self, user_id, debug = False):
        self.user_id = user_id
        self.table_name = 'UserTable'
        debug = False
        self.debug = debug
        self.c_step = 0

    def fetch(self, user_id):
        logger.debug(
            f"user_table fetching last state for user {user_id} from table {self.table_name}")
        if user_id is None:
            return None
        

        item = None
        start_time = time.time()
        timeout = 2  # second

        while (item is None and time.time() < start_time + timeout):
            item = user_store[user_id]
        if item is None:
            logger.error(
                f"Timed out when fetching user attributes\nfor user_id {user_id} from table {self.table_name}.")
        else:
            return item

        logger.error("Exception when fetching user attributes from table: " + self.table_name,
                        exc_info=True)
        return None

    def persist(self, user_attributes: Dict) -> None:
        """
        This will take the provided user_preferences object and persist it to DynamoDB. It does this by creating
                a dictionary representing the DynamoDB item to push consisting of user_id and a dictionary representing all of
                the user preferences.
        :param user_attributes: input UserAttributes object
        :return: None
        """

        assert 'user_id' in user_attributes
        global user_store
        user_store[self.user_id] = user_attributes
        return True

class LocalAgent():
    """
    Agent that inputs and outputs text, and runs callables locally.
    """
    def __init__(self, debug = False):
        self.session_id = uuid.uuid4().hex
        debug = True
        self.user_id = self.session_id

        self.state_table = StateTable(self.session_id, debug = debug)
        self.user_table = UserTable(self.user_id, debug = debug)

        self.new_session = True
        self.last_state_creation_time = None

    def should_end_session(self, turn_result):
        return turn_result.should_end_session

    def should_launch():
        return True

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
        state_attributes['status'] = 'Welcome'
        state_attributes['supported_interfaces'] = {}
        # Welcome
        state_attributes = {k: jsonpickle.encode(v) for k, v in state_attributes.items()}
        return state_attributes

    def get_user_attributes(self):
        user_attributes = self.user_table.fetch(self.user_id)
        if user_attributes == None: user_attributes = {}

        user_attributes['user_id'] = self.user_id
        user_attributes['user_timezone'] = None
        
        user_attributes = {k: jsonpickle.encode(v) if k in ['user_id', 'user_timezone'] else v for k, v in user_attributes.items()}
        return user_attributes

    def get_last_state(self): # figure out new session and session_id
        if not self.new_session or True:
            last_state = self.state_table.fetch(self.session_id, self.last_state_creation_time)
        else:
            last_state = None
        return last_state

    def create_handler(self):
        return Handler(
            response_generator_classes=[LaunchResponseGenerator, FallbackResponseGenerator,
                                            NeuralChatResponseGenerator,
                                            NeuralFallbackResponseGenerator,
                                            CategoriesResponseGenerator,
                                            AcknowledgmentResponseGenerator,
                                            PersonalIssuesResponseGenerator,
                                            OpinionResponseGenerator2,
                                            AliensResponseGenerator,
                                            TransitionResponseGenerator,
                                            FoodResponseGenerator,
                                            WikiResponseGenerator,
                                            Lanuch_Generator,
                                            preparation_Generator,
                                            QA_Generator,
                                            INGREDIENT_Generator,
                                            halt_Generator,
                                            Remote_QA_Generator,
                                            execution_Generator,
                                            Exception_ResponseGenerator,
                                            choice_ResponseGenerator,
                                            utils_Generator
                                           ],

            annotator_classes=[DialogActAnnotator, NavigationalIntentModule, CorenlpModule, Docparse, NeuralIntent, NounPhrases,
                        EntityLinkerModule, BlenderBot, QuestionType, RecipeSearch, Taskfilter, TaskSearch, TaskType, Template],
            annotator_timeout = NLP_PIPELINE_TIMEOUT
        )

    def process_utterance(self, user_utterance):
        # create handler (pass in RGs + annotators)
        handler = self.create_handler()

        current_state = self.get_state_attributes(user_utterance)
        user_attributes = self.get_user_attributes()
        last_state = self.get_last_state()

        turn_result = handler.execute(current_state, user_attributes, last_state)
        response = turn_result.response

        self.user_table.persist(turn_result.user_attributes)
        self.state_table.persist(turn_result.current_state) 

        if self.new_session:
            self.new_session = False

        self.last_state_creation_time = current_state['creation_date_time']

        deserialized_current_state = {}
        for k, v in turn_result.current_state.items():
            if k == 'should_end_session':
                print('k = ', k)
                deserialized_current_state[k] = jsonpickle.decode(v)

        # deserialized_current_state = {k: jsonpickle.decode(v) for k, v in turn_result.current_state.items() if k != 'cache'}

        return response, deserialized_current_state


def lambda_handler():
    local_agent = LocalAgent()
    k = 0
    while user_input != "bye":
        user_input = input()
        if k == 0: user_input = "let's work together"

        response, deserialized_current_state = local_agent.process_utterance(user_input)
        print(response)
        k += 1
