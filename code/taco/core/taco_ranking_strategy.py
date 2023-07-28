from injector import inject

import sys
sys.path.insert(0, '/home/tai.97/github/tacobot_v2/taco/core/')

from taco_logger import LoggerFactory
from taco_state_manager import StateManager
from typing import List
from taco_offensive_speech_classifier import OffensiveSpeechClassifier

class RankingStrategy(object):
    """
    The BaseRankingStrategy returns the first element in a list of candidate responses. 
    
    In the case of a PolicySelectingStrategy or similar architecture where the optimal response mode is 
    determined prior to invoking ResponseGenerators, this default behavior is adequate.
    
    In the case of a Cobot implementation focused on generating multiple candidate responses and selecting
    optimal responses based on topical or semantic coherence, information content metrics, predicted engagement
    based on textual response analysis, much of the "heavy lifting" of the dialog strategy may occur in a
    metric-focused implementation of the RankingStrategy interface.
    """

    @inject
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.logger = LoggerFactory.setup(self)

    def rank(self, output_responses):
        # type: (List[str]) -> str
        """
        From a list of candidate responses, return a single, best response based on a ranking mechanism
        """
        self.logger.info('Rank 1st from {}'.format(output_responses))
        return output_responses[0]

    def rank_advanced(self, candidate_responses: dict) -> str:
        return self.rank(list(candidate_responses.values()))



