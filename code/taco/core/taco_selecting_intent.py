# new added

import re
import json
import logging

from taco.core.state_manager import StateManager
from taco.core.taco_selecting_intent_by_rule import TacoIntentByRule
from taco.core.taco_selecting_st_machine import REFLEXIVE_TRIGGERS, get_init_state_machine
from taco.core.taco_selecting_utils import *
from taco.core.response_generator.helpers import user_said_chatty_phrase
# from taco.core.taco_selecting_utils import _is_confirmed_complete

logger = logging.getLogger('tacologger')

class TacoIntent_manager(object):
    def __init__(self, state_manager: StateManager):

        self.state_manager = state_manager
        current_state = state_manager.current_state
        user_attributes = state_manager.user_attributes

    def init_state_machine(self):
        
        current_state = self.state_manager.current_state

        current_status = getattr(current_state, 'status', None)
        user_attributes = self.state_manager.user_attributes

        article = None
        build_steps = False
        is_wikihow = getattr(user_attributes, 'is_wikihow', None)
        has_parts = getattr(user_attributes, 'has_parts', False)

        logger.taco_merge(f'current_status = {current_status}')

        if ('Execution' in current_status or 'Prep' in current_status):
            article = get_article(current_state, user_attributes)
            build_steps = True

        # defined in taco_state_machine.py
        taco_state_machine = get_init_state_machine(build_steps, is_wikihow, article, has_parts, current_status)

        return taco_state_machine

    def intent_intrepret(self):

        current_state = self.state_manager.current_state
        user_attributes = self.state_manager.user_attributes

        self.state_machine = self.init_state_machine()

        intent = getattr(current_state, 'intent', None)

        # Find or init the current state
        current_status = getattr(current_state, 'status', None)

        logger.taco_merge(f'current taco state ---> {current_status}, intent ---> {intent}')
        allowed_intents = self.allowed_intents_generated(current_status)

        logger.taco_merge(f'allowed_intents ---> {allowed_intents}')
        # input()

        parsed_intent, guess_intent = self.parse_intent(current_status, allowed_intents)

        # last_state_dict = getattr(user_attributes, "last_state_dict", None)
        # print('[last state dict]: \n', json.dumps(last_state_dict, indent=2))

        setattr(current_state, 'parsed_intent', parsed_intent)
        # input()
        # print('parsed intent ======>', parsed_intent)
        # print('guessed intent ======>', guess_intent)

        logger.taco_merge(f'parsed intent ======> {parsed_intent}')
        logger.taco_merge(f'guessed intent ======> {guess_intent}')

        return parsed_intent, guess_intent, allowed_intents

    def parse_intent(self, current_status, allowed_intents):
        """
        We parse most user intents using our custom intent classification model, while
        some ASK intents are preserved. Some heuristics are used to compensate for 
        errors of intent classification.

        Args:
            intent: Intent produced by ASK.
            current_state: The current_state argument passed to select_response_model.
            allowed_intents: Legal intents based on state transitions.
            current_status: current taco_state

        Returns:
            intent: (str or None) parsed intent.
            guess_intent: (str or None) when neural NLU is not confident enough, used for fallbacks.

        Exactly one of these two return values will be None, the other will be
        a string.
        """

        current_state = self.state_manager.current_state
        user_attributes = self.state_manager.user_attributes

        text = getattr(current_state, 'text', None)
        # intent = getattr(current_state, 'intent', None)


        # Keep some ASK intents # reduntent
        # if intent in ["LaunchRequestIntent", "AMAZON.RepeatIntent", "AMAZON.ResumeIntent", "AMAZON.ScrollDownIntent",
        #     "AMAZON.ScrollUpIntent","AMAZON.ScrollLeftIntent","AMAZON.ScrollRightIntent", "AMAZON.CancelIntent", "AMAZON.StopIntent", 
        #     "UserEvent"] and text not in ASK_ERRORS:

        if self.state_manager.last_state is None:
            return 'LaunchRequestIntent', 'LaunchRequestIntent'
        # elif intent in ["AMAZON.RepeatIntent", "AMAZON.ResumeIntent", "AMAZON.ScrollDownIntent",
        #     "AMAZON.ScrollUpIntent","AMAZON.ScrollLeftIntent","AMAZON.ScrollRightIntent", "AMAZON.CancelIntent", "AMAZON.StopIntent", 
        #     "UserEvent"] and text not in ASK_ERRORS:
        #     parsed_intent = intent.split('.')[-1]
            # return parsed_intent, parsed_intent

        # timer intent
        set_timer_pattern = re.compile(r'\bset\b.*\b(alarm|timer)\b.*\bfor\b')
        if re.search(set_timer_pattern, text.lower()):
            parsed_intent = 'SetTimerIntent'
            return parsed_intent, parsed_intent
        

        # model intent extractor => 
        # check neural intent is in allowed intent or 
        # AcknowledgeIntent or NegativeAcknowledgeIntent is high enough
        parsed_intent, guess_intent = self.neural_intent_extractor(current_status, allowed_intents)

        # SelfIntroIntent is only used for Certification (required for changes to ASK interaction model).
        # ????????????? SelfIntroIntent
        # if intent == "SelfIntroIntent":
        #     parsed_intent = "IgnoreIntent"
        
        logger.taco_merge(f'parsed_intent after neural_intent_extractor ---> {parsed_intent}')


        # rule based intent extractor
        parsed_intent, regex_flag = self.rule_base_intent_extractor(parsed_intent, current_status)

        if regex_flag == True and ('PAK' not in current_status and 'chat' not in current_status): return parsed_intent, guess_intent

        logger.taco_merge(f'parsed_intent after rule based intent ---> {parsed_intent}')

        # senario based intent parser
        parsed_intent, guess_intent = self.senario_based_extractor(parsed_intent, guess_intent, current_status)

        return parsed_intent, guess_intent

    def allowed_intents_generated(self, current_status):
        # Init state machine to find allowed intents
        # get trigger and extend written in 

        user_attributes = self.state_manager.user_attributes

        # print('incoming raw intent ======>', intent)
        # logger.taco_merge(f'guess_intent = {guess_intent}')
        allowed_intents = self.state_machine.get_triggers(current_status)
        allowed_intents.extend(REFLEXIVE_TRIGGERS)

        if 'Instruction' in current_status and 'DetailRequestIntent' not in allowed_intents:
            allowed_intents.append('DetailRequestIntent')
        
        # support DetailRequestIntent for recipes...
        is_wikihow = getattr(user_attributes, 'is_wikihow', None)
        if is_wikihow == False and 'Execution' != current_status:
            allowed_intents.append('DetailRequestIntent')

        return allowed_intents
    
    def neural_intent_extractor(self, current_status, allowed_intents):
        parsed_intent, guess_intent = '', ''

        current_state = self.state_manager.current_state
        user_attributes = self.state_manager.user_attributes


        if 'PAK' in current_status or 'chat' in current_status:
            pass
        elif "neuralintent" in current_state.__dict__ and current_state.neuralintent:
            # parsed_intent, guess_intent = self.process_custom_intent(current_status, allowed_intents) 
            # print('current_state.neuralintent = ', current_state.neuralintent)
            if 'intent_scores' in  current_state.neuralintent:
                intent_scores = current_state.neuralintent['intent_scores']
            else:
                intent_scores = {}
            # The score of these three intents are obtained via softmax.

            logger.taco_merge(f'intent_scores ---> {intent_scores}')

            other_scores = {}
            for k, v in intent_scores.items():
                if not (k in ['NeutralIntent', 'AcknowledgeIntent', 'NegativeAcknowledgeIntent']) and k in allowed_intents:
                    if k in ['QuestionIntent', 'TaskRequestIntent']:
                        # ?????? not need two intents
                        other_scores[k] = max(intent_scores['QuestionIntent'], intent_scores['TaskRequestIntent']) # alleviate problems caused by the ambiguity between these two
                    else:
                        other_scores[k] = v
            logger.taco_merge(f'other_scores ---> {other_scores}')

            sorted_other_scores = sorted(other_scores, key=other_scores.get, reverse=True)

            logger.taco_merge(f'sorted_other_scores ---> {sorted_other_scores}')

            if len(sorted_other_scores) > 0:
                if 'Instruction' in current_status and other_scores['DetailRequestIntent'] > 0.95:
                    guess_intent = 'DetailRequestIntent'
                elif 'Execution' in current_status and other_scores['HelpIntent'] > 0.95:
                    guess_intent = 'HelpIntent'
                else: guess_intent = sorted_other_scores[0]

                # ????????????????? why need to make condition before
                if other_scores[sorted_other_scores[0]] > 0.3:
                    guess_intent = sorted_other_scores[0]
            else:
                guess_intent = None

            # The score of these intents are obtained via sigmoid, with threshold 0.5.
            if guess_intent and other_scores[guess_intent] > 0.5:
                parsed_intent = guess_intent
            else:
                # parsed_intent = None
                try:                
                    polarity_scores = {
                        'NeutralIntent': intent_scores['NeutralIntent'],
                        'AcknowledgeIntent': intent_scores['AcknowledgeIntent'],
                        'NegativeAcknowledgeIntent': intent_scores['NegativeAcknowledgeIntent']
                    }
                except:
                    polarity_scores = {
                        'NeutralIntent': None,
                        'AcknowledgeIntent': None,
                        'NegativeAcknowledgeIntent': None
                    }
                sorted_polarity_scores = sorted(polarity_scores, key=polarity_scores.get, reverse=True)
                polarity_result = sorted_polarity_scores[0]

                # ????? why polarity_result != 'NeutralIntent', NeutralIntent would never be intent
                if polarity_result != 'NeutralIntent':
                    parsed_intent = polarity_result

        # input()
        return parsed_intent, guess_intent

    def rule_base_intent_extractor(self, parsed_intent, current_status):

        current_state = self.state_manager.current_state
        user_attributes = self.state_manager.user_attributes
        text = getattr(current_state, 'text', None)
        tokens = text.split()

        method_idx, N_methods, N_steps, current_step_num = TacoIntentByRule.parse_step_nums(current_status)
        all_total_steps = getattr(user_attributes, 'all_total_steps', None)

        # Intent parsing using regex, as supplement to neural model.
        regex_intent = TacoIntentByRule.parse_regex_intents(text, N_steps, all_total_steps, current_status)

        if 'TaskPreparation' in current_status and len(all_total_steps) > 1:
            _text, _intent = transform_text_prep(text)
            if _intent is not None:
                regex_intent = _intent
                text = _text
                current_state.text = _text
                print('[dm transform]: text => ', _text)
        elif 'Detail' in current_status and regex_intent == 'NaviNextIntent' and 'step' in text:
                # escape from tips by 'next STEP'
                return 'ResumeIntent', True

        logger.taco_merge(f"regex intent ==========> {regex_intent}")

        # 20221110 1017 
        if regex_intent in ['ListManageIntent', 'ReadIngredientIntent']:
            list_item_selected = getattr(user_attributes, 'list_item_selected', -1)
            is_wikihow = getattr(user_attributes, 'is_wikihow', True)
            if list_item_selected > -1 and (not is_wikihow) and ('step' not in text):
                return regex_intent, True
        elif (
            ('TaskPrepConfirmation' in current_status and regex_intent == 'IngredientQuestionIntent') or 
            ('TaskPrepConfirmation' in current_status and regex_intent == 'AcknowledgeIntent') or 
            (('TaskExecution' in current_status or 'TaskPrep' in current_status) and regex_intent != None and  'Navi' in regex_intent) or
            (('TaskChoice' in current_status) and regex_intent == 'RepeatIntent') and
            ("PAK" not in current_status and 'chat' not in current_status)
            ):
            return regex_intent, True

        if parsed_intent is None and regex_intent:
            parsed_intent = regex_intent

        # string strict matching based method
        strict_matched_intent = TacoIntentByRule.parse_strict_matching(text)
        if strict_matched_intent:
            if strict_matched_intent == 'TaskCompleteIntent' and not('Execution' != current_status):
                print("strict match intent ===> ", strict_matched_intent)
                parsed_intent = 'IgnoreIntent'
            else:
                print("strict match intent ===> ", strict_matched_intent)
                parsed_intent =  strict_matched_intent

        matching_slots = user_said_chatty_phrase(self.state_manager)
        if matching_slots:
            parsed_intent = "USERWANTTOCHAT"

        return parsed_intent, False

    def senario_based_extractor(self, parsed_intent, guess_intent, current_status):
        current_state = self.state_manager.current_state
        user_attributes = self.state_manager.user_attributes
        text = getattr(current_state, 'text', None)
        tokens = text.split()

        logger.taco_merge(f'parsed_intent = {parsed_intent}')
        # input()
        if ('cancel' in parsed_intent and 'timer' not in parsed_intent) or ('start over' in text):
            parsed_intent = 'CancelIntent'


        if 'PAK' in current_status or 'chat' in current_status:
            # if self.state_manager.last_state.selected_prompt_rg == 'NEURAL_CHAT'
            # print(self.state_manager.current_state.response_generator_states['NEURAL_CHAT'])
            if self.state_manager.last_state.selected_prompt_rg == 'NEURAL_CHAT' and self.state_manager.current_state.response_generator_states['NEURAL_CHAT'].should_go_back_instruction == True:
                recent_treelt = getattr(self.state_manager.current_state.response_generator_states['NEURAL_CHAT'], 'most_recent_treelet', None) 
                # print('recent_treelt = ', recent_treelt)
                # input()
                if recent_treelt == 'GO_BACK_Treelet':
                    self.state_manager.current_state.response_generator_states['NEURAL_CHAT'].should_go_back_instruction = False
                    parsed_intent = 'GOBACKMAINTASKINENT'
            else:
                parsed_intent = 'keep_chating'
            return parsed_intent, guess_intent

        if current_status == "Welcome" or 'Catalog' in current_status or 'TaskComparison' in current_status:
            if (parsed_intent not in ["AlexaCommandIntent", "UserEvent"] and 
                ('favorite' in parsed_intent or 'favorites' in parsed_intent)):
                parsed_intent = 'RecommendIntent'

        #TODO

        if 'TaskChoice' in current_status:
            new_intent = get_task_choice(current_state, text, user_attributes)
            if new_intent is not None:
                parsed_intent = new_intent
            else:
                new_intent = choice_intent_keywords(text, parsed_intent, current_state)
                if new_intent is not None:
                    parsed_intent = new_intent
            if parsed_intent == 'NegativeAcknowledgeIntent' and 'Catalog' in current_status:
                list_item_rec = getattr(user_attributes, 'list_item_rec', -1)
                if list_item_rec < 0:
                    parsed_intent = 'MoreChoiceIntent' # Treat Nak as MoreChoice in TaskChoice_TaskCatalog
        #TODO
        elif 'TaskPreparation' in current_status and TacoIntentByRule._regex_match(TacoIntentByRule.rStartCooking, text):
            # This will be further processed by conditional transition
            parsed_intent = 'AcknowledgeIntent'
            return parsed_intent, parsed_intent
        #TODO
        elif "TaskExecution" in current_status and 'PAK' not in current_status:

            # if "peoplealsoask" in current_status:
            #     parsed_intent = "PAK_to_instruction"
            #     return parsed_intent, parsed_intent 
            if parsed_intent == 'AMAZON.NextIntent':
                parsed_intent = 'NaviNextIntent'
                return parsed_intent, parsed_intent
            elif parsed_intent == 'AMAZON.PreviousIntent':
                parsed_intent = 'NaviPreviousIntent'
                return parsed_intent, parsed_intent
            elif parsed_intent == 'TaskRequestIntent':
                if current_state['punctuation'] and '?' in current_state['punctuation']:
                    parsed_intent = 'QuestionIntent'
        
            elif parsed_intent == 'AcknowledgeIntent':
                selected_prompt_rg = getattr(current_state, 'selected_prompt_rg', False)
                print('selected_prompt_rg = ', selected_prompt_rg)
                if selected_prompt_rg == 'execution_INTERNT':
                    parsed_intent = 'PAK_AcknowledgeIntent'

        #TODO
        if 'back' in tokens:
            if 'TaskCatalog' in current_status and getattr(user_attributes, 'choice_start_idx', 0) == 0:
                parsed_intent = 'GoBackIntent'
            elif 'TaskPrep' in current_status:
                parsed_intent = 'GoBackIntent'

        if text == 'help' or ('help' in tokens and parsed_intent not in allowed_intents):
            parsed_intent = 'HelpIntent'

        # 'text' might be updated in parse_intent() when rule based parser working "TaskPreparation" first -> 1
        if 'Clarification' in current_status:
            if parsed_intent not in ['NegativeAcknowledgeIntent', 'GoBackIntent', 'CancelIntent', 'RepeatIntent']:
                parsed_intent = 'ClarifyIntent'
        elif 'TaskCatalog' in current_status:
            if 'option' in text and parsed_intent not in ['MoreChoiceIntent', 'LessChoiceIntent', 'ChoiceIntent']:
                parsed_intent = 'HelpIntent'

        return parsed_intent, guess_intent

