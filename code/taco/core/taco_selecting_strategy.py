# new added

import json
import logging

from taco.core.state_manager import StateManager
from taco.core.taco_selecting_intent_by_rule import TacoIntentByRule
from taco.core.taco_selecting_intent import TacoIntent_manager
from taco.core.taco_selecting_st_machine import REFLEXIVE_TRIGGERS
from taco.core.taco_selecting_utils import *
from taco.core.util import taco_RP_NAME

logger = logging.getLogger('tacologger')


class TacoSelectingStrategy(object):
    """
    A generic mapper from an input string to a list of candidate response mode names, each of which must be
    registered as a response handler with the ResponseGeneratorRegistry..
    
    Base selecting strategy returns a full list of all available candidate modes, each of which maps to a
    ResponseGenerator. The BaseSelectingStrategy is not the most computationally efficient strategy, and 
    transfers all the of the responsibilities of response selection into the RankingStrategy, which then 
    must select the most coherent, reasonable response to the given user inquiry.
    
    A reasonable selecting strategy should take into account context, user intent, and any personalization 
    factors in selecting high probability response modes.
    
    See also: :py:class:`cobot_core.mapping_selecting_strategy.MappingSelectingStrategy`, PolicyStrategy, KerasPolicyStrategy
    
    """

    def __init__(self,
                 state_manager: StateManager):

        self.state_manager = state_manager
        self.Intent_manager = TacoIntent_manager(state_manager)

    def select_response_mode(self):
        """
        Returns:
            responders: (list[str]) a list of strings that correspond to
                        responde generators (that are added in osu_tacobot.py)
        """
        current_state = self.state_manager.current_state
        last_state = self.state_manager.last_state
        user_attributes = self.state_manager.user_attributes

        parsed_intent, guess_intent, allowed_intents = self.Intent_manager.intent_intrepret()

        candidate_responders = self.select_candidate_responders(parsed_intent, guess_intent, allowed_intents, 
            current_state, last_state, user_attributes)

        rg_states = self.state_manager.current_state.response_generator_states

        n_candidate_responders = []
        select_dic = {}
        for rg in candidate_responders:
            if rg in TACO2RP:
                selected_rp_module, selected_treelet = TACO2RP[rg]
                if selected_rp_module not in select_dic:
                    select_dic[selected_rp_module] = 1
                    n_candidate_responders.append(selected_rp_module)
                    rg_states[selected_rp_module].cur_treelet_str = selected_treelet
                    candidate_treelets = getattr(rg_states[selected_rp_module], 'candidate_treelets', None)
                    if candidate_treelets != None:
                        rg_states[selected_rp_module].candidate_treelets.append(selected_treelet)
            else:
                logger.error(f'{rg} not in TACO2RP fix it')

        return n_candidate_responders

    def select_responder_by_intent(self, parsed_intent, candidate_responders):

        if parsed_intent in ['RepeatIntent', 'IgnoreIntent']:
            candidate_responders.append('REPEAT_RESPONDER')
        elif parsed_intent == 'ReadIngredientIntent':
            candidate_responders.append('PREPARATION_RESPONDER')
        elif parsed_intent == 'TaskCompleteIntent':
            candidate_responders.append('HALT_RESPONDER')
        elif parsed_intent == 'HelpIntent':
            candidate_responders.append('HELP_RESPONDER')
        elif parsed_intent == 'StopIntent':
            candidate_responders.append('STOP_RESPONDER')

        

    def select_candidate_responders(self, parsed_intent, guess_intent, allowed_intents, current_state, last_state, user_attributes):
        current_status = getattr(current_state, 'status', None)

        candidate_responders = ['ERROR_RESPONDER']

        if (
            (parsed_intent == 'TaskRequestIntent' and 'TaskExecution' != current_status) or
            (parsed_intent == 'UserEvent' and 'Welcome' in current_status)
        ):

            candidate_responders.append('BAD_TASK_RESPONDER')
            # set up user user_attributes
            flush_slot_values(current_state, user_attributes)
        
        # select by intent
        # whether we should perform transition for intents used for selecting RGs
        self.select_responder_by_intent(parsed_intent, candidate_responders)

        logger.taco_merge(f'parsed_intent = {parsed_intent} after selected RG by parsed_intent:  {candidate_responders}')

        # print('allowed_intents = ', allowed_intents)
        processed_status = current_status

        next_status, transit_back = current_status, False
        if 'TaskCompleteIntent' == parsed_intent and parsed_intent in allowed_intents:
            self.Intent_manager.state_machine.trigger(parsed_intent, current_state=current_state, user_attributes=user_attributes)
            next_status = self.Intent_manager.state_machine.state
        elif parsed_intent not in ['RepeatIntent', 'IgnoreIntent', 'ReadIngredientIntent', 'TaskCompleteIntent', 
            'HelpIntent', 'StopIntent', 'AlexaCommandIntent']:
            # select by state
            # if second_transition and parsed_intent != 'AlexaCommandIntent':
            if parsed_intent == 'Navi2StepIntent' and 'TaskPrep' in current_status:
                self.Intent_manager.state_machine.trigger('AcknowledgeIntent')
                current_status = self.Intent_manager.state_machine.state
            elif 'Execution' in current_status and parsed_intent == 'LaunchRequestIntent' and is_launch_resume(current_state, user_attributes):
                parsed_intent = 'IgnoreIntent'
            if parsed_intent in allowed_intents:
                self.Intent_manager.state_machine.trigger(parsed_intent, current_state=current_state, user_attributes=user_attributes)
                next_status = self.Intent_manager.state_machine.state
            elif parsed_intent in ['Navi2StepIntent', 'NaviForwardStepsIntent', 'NaviBackStepsIntent'] and 'Execution' in current_status:
                text = getattr(current_state, 'text', None)
                new_execution_state = self._handle_advanced_navi(next_status, current_state, user_attributes, text, current_status)
                print('[dm navi2step] => ', new_execution_state)
                if new_execution_state:
                    next_status = new_execution_state

            # Select RG by state
            selected_responder, transit_back = self.select_responder_by_state(current_state, user_attributes,
                                                                 next_status, getattr(user_attributes, 'is_wikihow', False))
            logger.taco_merge(f'selected RG by state: {selected_responder}')
            if 'PAK' in current_status or 'chat' in current_status:
                candidate_responders = []
            for rp in selected_responder:
                candidate_responders.append(rp)


        if transit_back == False:
            setattr(current_state, 'status', next_status)
        
        logger.taco_merge(f'transition to state --> {next_status}')
        
        if parsed_intent not in REFLEXIVE_TRIGGERS and transit_back == False:
            setattr(current_state, 'last_status', processed_status)
        else:
            setattr(current_state, 'last_status', self.state_manager.last_state.last_status)

        return candidate_responders

    def _handle_advanced_navi(self, next_status, current_state, user_attributes, text, current_status):
        # deprecitaed: total_steps = getattr(user_attributes, 'total_steps', -1)
        all_total_steps = getattr(user_attributes, 'all_total_steps', None)
        print('[Advanced Navi] all steps: ', all_total_steps)

        method_idx, N_methods, N_steps, current_step_num = TacoIntentByRule.parse_step_nums(current_status)
        navi_intent, step_num, method_num = TacoIntentByRule.parse_navi_intents(text, N_steps, all_total_steps)
        # current_step_num = getattr(user_attributes, 'current_step', -1)
        
        if N_steps > -1 and (step_num > -1 or method_num > -1): 
            if navi_intent == 'Navi2StepIntent':
                print('[Advanced navi] -> ', step_num, ' @ ', method_num)
                if step_num > 0:
                    if method_num > 0:
                        # navi to step X @ method/part Y
                        if method_num <= N_methods:
                            if step_num <= all_total_steps[method_num-1]:
                                #setattr(user_attributes, 'total_steps', all_total_steps[method_num-1])
                                return f'TaskExecution_MethodNo{method_num-1}of{N_methods}w{all_total_steps[method_num-1]}steps_StepAt{step_num - 1}_Instruction'
                            else:
                                # step X OOB 
                                setattr(current_state, 'error_step_num', step_num - 1)
                        else:
                            # method Y OOB 
                            setattr(current_state, 'error_method_num', method_num - 1)
                    else:
                        if step_num <= N_steps:
                            # navi within the current method/part
                            return f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_num - 1}_Instruction'
                        else:
                            # step OOB for the current method/part
                            setattr(current_state, 'error_step_num', step_num - 1)
                elif method_num > 0:
                    if method_num <= N_methods:
                        # go to another method/part
                        #setattr(user_attributes, 'total_steps', all_total_steps[method_num-1])
                        return f'TaskExecution_MethodNo{method_num-1}of{N_methods}w{all_total_steps[method_num-1]}steps_StepAt{0}_Instruction'
                    else:
                        # method OOB
                        setattr(current_state, 'error_method_num', method_num - 1)
            elif navi_intent == 'NaviForwardStepsIntent' and current_step_num > -1 and step_num > -1:
                if current_step_num + step_num < N_steps:
                    return f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{current_step_num + step_num}_Instruction'
                else:
                    setattr(current_state, 'error_step_num', current_step_num + step_num)
            elif navi_intent == 'NaviBackStepsIntent' and current_step_num > -1 and step_num > -1:
                if current_step_num - step_num > -1:
                    return f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{current_step_num - step_num}_Instruction'
                else:
                    setattr(current_state, 'error_step_num', current_step_num - step_num)
        
        return next_status


    def select_responder_by_state(self, current_state, user_attributes, current_status, is_wikihow):
        selected_responder = None
        to_state_touch = None
        transit_back = False
        if current_status == 'Welcome':
            selected_responder = ['LAUNCH_RESPONDER']
        elif 'PAK' in current_status:
            selected_prompt_rg = getattr(current_state, 'selected_prompt_rg', False)
            if selected_prompt_rg == 'execution_INTERNT':
                # beginning answer pak question
                # get_last_rg_in_control use it control later
                selected_responder = ['EXECUTION_RESPONDER']
            else:
                # PAK only do chitchat
                selected_responder = taco_RP_NAME
        elif "chat" in current_status:
            selected_responder = taco_RP_NAME
        elif 'TaskChoice' in current_status:
            selected_responder = ['CHOICE_RESPONDER']
        elif current_status in ['TaskPreparation_TaskPrepConfirmation']:
            selected_responder = ['PREPARATION_RESPONDER']
        elif (isinstance(current_status, str) and  current_status.split('_')[0] == 'TaskExecution') and "PAK" not in current_status:
            selected_responder = ['EXECUTION_RESPONDER']
        elif current_status == 'TaskPreparation_MethodSelection':
            to_state_touch = _handle_method_selection(current_state, user_attributes)
            if to_state_touch != None:
                selected_responder = ['EXECUTION_RESPONDER']
            else:
                selected_responder = ['PREPARATION_RESPONDER']
                transit_back = True
        elif current_status == 'Halt':
            transit_back = True
            selected_responder = ['HALT_RESPONDER']
        elif current_status == 'ListManagement':
            selected_responder = ['LIST_MANAGEMENT_RESPONDER']
            transit_back = True
        elif current_status == 'TimerManagement':
            selected_responder = ['TIMER_MANAGEMENT_RESPONDER']
            transit_back = True
        elif current_status == 'IngredientQA':
            selected_responder = ['INGREDIENT_QA_RESPONDER', 'IDK_RESPONDER']
            transit_back = True
        elif current_status == 'QA':
            ##we want to run all the QA modules, so we add ALL qa modules here
            if not is_wikihow:
                selected_responder = ['STEP_QA_RESPONDER', 'mrc', 'faq', 'SUB_QA_RESPONDER', 'INGREDIENT_QA_RESPONDER', 'EVI_RESPONDER', 'IDK_RESPONDER']
            else:
                selected_responder = ['STEP_QA_RESPONDER', 'mrc', 'faq', 'EVI_RESPONDER', 'IDK_RESPONDER']

            transit_back = True
            
        return selected_responder, transit_back