class TacoRankingStrategy(RankingStrategy):
    """
    Simple priority ranking strategy
    """

    def rank_advanced(self, candidate_responses: dict) -> str:
        # No valid response : return help info
        final_response = candidate_responses.pop('ERROR_RESPONDER', None)
        final_responder = 'ERROR_RESPONDER'

        if 'STOP_RESPONDER' in candidate_responses.keys():
            setattr(self.state_manager.current_state, 'final_responder', 'STOP_RESPONDER')
            return candidate_responses.pop('STOP_RESPONDER', '')
            
        responder_name, response = self._handle_bad_user(candidate_responses)
        if response is not None:
            final_responder = responder_name
            final_response = response
        elif 'I think you said cancel multiple times' in final_response:
            setattr(self.state_manager.current_state, 'final_responder', final_responder)
            print('Final responder =>', final_responder)
            return final_response
        else:
            offensive_classifier = OffensiveSpeechClassifier(self.state_manager)
            intent = getattr(self.state_manager.current_state, 'final_intent', None)
            current_state = getattr(self.state_manager.user_attributes, 'taco_state', None)

            print(f'RG select intent => {intent}')
            print(f'RG select init state => {current_state}')

            responder_name, response = self._ranking_rules(
                candidate_responses, offensive_classifier, intent, current_state)
            
            # should have only one response left, if not error
            if response is None and candidate_responses and len(candidate_responses) == 1: 
                responder_name = list(candidate_responses.keys())[0]
                response = candidate_responses[responder_name]
                
            response = self._filter_privacy_keywords(response)
            if response is not None:
                final_responder = responder_name
                final_response = response

        setattr(self.state_manager.current_state, 'final_responder', final_responder)
        print('Final responder =>', final_responder)
        return final_response

    def _ranking_rules(self, candidate_responses, offensive_classifier, intent, current_state):
        responder_name = ''
        response = None

        if 'HELP_RESPONDER' in candidate_responses:
            responder_name = 'HELP_RESPONDER'
            response = candidate_responses.pop('HELP_RESPONDER', None)
        elif current_state == 'RequestHandler':
            responder_name, response = self._handle_task_req(candidate_responses, offensive_classifier)
        elif current_state in ['TaskChoice', 'TaskChoiceInfo']:
            responder_name, response = self._handle_task_choice(candidate_responses)
        elif current_state == 'TaskDetails':
            responder_name, response = self._handle_task_details(candidate_responses)
        elif intent and 'QuestionIntent' in intent:
            responder_name, response = self._handle_question(candidate_responses, offensive_classifier)
        
        return responder_name, response

    def _handle_bad_user(self, candidate_responses):
        bad_task = candidate_responses.pop('BAD_TASK_RESPONDER', None)
        if bad_task:
            self._reset_user_attrs()
            return 'BAD_TASK_RESPONDER', bad_task

        #inappropriate_response = candidate_responses.pop('taskfilter', None)
        #if inappropriate_response:
        #    self._reset_user_attrs()
        #    return inappropriate_response

        sensitive_response = candidate_responses.pop('SENSITIVE_RESPONDER', None)
        if sensitive_response:
            last_taco_state = getattr(
                self.state_manager.user_attributes, 'last_taco_state', None)
            setattr(self.state_manager.user_attributes,
                    'taco_state', last_taco_state)
            return 'SENSITIVE_RESPONDER', sensitive_response

        return '', None

    def _reset_user_attrs(self):
        setattr(self.state_manager.user_attributes,
                    "recipe_query_result", None)
        setattr(self.state_manager.user_attributes,
                    "wikihow_query_result", None)
        setattr(self.state_manager.user_attributes, "current_task", None)
        setattr(self.state_manager.user_attributes, "current_step", None)
        setattr(self.state_manager.user_attributes, "list_item_selected", None)
        setattr(self.state_manager.user_attributes, "started_cooking", None)
        setattr(self.state_manager.user_attributes, 'taco_state', None)
        setattr(self.state_manager.user_attributes, 'query_wikihow', None)
        setattr(self.state_manager.user_attributes, 'query_recipe', None)
        setattr(self.state_manager.user_attributes, 'confirmed_query', None)

    def _handle_task_req(self, candidate_responses, offensive_classifier):
        evi_response = candidate_responses.pop('EVI_QUERY_RESPONSER', None)
        need_filter = False

        rec_response = candidate_responses.pop('RECIPE_REC_RESPONDER', None)
        responder = 'RECIPE_REC_RESPONDER'
        if not rec_response:
            rec_response = candidate_responses.pop('WIKIHOW_REC_RESPONDER', None)
            responder = 'WIKIHOW_REC_RESPONDER'
        if not rec_response:
            rec_response = candidate_responses.pop('REC_HANDLER_RESPONDER', None)
            responder = 'REC_HANDLER_RESPONDER'

        if evi_response:
            try:
                need_filter = offensive_classifier.classify([evi_response])
            except:
                need_filter = False
            need_filter = need_filter[0] if need_filter else False
        
        if candidate_responses and len(candidate_responses) > 0:
            # Pick the first available non-offensive response after removing Sensitive response
            responder = list(candidate_responses.keys())[0]
            response = candidate_responses[responder]
            
            setattr(self.state_manager.user_attributes, 'taco_state', 'TaskChoice')
            print('RG state transit => TaskChoice')
            setattr(self.state_manager.user_attributes, 'evi_query_result', None)
            return responder, response
        elif rec_response:
            setattr(self.state_manager.user_attributes, 'taco_state', 'Recommender')
            print('RG state transit => Recommender')
            setattr(self.state_manager.user_attributes, 'evi_query_result', None)
            return responder, rec_response
        elif evi_response and (not need_filter):
            setattr(self.state_manager.user_attributes, 'taco_state', 'EVI_Handler')
            setattr(self.state_manager.user_attributes, 'first_visit', True)
            setattr(self.state_manager.user_attributes, 'use_evi', True)
            print('RG state transit => EVI_Handler')
            return 'EVI_QUERY_RESPONSER', evi_response

        return '', None

    def _handle_task_choice(self, candidate_responses):
        if candidate_responses and len(candidate_responses) == 1: 
            responder = list(candidate_responses.keys())[0]
            response = candidate_responses[responder]

            if 'Do you want to choose it' in response:
                setattr(self.state_manager.user_attributes, 'taco_state', 'TaskChoiceInfo')
                print('RG state transit => TaskChoiceInfo')
            else:
                setattr(self.state_manager.user_attributes, 'taco_state', 'TaskChoice')
                print('RG state transit => TaskChoice')
            return responder, response

        return '', None

    def _handle_task_details(self, candidate_responses):
        if candidate_responses and len(candidate_responses) == 1: 
            responder = list(candidate_responses.keys())[0]
            response = candidate_responses[responder]

            if ('We can also continue the task if you say next' in response or
                'We can move on if you say next' in response):
                print('transition @ ranking 159')
                setattr(self.state_manager.user_attributes, 'taco_state', 'TaskExecution')
                print('RG state transit => TaskExecution')
            return responder, response

        return '', None

    def _handle_question(self, candidate_responses, offensive_classifier):
        step_qa_response = candidate_responses.pop('STEP_QA_RESPONDER', None)
        if step_qa_response:
            return 'STEP_QA_RESPONDER', step_qa_response

        question_types = getattr(self.state_manager.current_state, 'questiontype', None)

        if question_types:
            print('[question types]: ', question_types['question_types'])
        else:
            print('[question types]: None')

        type2responder = {
            "MRC": 'mrc',
            "FAQ":'faq',
            "EVI":'EVI_RESPONDER',
            "SubstituteQuestion": 'SUB_QA_RESPONDER',
            "IngredientQuestion": 'INGREDIENT_QA_RESPONDER',
        }

        if question_types is not None and 'question_types' in question_types:
            order = []
            for type in question_types['question_types']:
                order.append(type2responder[type])

            for responder in type2responder.values():
                if responder not in order:
                    order.append(responder)

            order += ['IDK_RESPONDER']

            print('[QA Responder order]: ',order)

            for k, responder in enumerate(order):
                cur_response = candidate_responses.pop(responder, None)
                if cur_response:

                    # skip these two responders if the they are not in the top-2
                    if k >= 2 and responder in ['SUB_QA_RESPONDER', 'INGREDIENT_QA_RESPONDER']:
                        continue

                    #that means we find something that we are not super confident
                    need_filter = False
                    if responder == 'EVI_RESPONDER':
                        try:
                            need_filter = offensive_classifier.classify([cur_response])
                        except:
                            need_filter = False
                        need_filter = need_filter[0] if need_filter else False

                    if k > 0 and responder != 'IDK_RESPONDER':
                        cur_response = "let me try giving an answer, but I am not so sure of it. " + cur_response

                    if not need_filter:
                        return responder, cur_response

        return '', None
        
    def _filter_privacy_keywords(self, response):
        PRIVACY = [
            "aadhaar number",
            "aadhar card number",
            "account password",
            "bank account",
            "business id number",
            "business identification number",
            "credit card",
            "credit card number",
            "debit card",
            "debit card number",
            "dl number",
            "driver's license number",
            "driving license number",
            "european health insurance card",
            "fiscal code",
            "genetic test result",
            "health insurance card number",
            "health insurance number",
            "identity card number",
            "insee code",
            "medical card number",
            "national health index number",
            "national health insurance number",
            "national health service number",
            "national id number",
            "national identity document",
            "national identity number",
            "national insurance number",
            "nhi number",
            "nie number",
            "office id card number",
            "pan card number",
            "pan number",
            "passport number",
            "pension insurance number",
            "permanent account number",
            "personal account",
            "pin number",
            "salary account",
            "savings account",
            "social insurance number",
            "social security number",
            "ssn",
            "tax file number",
            "tax identification number",
            "tds number",
            "unique population registry code",
            "vehicle registration number",
            "vehicle registration plate number",
            "voter id number",
            "voter identification number",
            "voting identification number",
            "password"
        ]
        detect_keyword = lambda x, k: (k in x) if ' ' in k else (k in x.split())

        segs = response.split('. ')
        final_segs = []
        return_seg = False
        for s in segs:
            final_segs.append(s)
            s_lower = s.lower()
            for keyword in PRIVACY:
                if detect_keyword(s_lower, keyword):
                    final_segs.pop(-1)
                    return_seg = True
                    print(keyword)
                    break
        
        if return_seg:
            return '. '.join(final_segs)
        else:
            return response


# if __name__ == '__main__':
#     class Dummy:
#         def __init__(self, **kwargs):
#             for key, value in kwargs.items():
#                 setattr(self, key, value)

#     class DummyState(Dummy):
#         supported_interfaces = {}

#         def __contains__(self, item):
#             return item in self.__dict__

    
#     state_manager = DummyState(current_state='')
#     test_module = TacoRankingStrategy(state_manager)
#     print(test_module._filter_privacy_keywords('Remember that the ssn of others does not constitute an emergency on your part. They will need to learn to stay on top of their own responsibilities. '))
#     print(test_module._filter_privacy_keywords('Remember that the carelessness of others does not constitute an emergency on your part. They will need to learn to stay on top of their own responsibilities. '))
#     print(test_module._filter_privacy_keywords('Some dummy words. Your eight (8) digit Driver\'s License Number. See the samples below.'))
#     print(test_module._filter_privacy_keywords('In Columbus, the SSA is located at 200 N. High Street. The Social Security Administration (SSA) issues the SSN. '))
    