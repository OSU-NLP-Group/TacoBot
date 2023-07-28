# import copy
# import logging
# from typing import Dict, List, Optional

# from chirpy.core.callables import run_multithreaded, ResponseGenerators
# # from chirpy.core.offensive_speech_classifier import OffensiveSpeechClassifier
# from chirpy.core.state_manager import StateManager
# from chirpy.core.priority_ranking_strategy import PriorityRankingStrategy
# from chirpy.core.flags import use_timeouts, inf_timeout
# from chirpy.core.priority_ranking_strategy import RankedResults
# from chirpy.core.response_generator_datatypes import ResponseGeneratorResult, PromptResult, UpdateEntity, CONTINUING_ANSWER_TYPES, is_killed
# from chirpy.core.util import print_dict_linebyline, sentence_join
# from chirpy.core.offensive_classifier.offensive_classifier import contains_offensive
# from chirpy.response_generators.closing_confirmation.closing_confirmation_response_generator import CLOSING_CONFIRMATION_STOP
# from chirpy.core.latency import measure


from injector import inject, singleton
from typing import Dict, Any, List
from taco_logger import LoggerFactory
from taco_nlp_pipeline import ResponseGeneratorsRunner # TODO
from taco_offensive_speech_classifier import OffensiveSpeechClassifier # TODO: can't use the API, develop our own model
from taco_output_responses_converter import OutputResponsesConverter
from taco_prompt_constants import Prompt
from taco_utils import map_two_lists
from taco_ranking_strategy import TacoRankingStrategy
from taco_selecting_strategy import TacoSelectingStrategy
from taco_state_manager import StateManager
from chirpy.core.response_generator import ResponseGenerator


@singleton
class DialogManager:
    """
    The default DialogManager class implements a generic flow for response generation in a Cobot implementation.
    
    The generic flow consists of a response mode selecting strategy, followed by high performance parallel invocation of
    all candidate response generator modules (which may be simple locally-hosted, rule-driven modules, complex retrieval
    systems or generative models hosted in long=lived independent Docker modules, or combinations of both). Finally,
    the list of candidate responses are filtered for offensive content, the best-ranked response is chosen and returned to
    the Handler for packaging and delivery to the Alexa Skills Kit API.
    
    **IMPORTANT NOTE**
    In many cases, a custom Cobot can be implemented with the default DialogManager flow, simply by injecting a specific 
    SelectingStrategy and/or RankingStrategy and implementing and registering appropriate ResponseGenerators. However, it 
    is also possible to override the DialogManager itself if, for example, a unified selection and ranking strategy is 
    desired that is not amenable to implementation in the default flow.    
    """

    @inject
    def __init__(self,
                 state_manager: StateManager,
                 selecting_strategy: TacoSelectingStrategy,
                 ranking_strategy: TacoRankingStrategy,
                 offensive_speech_classifier: OffensiveSpeechClassifier,
                 response_generators: ResponseGenerator
                #  output_responses_converter: OutputResponsesConverter,
                #  response_generator_runner: ResponseGeneratorsRunner
                 ) -> None:
        self.state_manager = state_manager
        self.selecting_strategy = selecting_strategy
        self.ranking_strategy = ranking_strategy
        self.offensive_speech_classifier = offensive_speech_classifier
        self.response_generators = response_generators
        # self.output_responses_converter = output_responses_converter
        # self.response_generator_runner = response_generator_runner
        self.logger = LoggerFactory.setup(self)

    def select_response(self, features):
        # type: (Dict[str,Any]) -> (str, bool, list)
        """
        Runs the entire dialog pipeline. In the case of the default DialogManager, this uses the currently configured SelectingStrategy, runs the resulting ResponseGenerators, and uses the configured RankingStrategy to choose the best candidate response.
        
        :param features: optional dict, with a subset of current_state from state_manager, to pass into the selecting_strategy
        """
        should_end_session = False
        directives = []

        if features is None:
            features = self.state_manager.current_state.features

        selected_response_generators = self.selecting_strategy.select_response_mode(features)
        self.logger.info('All selected RGs: %s', selected_response_generators)

        # output_responses_dict = self.response_generator_runner.run(selected_response_generators) # TODO: pipeline.py, ServiceModuleManager

        output_responses_dict = {"Responder1": "response1", "Responder2": "response2"} # dummy responses

        # Save all the response generators' responses in the state manager
        setattr(self.state_manager.current_state, 'candidate_responses', output_responses_dict)
        self.logger.info('Candidate Responses: %s', output_responses_dict)

        # responses_list, converted_output_responses_dict = self.output_responses_converter.convert(output_responses_dict)
        responses_list = ['response1', 'response2']
        converted_output_responses_dict = output_responses_dict

        # filtered_output_responses: List[str] = []
        # if len(responses_list) > 0:
        #     try:
        #         batch_profanity_result = self.offensive_speech_classifier.classify(responses_list)
        #         filtered_output_responses: List[str] = map_two_lists(responses_list, batch_profanity_result)
        #         self.logger.info('Filtered output responses before ranking: {}'.format(filtered_output_responses))
        #     except:
        #         filtered_output_responses = responses_list
        #         self.logger.error('Exception in Dialog Manager', exc_info=True)
        filtered_output_responses = responses_list

        if len(filtered_output_responses) > 1:
            response = self.rank_wrapper(converted_output_responses_dict, filtered_output_responses)
        elif len(filtered_output_responses) == 1:
            response = filtered_output_responses[0]
            self.logger.info("Selected response: {}".format(response))
        else:
            if self.state_manager.current_state.request_type == 'LaunchRequest':
                response = Prompt.welcome_prompt_followup
            else:
                response = Prompt.no_answer_prompt
            self.logger.info("No valid response after running all response generators")

        # Get the directives for the selected response, if any exist
        for output_response in output_responses_dict.values():
            if isinstance(output_response, dict) and output_response.get("response"):
                if response == output_response["response"]:
                    directives = output_response.get("directives", [])
                    should_end_session = output_response.get("shouldEndSession", False)
                    self.logger.info(
                        "Selected output dict - speak output: {}, directives: {}, shouldEndSession: {}".format(response,
                                                                                                          directives,
                                                                                                          should_end_session))
                    break

        self.logger.info("Final output - speak output: {}, directives: {}, shouldEndSession: {}".format(response, directives, should_end_session))
        return response, should_end_session, directives

    def rank_wrapper(self,
                     output_responses: dict,
                     filtered_output_responses: list):
        """
        Generates the ranking strategy's input and call ranking strategy to get the best response
        :param output_responses: candidate responses from response generators
        :param filtered_output_responses: non-offensive candidate responses in list
        :return:
        """
        response = self.ranking_strategy.rank(filtered_output_responses)
        return response