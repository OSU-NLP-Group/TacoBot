from injector import inject

import logging
import sys

from typing import List
from taco.core.state_manager import StateManager
# from taco_offensive_speech_classifier import OffensiveSpeechClassifier
from taco.core.priority_ranking_strategy import RankedResults
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.taco_offensive_speech_classifier import OffensiveSpeechClassifier
from taco.core.taco_selecting_utils import TACO2RP, RP2TACO

logger = logging.getLogger('tacologger')


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

    def rank(self, output_responses):
        # type: (List[str]) -> str
        """
        From a list of candidate responses, return a single, best response based on a ranking mechanism
        """
        logger.taco_merge('Rank 1st from {}'.format(output_responses))
        return output_responses[0]

    def rank_advanced(self, candidate_responses: dict) -> str:
        return self.rank(list(candidate_responses.values()))



class TacoRankingStrategy(RankingStrategy):
    """
    Simple priority ranking strategy
    """

    def rg_to_dic(self, tmp_candidate_responses):
        rg_states = self.state_manager.current_state.response_generator_states
        candidate_responses = {}

        logger.taco_merge(f'ranking candidate_responses = {[key for key in tmp_candidate_responses]}')
        for responder, value in tmp_candidate_responses.items():
            logger.taco_merge(f'responder = {responder}')
            
            cur_treelt = rg_states[responder].cur_treelet_str
            res_key = RP2TACO[responder][cur_treelt]
            candidate_responses[res_key] = value

        return candidate_responses

    def rank_advanced(self, candidate_responses: dict) -> str:
        # No valid response : return help info

        candidate_responses = self.rg_to_dic(candidate_responses)

        if 'STOP_RESPONDER' in candidate_responses.keys():
            candidate_responses['STOP_RESPONDER'].priority = ResponsePriority.STRONG_CONTINUE

        else:
            responder_name, response = self._handle_bad_user(candidate_responses)
            if response is not None:
                candidate_responses[responder_name].priority = ResponsePriority.STRONG_CONTINUE

            else:
                offensive_classifier = OffensiveSpeechClassifier()

                parsed_intent = getattr(self.state_manager.current_state, 'parsed_intent', None)
                current_status = getattr(self.state_manager.current_state, 'status', None)

                logger.taco_merge(f'RG select intent => {parsed_intent}')
                logger.taco_merge(f'RG select init current_status => {current_status}')

                print('candidate_responses = ', [ca for ca in candidate_responses])
                # input()
                responder_name = self._ranking_rules(
                    candidate_responses.copy(), offensive_classifier, parsed_intent, current_status)
                
                if responder_name != '':
                    logger.taco_merge(f'responder_name =  {responder_name}')
                    print('responder_name = ', responder_name)
                    print('candidate_responses = ', [ca for ca in candidate_responses])
                    # input()
                    candidate_responses[responder_name].priority = ResponsePriority.STRONG_CONTINUE


        priority_sorted_responses = sorted(candidate_responses.items(),
                                           key=lambda rg_and_response: (rg_and_response[1].priority,
                                                                        rg_and_response[1].tiebreak_priority),
                                           reverse=True)

        n_priority_sorted_responses = []
        for rg in priority_sorted_responses:
            if rg[0] in TACO2RP:
                rg_name = TACO2RP[rg[0]][0]
            n_priority_sorted_responses.append((rg_name,rg[1]))
        return RankedResults(n_priority_sorted_responses)

    def _ranking_rules(self, candidate_responses, offensive_classifier, intent, current_state):
        responder_name = ''
        response = None

        if 'HELP_RESPONDER' in candidate_responses:
            responder_name = 'HELP_RESPONDER'
        elif current_state == 'RequestHandler':
            responder_name, response = self._handle_task_req(candidate_responses, offensive_classifier)
        elif current_state in ['TaskChoice', 'TaskChoiceInfo']:
            responder_name, response = self._handle_task_choice(candidate_responses)
        elif current_state == 'TaskDetails':
            responder_name, response = self._handle_task_details(candidate_responses)
        elif intent and 'QuestionIntent' in intent:
            responder_name, response = self._handle_question(candidate_responses, offensive_classifier)
        
        return responder_name

    def _handle_bad_user(self, candidate_responses):
        # bad_task = candidate_responses.pop('BAD_TASK_RESPONDER', None)
        if 'BAD_TASK_RESPONDER' in candidate_responses:
            self._reset_attrs()
            return 'BAD_TASK_RESPONDER', candidate_responses["BAD_TASK_RESPONDER"]

        return '', None

    def _reset_attrs(self):
        setattr(self.state_manager.current_state, 'status', None)

        setattr(self.state_manager.user_attributes,
                    "recipe_query_result", None)
        setattr(self.state_manager.user_attributes,
                    "wikihow_query_result", None)
        setattr(self.state_manager.user_attributes, "current_task", None)
        setattr(self.state_manager.user_attributes, "current_step", None)
        setattr(self.state_manager.user_attributes, "list_item_selected", None)
        setattr(self.state_manager.user_attributes, "started_cooking", None)
        setattr(self.state_manager.user_attributes, 'query_wikihow', None)
        setattr(self.state_manager.user_attributes, 'query_recipe', None)
        setattr(self.state_manager.user_attributes, 'confirmed_query', None)

    def _handle_task_req(self, candidate_responses, offensive_classifier):

        need_filter = False
        responder = 'RECIPE_REC_RESPONDER'

        if 'EVI_QUERY_RESPONSER' in candidate_responses:
            evi_response = candidate_responses['EVI_QUERY_RESPONSER']

        if 'RECIPE_REC_RESPONDER' in candidate_responses:
            rec_response = candidate_responses['RECIPE_REC_RESPONDER']
        else:
            if 'WIKIHOW_REC_RESPONDER' in candidate_responses:
                rec_response = candidate_responses['WIKIHOW_REC_RESPONDER']
                responder = 'WIKIHOW_REC_RESPONDER'
            if 'REC_HANDLER_RESPONDER' in candidate_responses:
                rec_response = candidate_responses['REC_HANDLER_RESPONDER']
                responder = 'REC_HANDLER_RESPONDER'

        if evi_response:
            try:
                need_filter = offensive_classifier.classify([evi_response.text])
            except:
                need_filter = False
            need_filter = need_filter[0] if need_filter else False
        
        if candidate_responses and len(candidate_responses) > 0:
            # Pick the first available non-offensive response after removing Sensitive response
            responder = list(candidate_responses.keys())[0]
            response = candidate_responses[responder]
            
            setattr(self.state_manager.current_state, 'status', 'TaskChoice')
            print('RG state transit => TaskChoice')
            setattr(self.state_manager.user_attributes, 'evi_query_result', None)
            return responder
        elif rec_response:
            setattr(self.state_manager.current_state, 'status', 'Recommender')
            print('RG state transit => Recommender')
            setattr(self.state_manager.user_attributes, 'evi_query_result', None)
            return responder
        elif evi_response and (not need_filter):
            setattr(self.state_manager.current_state, 'status', 'EVI_Handler')
            setattr(self.state_manager.user_attributes, 'first_visit', True)
            setattr(self.state_manager.user_attributes, 'use_evi', True)
            print('RG state transit => EVI_Handler')
            return 'EVI_QUERY_RESPONSER', evi_response

        return '', None

    def _handle_task_choice(self, candidate_responses):
        if candidate_responses and len(candidate_responses) == 1: 
            responder = list(candidate_responses.keys())[0]
            response = candidate_responses[responder].text

            if 'Do you want to choose it' in response:
                setattr(self.state_manager.current_state, 'status', 'TaskChoiceInfo')
                print('RG state transit => TaskChoiceInfo')
            else:
                setattr(self.state_manager.current_state, 'status', 'TaskChoice')
                print('RG state transit => TaskChoice')
            return responder, response

        return '', None

    def _handle_task_details(self, candidate_responses):
        if candidate_responses and len(candidate_responses) == 1: 
            responder = list(candidate_responses.keys())[0]
            response = candidate_responses[responder].text

            if ('We can also continue the task if you say next' in response or
                'We can move on if you say next' in response):
                print('transition @ ranking 159')
                setattr(self.state_manager.current_state, 'status', 'TaskExecution')
                print('RG state transit => TaskExecution')
            return responder, response

        return '', None

    def _handle_question(self, candidate_responses, offensive_classifier):
        if 'STEP_QA_RESPONDER' in candidate_responses:
            step_qa_response = candidate_responses["STEP_QA_RESPONDER"]
            return 'STEP_QA_RESPONDER'

        question_types = getattr(self.state_manager.current_state, 'questiontype', None)

        type2responder = {
            "MRC": 'mrc',
            "FAQ":'faq',
            "EVI":'ooc',
            "SubstituteQuestion": 'SUB_QA_RESPONDER',
            "IngredientQuestion": 'INGREDIENT_QA_RESPONDER',
        }

        if question_types is not None and 'question_types' in question_types:
            order = []
            for type in question_types['question_types']:
                order.append(type2responder[type])

            for responder in type2responder.values():
                if responder not in order:
                    order.append(responder )

            order += ['IDK_RESPONDER']
            order = [rp for rp in order if rp in candidate_responses]

            print('[QA Responder order]: ',order)
            
            cur_response = candidate_responses.pop(order[0], None).text
            return order[0], cur_response

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
