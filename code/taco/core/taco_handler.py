import logging
from dataclasses import dataclass

from taco.core.callables import Annotator, AnnotationDAG, ResponseGenerators
from chirpy.core.response_generator import ResponseGenerator
from taco.core.latency import measure
from taco.core.regex.templates import StopTemplate
from .taco_state import State
from .taco_state_manager import StateManager
# from chirpy.core.priority_ranking_strategy import PriorityRankingStrategy
from .taco_selecting_strategy import TacoSelectingStrategy
from .taco_ranking_strategy import TacoRankingStrategy
from .taco_offensive_speech_classifier import OffensiveSpeechClassifier
from .taco_output_responses_converter import OutputResponsesConverter
from .taco_nlp_pipeline import ResponseGeneratorsRunner

from .taco_user_attributes import UserAttributes
from .taco_dialogue_manager import DialogManager
from typing import List, Type, Optional, Dict
from taco.annotators.navigational_intent.navigational_intent import NavigationalIntentOutput
from injector import Injector
from injector import inject, singleton

StateTableName = 'StateTable'

logger = logging.getLogger('tacologger')

# NOTE: disable immediate stopping via dialogact to increase precision.
# High-probability "closing" prediction via dialogact will be handled by CLOSING_CONFIRMATION RG.
CLOSING_HIGH_CONFIDENCE_THRESHOLD = 1
DEFAULT_MAX_SESSION_HISTORY_COUNT = 50 # TODO: find me a better home

@dataclass
class TurnResult:
    response: str
    should_end_session: bool
    current_state: Dict[str, str]
    user_attributes: Dict[str, str]

    @classmethod
    def from_namespaces(cls, current_state: State, user_attributes: UserAttributes):
        return cls(current_state.response,
                   current_state.should_end_session,
            current_state.serialize(),
            user_attributes.serialize())

class Handler():
    @measure
    def __init__(self, annotator_classes: List[Type[Annotator]], response_generator_classes: List[Type[ResponseGenerator]],
                 annotator_timeout = 3):
        """
        """
        self.annotator_classes = annotator_classes
        self.response_generator_classes = response_generator_classes
        self.annotator_timeout = annotator_timeout

    def should_end_conversation(self, text):
        """Determines whether we should immediately end the conversation, rather than running the bot"""
        if StopTemplate().execute(text) is not None:
            logger.primary_info('Received utterance matching StopTemplate, so ending conversation')
            return True
        else:
            return False

    @measure
    def execute(self, current_state:dict, user_attributes:dict, last_state:Optional[dict]=None, test_args=None) -> TurnResult:
        print('***current_state: ', current_state)
        # current_state:  {'creation_date_time': '"2022-09-27T17:50:12.444289"', 'pipeline': '""', 'commit_id': '""', 'session_id': '"2ba957c77ca949b68dd58f10fe2ec703"', 'user_id': '"1"', 'text': '"Hi"'}
        current_state = State.deserialize(current_state)
        user_attributes = UserAttributes.deserialize(user_attributes)
        # if last_state:
        #     last_state = State.deserialize(last_state)
        #     current_state.update_from_last_state(last_state)
        # state_manager = StateManager(current_state, user_attributes, last_state)
        table_name = "state_table_name"
        state_manager = StateManager(table_name, user_attributes, current_state)
        offensive_speech_classifier = OffensiveSpeechClassifier()
        # output_response_converter = OutputResponsesConverter()
        # response_generatator_runner = ResponseGeneratorsRunner()

        if self.should_end_conversation(current_state.text):
            response, should_end_session = None, True
        else:
            response_generators = ResponseGenerators(state_manager, self.response_generator_classes)
            annotator_objects = [c(state_manager) for c in self.annotator_classes]
            annotation_dag = AnnotationDAG(state_manager, annotator_objects, self.annotator_timeout) # TODO

            ranking_strategy = TacoRankingStrategy(state_manager)
            selecting_strategy = TacoSelectingStrategy(state_manager)

            # step1. ranking and selecting_strategy
            # step2. feed generate dialog_manger
            # step3. dialog_manger.select_response call candidate rp
            # step4. rp feed ranking

            # data format

            # dialog_manager = DialogManager(state_manager, selecting_strategy, ranking_strategy, \
            #     offensive_speech_classifier, output_response_converter, response_generatator_runner)
            dialog_manager = DialogManager(state_manager, selecting_strategy, ranking_strategy, \
                offensive_speech_classifier, response_generators)

            if test_args:
                state_manager.current_state.test_args = test_args

                if test_args.selected_prompt_rg:
                    logger.info("Updating the probability distribution of the prompt ranking strategy.")
                dialog_manager.ranking_strategy.save_test_args(test_args)

                if test_args.experiment_values:
                    logger.info("Overriding experiment values as given by test_argss")
                    for experiment, value in test_args.experiment_values.items():
                        state_manager.current_state.experiments.override_experiment_value(experiment, value)

            logger.info('Running the NLP pipeline...')

            # run the NLP pipeline. this saves the annotations to state_manager.current_state
            # annotation_dag.run_multithreaded_DAG(last_state) # TODO
            logger.info('Finished running the NLP pipeline.')

            # If is_question=True, set navigational intent to none
            # We used to do this inside navigational intent module, but the NLP pipeline dependencies (question -> nav intent -> entity linker) caused problems
            if hasattr(state_manager.current_state, 'question') and state_manager.current_state.question is not None:
                is_question = state_manager.current_state.question['is_question']
                if is_question and not state_manager.current_state.text.startswith('why would'):
                    logger.primary_info(f"user utterance is marked as is_question, so setting navigational_intent to none")
                    state_manager.current_state.navigational_intent = NavigationalIntentOutput()

            closing_probability = 0
            if hasattr(state_manager.current_state, 'dialogact') and state_manager.current_state.dialogact is not None:
                closing_probability = state_manager.current_state.dialogact['probdist']['closing']

            if closing_probability > CLOSING_HIGH_CONFIDENCE_THRESHOLD: # If closing detected with high confidence, end conversation immediately
                logger.primary_info('Stopping the conversation since "dialogact" is "closing" with probability {}'.format(closing_probability))
                response, should_end_session, directives = None, True, None

            else:
                features = None # dummy features
                response, should_end_session, directives = dialog_manager.select_response(features)  # str, bool

        setattr(state_manager.current_state, 'response', response)
        setattr(state_manager.current_state, 'should_end_session', should_end_session)
        return TurnResult.from_namespaces(state_manager.current_state, state_manager.user_attributes)
