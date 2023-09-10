import logging
from taco.core.regex.regex_template import RegexTemplate
from taco.response_generators.food.regex_templates import DoubtfulTemplate
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.core.entity_linker.entity_groups import EntityGroupsForExpectedType
from taco.core.util import infl
from cobot_core.service_module import ToolkitServiceModule

from taco.response_generators.taco_rp.qa.state import State, ConditionalState
import requests
import random

logger = logging.getLogger('tacologger')

"""
A sample response generator using EVI question answering API with QA classification models.
It calls EVI API to get an answer to an utterance and uses QA classification models to decide whether the response is good or not.
"""

TIMEOUT_IN_MILLIS = 2000
RR_LABEL_GOOD = "1"
RR_LABEL_BAD = "0"
QA_FACTOID_LABEL = "QA_FACTOID_LABEL"
QA_RESPONSE_RELEVANCE_LABEL = "QA_RESPONSE_RELEVANCE_LABEL"

CONFIDENCE_HIGH = 'confidence_high'
CONFIDENCE_MEDIUM = 'confidence_medium'
CONFIDENCE_LOW = 'confidence_low'

# For queries like 'hello', EVI returns a long meaningless string that usually contains a skill ID starting with
# 'skill://'.
# what is the news on corona virus - evi response - Audio: AP News Update COVID-19.mp3
# If any of these are a substring of the EVI response, we discard the response.
# We check for these: (a) ignoring case, (b) ignoring word boundaries (i.e. we just check str.contains()).
RESPONSE_NOT_ALLOWED_SUBSTRINGS = {
    'Alexa,',
    'skill://',
    'Audio:',
    'please say that again',
    'please try that again',
    'catch that',
    'find the answer to the question I heard',
    'I didn’t get that',
    'have an opinion on that',
    'skill',
    'skills',
    'you can',
    'try asking',
    "Here's something I found on",
    'Sorry, I don’t know that'
}

_sessions = requests.Session()


class TacoEVI(ToolkitServiceModule):

    def execute(self, state_manager):
        text = state_manager.current_state.text
        evi_response = self._call_evi_service(text)
        fc_response, rr_response = self._call_qa_classification_service(text, evi_response)
        evi_response = self.process_response(evi_response)
        confidence = self.get_confidence(evi_response, fc_response, rr_response)
        if evi_response and (confidence == CONFIDENCE_HIGH):
            return evi_response
        else:
            return ''

    @staticmethod
    def create_qa_service_request(text, response):
        request = dict()
        request["turns"] = list()
        request["turns"].append([text, response])
        return request

    def _call_evi_service(self, current_text):
        # Call Evi service
        # Input is a text. Timeout parameter is optional and the client timeout value is used if it's not set.
        try:
            result = self.toolkit_service_client.get_answer(
                question=current_text, timeout_in_millis=TIMEOUT_IN_MILLIS)
            response = result['response']
        except Exception as ex:
            if current_text != '':
                self.logger.exception("An exception while calling QA service",
                                      exc_info=True)
            response = ""
        return response

    def _call_qa_classification_service(self, text, response):
        fc = False
        rr = RR_LABEL_BAD
        request = self.create_qa_service_request(text, response)
        try:
            result = self.toolkit_service_client.get_qa_factoid_response_relevance_results(request)
            fc = result['qa_factoid_classifier_results']['results'][0]
            rr = result['qa_response_relevance_classifier_results']['results']['label']
            self.logger.debug('QA Factoid classifier returned => %s, QA Response Relevance Classifier => %s', fc, rr)
        except Exception as ex:
            self.logger.exception("An exception while calling qa classification service request",
                                  exc_info=True)
        return fc, rr

    @staticmethod
    def get_confidence(evi_response, fc_response, rr_response):
        """
        Get confidence about the appropriateness of EVI response. In real use case, it can be modified to return
        a numeric value that can be used for ranking by custom ranking strategy.
        """
        confidence = CONFIDENCE_LOW
        if evi_response and fc_response:
            confidence = CONFIDENCE_HIGH
        elif evi_response and not fc_response and rr_response == RR_LABEL_GOOD:
            confidence = CONFIDENCE_HIGH
        elif evi_response:
            confidence = CONFIDENCE_MEDIUM
        return confidence

    @staticmethod
    def process_response(response):
        """
        :param response: check if response contains any not_allowed phrase. Evi qa api sometimes returns not_allowed responses.
         We don't want to use them
        :return:
        """
        if response and any(string.lower() in response.lower() for string in RESPONSE_NOT_ALLOWED_SUBSTRINGS):
            return ""

        return response if response else ''


class EVI_qa_Treelet(Treelet):
    name = "EVI_qa_treelet"
    
    Taco_EVI = TacoEVI()
    
    def classify_user_response(self):
        assert False, "This should never be called."


    def get_response(self, state_manager, priority=ResponsePriority.WEAK_CONTINUE, **kwargs) -> ResponseGeneratorResult:
        """ Returns the response. """
        state, utterance, response_types = self.get_state_utterance_response_types()
        
        response = Taco_EVI.execute(state)
        
        return ResponseGeneratorResult(text=response, priority=priority,
                                       needs_prompt=False, state=state, cur_entity=None,
                                       conditional_state=ConditionalState(
                                           prompt_treelet=self.name,))

    def get_best_candidate_user_entity(self, utterance, cur_food):
        def condition_fn(entity_linker_result, linked_span, entity):
            return EntityGroupsForExpectedType.food_related.matches(entity) and entity.name != cur_food
        entity = self.rg.state_manager.current_state.entity_linker.top_ent(condition_fn) or self.rg.state_manager.current_state.entity_linker.top_ent()
        if entity is not None:
            user_answer = entity.talkable_name
            plural = entity.is_plural
        else:
            nouns = self.rg.state_manager.current_state.corenlp['nouns']
            if len(nouns):
                user_answer = nouns[-1]
                plural = True
            else:
                user_answer = utterance.replace('i like', '').replace('my favorite', '').replace('i love', '')
                plural = True

        return user_answer, plural

