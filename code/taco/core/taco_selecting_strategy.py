# new added

import json
# from .taco_service_module_manager import ServiceModuleManager
from taco_logger import LoggerFactory
from taco_state_machine import *
from taco_state_manager import StateManager
# from .taco_dialogue_manager import *
# from taco_utils import flush_slot_values, parse_intent
# from taco.response_modules.preparation.utils import get_query_result_selected
from taco_proc_nlu import flush_slot_values, parse_intent
from taco_select_helpers import *
from taco_intent_by_rule import TacoIntentByRule



def avoid_error_loop(current_state, last_state, last_state_dict, default_responders, intent, guess_intent):
    # If the previous turn was already exception, try to guess a valid transition to proceed
    if intent != 'CancelIntent':
        last_responder = None
        if last_state_dict:
            if 'final_responder' in last_state_dict:
                last_responder = last_state_dict['final_responder']
        else:
            # Use StateTable as backup. NOTE It may be erroneous!
            last_responder = (
                last_state.get('final_responder', '') if last_state is not None else ''
            )
        
        print('Last Responder ==>', last_responder)
        if last_responder == 'ERROR_RESPONDER':
            if intent is None and guess_intent != None and guess_intent not in ['StopIntent']:
                intent = guess_intent
                print('Intent Changed to Guess ==>', intent)
            else:
                setattr(current_state, 'need_cancel', True)
                default_responders.append('HELP_RESPONDER')
    return intent


def select_responder_by_intent(intent):
    selected_responder = None
    perform_transition = False
    if intent == 'AlexaCommandIntent':
        selected_responder = []
    # elif intent == 'ListManageIntent':
        # selected_responder = ['LIST_MANAGEMENT_RESPONDER'] 
    elif intent in ['RepeatIntent', 'IgnoreIntent']:
        selected_responder = ['REPEAT_RESPONDER']
    elif intent == 'ReadIngredientIntent':
        selected_responder = ['PREPARATION_RESPONDER']
    elif intent == 'TaskCompleteIntent':
        selected_responder = ['HALT_RESPONDER']
        perform_transition = True
    # elif intent  == 'SetTimerIntent':
        # selected_responder = ['TIMER_MANAGEMENT_RESPONDER']
    # elif intent == 'QuestionIntent':
        # selected_responder = ['EVI_RESPONDER', 'mrc']
        
    # elif intent == 'IngredientQuestionIntent':
        # selected_responder = ['INGREDIENT_QA_RESPONDER']
    elif intent == 'HelpIntent':
        selected_responder = ['HELP_RESPONDER']
    elif intent == 'StopIntent':
        selected_responder = ['STOP_RESPONDER']
    
    return selected_responder, perform_transition

def _handle_method_selection(current_state, user_attributes):
    arguments = current_state.user_event.get('arguments', [])
    if arguments and arguments[0] in ['MethodSelected', 'PartSelected']:
        all_total_steps = getattr(user_attributes, 'all_total_steps')
        item_selected = arguments[1] if len(arguments) > 1 else -1
        if item_selected > 0:
            to_state_touch = f'TaskExecution_MethodNo{item_selected-1}of{len(all_total_steps)}w{all_total_steps[item_selected-1]}steps_StepAt0_Instruction'
            return to_state_touch
    return None

def select_responder_by_state(current_state, user_attributes, current_taco_state, is_wikihow):
    selected_responder = None
    to_state_touch = None
    transit_back = False
    if current_taco_state == 'Welcome':
        selected_responder = ['LAUNCH_RESPONDER']
    elif 'TaskChoice' in current_taco_state:
        selected_responder = ['CHOICE_RESPONDER']
    elif current_taco_state in ['TaskPreparation_TaskPrepConfirmation']:
        selected_responder = ['PREPARATION_RESPONDER']
    elif (isinstance(current_taco_state, str) and  current_taco_state.split('_')[0] == 'TaskExecution'):
        selected_responder = ['EXECUTION_RESPONDER']
    elif current_taco_state == 'TaskPreparation_MethodSelection':
        to_state_touch = _handle_method_selection(current_state, user_attributes)
        if to_state_touch != None:
            selected_responder = ['EXECUTION_RESPONDER']
        else:
            selected_responder = ['PREPARATION_RESPONDER']
            transit_back = True
    elif current_taco_state == 'Halt':
        transit_back = True
        selected_responder = ['HALT_RESPONDER']
    elif current_taco_state == 'ListManagement':
        selected_responder = ['LIST_MANAGEMENT_RESPONDER']
        transit_back = True
    elif current_taco_state == 'TimerManagement':
        selected_responder = ['TIMER_MANAGEMENT_RESPONDER']
        transit_back = True
    elif current_taco_state == 'IngredientQA':
        selected_responder = ['INGREDIENT_QA_RESPONDER', 'IDK_RESPONDER']
        transit_back = True
    elif current_taco_state == 'QA':
        ##we want to run all the QA modules, so we add ALL qa modules here
        if not is_wikihow:
            selected_responder = ['STEP_QA_RESPONDER', 'mrc', 'SUB_QA_RESPONDER', 'INGREDIENT_QA_RESPONDER','faq', 'EVI_RESPONDER', 'IDK_RESPONDER']
        else:
            selected_responder = ['STEP_QA_RESPONDER', 'mrc', 'faq', 'EVI_RESPONDER', 'IDK_RESPONDER']

        transit_back = True
        
    return selected_responder, transit_back, to_state_touch


def _init_state_machine(features, user_attributes, current_taco_state):
    # taco_state_machine = transitions.Machine(
        # states=taco.taco_states.TacoStates, 
        # transitions=taco.taco_states.TacoTransitions, 
        # initial=current_taco_state
    # )

    article = None
    build_steps = False
    is_wikihow = getattr(user_attributes, 'is_wikihow', None)
    has_parts = getattr(user_attributes, 'has_parts', False)
    print(current_taco_state)
    if ('Execution' in current_taco_state or 'Prep' in current_taco_state):
        article = _get_article(features, user_attributes)
        build_steps = True

    # defined in taco_state_machine.py
    taco_state_machine = get_init_state_machine(build_steps, is_wikihow, article, has_parts, current_taco_state) 

    # ======= Conditional Transitions =======

    # taco_state_machine.add_transition('LaunchRequestIntent', taco.taco_states.TacoStates.TaskExecution,        taco.taco_states.TacoStates.TaskExecution, conditions=[self._is_launch_resume]) # handled by rule
    taco_state_machine.add_transition('LaunchRequestIntent', 'TaskExecution',                        'Welcome', unless=[is_launch_resume])
    taco_state_machine.add_transition('LaunchRequestIntent', 'TaskPreparation_TaskPrepConfirmation', 'TaskPreparation_TaskPrepConfirmation', conditions=[is_launch_resume_prep])
    taco_state_machine.add_transition('LaunchRequestIntent', 'TaskPreparation_TaskPrepConfirmation', 'Welcome', unless=[is_launch_resume_prep])
    taco_state_machine.add_transition('TaskCompleteIntent', 'TaskExecution', 'Halt', conditions=[_is_confirmed_complete])
    taco_state_machine.add_transition('TaskRequestIntent', 'Welcome', 'TaskChoice_TaskCatalog', unless=[_has_clarification_question])
    taco_state_machine.add_transition('TaskRequestIntent', 'Welcome', 'TaskChoice_TaskClarification', conditions=[_has_clarification_question])
    taco_state_machine.add_transition('TaskRequestIntent', 'TaskChoice_TaskCatalog', 'TaskChoice_TaskCatalog', unless=[_has_clarification_question])
    taco_state_machine.add_transition('TaskRequestIntent', 'TaskChoice_TaskCatalog', 'TaskChoice_TaskClarification', conditions=[_has_clarification_question])
    taco_state_machine.add_transition('TaskRequestIntent', 'TaskChoice_TaskComparison', 'TaskChoice_TaskCatalog', unless=[_has_clarification_question])
    taco_state_machine.add_transition('TaskRequestIntent', 'TaskChoice_TaskComparison', 'TaskChoice_TaskClarification', conditions=[_has_clarification_question])
    taco_state_machine.add_transition('TaskRequestIntent', 'TaskPreparation', 'TaskChoice_TaskCatalog', unless=[_has_clarification_question])
    taco_state_machine.add_transition('TaskRequestIntent', 'TaskPreparation', 'TaskChoice_TaskClarification', conditions=[_has_clarification_question])
    taco_state_machine.add_transition('AcknowledgeIntent', 'TaskChoice_TaskCatalog', 'TaskPreparation_TaskPrepConfirmation', conditions=[_only_one_query_result])
    taco_state_machine.add_transition('NegativeAcknowledgeIntent', 'TaskChoice_TaskCatalog', 'Welcome', conditions=[_only_one_query_result])
    # taco_state_machine.add_transition('UserEvent', 'Welcome', 'TaskChoice_TaskRecommendation', conditions=[_is_rec])
    # taco_state_machine.add_transition('UserEvent', 'Welcome', 'TaskChoice_TaskCatalog', unless=[_is_rec])
    # taco_state_machine.add_transition('AcknowledgeIntent',   'TaskPreparation_TaskPrepConfirmation', taco.taco_states.TacoStates.TaskExecution, conditions=[taco.dialogue_manager.utils.taco_select_helpers.is_start_task])
    # taco_state_machine.add_transition('AcknowledgeIntent',   'TaskPreparation_TaskPrepConfirmation', 'TaskPreparation_TaskPrepConfirmation', unless=[taco.dialogue_manager.utils.taco_select_helpers.is_start_task])
    
    return taco_state_machine

def _only_one_query_result(current_state, user_attributes, features):
    list_item_rec = getattr(user_attributes, 'list_item_rec', -1)
    print('[sm li_rec]: ', list_item_rec)
    return list_item_rec >= 0

def _has_clarification_question(current_state, user_attributes, features):
    # return False # disable for now
    if 'tasktype' in features.__dict__ and 'tasktype' in features.tasktype:
        tasktype = features.tasktype['tasktype']
        if tasktype == 'cooking' and 'attributes_to_clarify' in features.recipesearch \
            and features.recipesearch['attributes_to_clarify'] is not None:
            return True
    return False
def _is_confirmed_complete(current_state, user_attributes, features):
    complete_confirmation = getattr(user_attributes, 'confirmed_complete', False)
    if complete_confirmation:
        return True
    else:
        method_idx, N_methods, total_steps, current_step_num = TacoIntentByRule.parse_step_nums(user_attributes.taco_state)
        has_parts = getattr(user_attributes, 'has_parts', False)
        return current_step_num == total_steps-1 and (not has_parts or (has_parts and method_idx == N_methods-1 ))


def _get_article(features, user_attributes):
    current_task_docparse = getattr(user_attributes, 'current_task_docparse', None)
    if current_task_docparse:
        return current_task_docparse
    elif features['docparse'] and 'docparse' in features['docparse'] and not features['docparse']['is_batch']:
        current_task_docparse = features['docparse']['docparse']
        setattr(user_attributes, 'current_task_docparse', current_task_docparse)
        return current_task_docparse
    else:
        return None
    
    # list_item_selected = getattr(user_attributes, 'list_item_selected', -1)
    # query_result = getattr(user_attributes, 'query_result', None)
    # is_wikihow = getattr(user_attributes, 'is_wikihow', None)
    # if query_result and is_wikihow is not None and list_item_selected >= 0:
    #     if is_wikihow:
    #         return query_result[list_item_selected]
    #     else:
    #         return json.loads(query_result['documents'][list_item_selected])
    # else:
    #     return None


def _handle_advanced_navi(current_state, user_attributes, text, current_taco_state):
    # deprecitaed: total_steps = getattr(user_attributes, 'total_steps', -1)
    all_total_steps = getattr(user_attributes, 'all_total_steps', None)
    print('[Advanced Navi] all steps: ', all_total_steps)

    method_idx, N_methods, N_steps, current_step_num = TacoIntentByRule.parse_step_nums(current_taco_state)
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
    
    return None

def _parse_touch_event(user_event):
    '''
    Parse UserEvent to dialogue intents.

    Argument: 
        user_event: the input user event
    
    Output:
        intent (str): Dialogue intent for supported user events. 'UserEvent' otherwise.
    '''

    arguments = user_event.get('arguments', [])
    
    if arguments[0] == 'NextButtonPressed':
        return 'NaviNextIntent'
    elif arguments[0] == 'PreviousButtonPressed':
        return 'NaviPreviousIntent'
    elif arguments[0] == 'CompleteButtonPressed':
        return 'TaskCompleteIntent'
    elif arguments[0] == 'goBack':
        return 'GoBackIntent'
    elif arguments[0] == 'StartRecipeButtonPressed':
        return 'AcknowledgeIntent'
    
    return 'UserEvent'

def select_strategy(current_state, last_state, user_attributes, features):
    default_responders = ['ERROR_RESPONDER', 'SENSITIVE_RESPONDER']
    text = getattr(current_state, 'text', None)
    intent = getattr(current_state, 'intent', None)
    _last_taco_state = getattr(user_attributes, 'last_taco_state', None)
    print('[_last taco state]: ', _last_taco_state)
    if intent == 'UserEvent':
        print('[Touch Event] :\n', json.dumps(current_state.user_event, indent=2))
    
    # Find or init the current state
    current_taco_state = getattr(user_attributes, 'taco_state', None)
    if current_taco_state == None: 
        current_taco_state = 'Welcome'
    elif intent == 'LaunchRequestIntent' and not any(['Welcome' in current_taco_state, 'Execution' in current_taco_state]): #reset in case of abnormal exit in the last session.
        current_taco_state = 'Welcome'
        

    # Init state machine
    taco_state_machine = _init_state_machine(features, user_attributes, current_taco_state) 

    # print('incoming raw intent ======>', intent)
    # input()

    
    allowed_intents = taco_state_machine.get_triggers(current_taco_state)
    allowed_intents.extend(REFLEXIVE_TRIGGERS)
    if 'Instruction' in current_taco_state and 'DetailRequestIntent' not in allowed_intents:
        allowed_intents.append('DetailRequestIntent')
    
    # support DetailRequestIntent for recipes...
    is_wikihow = getattr(user_attributes, 'is_wikihow', None)
    if is_wikihow is not None:
        if not is_wikihow and 'Execution' in current_taco_state:
            allowed_intents.append('DetailRequestIntent')
    
    print('current taco state --->', current_taco_state)
    guess_intent = None
    if intent == 'UserEvent':
        intent = _parse_touch_event(current_state.user_event)
        
        if intent == 'UserEvent': # Unsupported UserEvent
            intent, guess_intent = parse_intent(text, intent, features, allowed_intents, current_taco_state, user_attributes, current_state)
    else:
        intent, guess_intent = parse_intent(text, intent, features, allowed_intents, current_taco_state, user_attributes, current_state)
    # 'text' might be updated in parse_intent()

    print('after regex_intent = ', intent)
    # input()


    text = getattr(current_state, 'text', None)
    if 'Clarification' in current_taco_state:
        if intent not in ['NegativeAcknowledgeIntent', 'GoBackIntent', 'CancelIntent', 'RepeatIntent']:
            intent = 'ClarifyIntent'
    elif 'TaskCatalog' in current_taco_state:
        if 'option' in text and intent not in ['MoreChoiceIntent', 'LessChoiceIntent', 'ChoiceIntent']:
            intent = 'HelpIntent'
    last_state_dict = getattr(user_attributes, "last_state_dict", None)
    print('[last state dict]: \n', json.dumps(last_state_dict, indent=2))

    # intent = avoid_error_loop(current_state, last_state, last_state_dict, default_responders, intent, guess_intent)
    
    ## For testing
    # if intent == 'QuestionIntent':
    #     intent = 'TaskRequestIntent'
    ## For testing
    
    setattr(current_state, 'final_intent', intent)
    setattr(current_state, 'parsed_intent', intent)
    print('parsed intent ======>', intent)
    print('guessed intent ======>', guess_intent)
    input()

    if (
        (intent == 'TaskRequestIntent' and 'TaskExecution' not in current_taco_state) or
        (intent == 'UserEvent' and 'Welcome' in current_taco_state)
    ):
        ### TESTING only ###
        # drop tasksearch
        # features['tasksearch'] = None
        # current_state.tasksearch = None
        # drop recipesearch
        # features['recipesearch'] = None
        # current_state.recipesearch = None
        ### TESTING only ###

        default_responders.append('BAD_TASK_RESPONDER')
        flush_slot_values(features, user_attributes)
    
    # select by intent
    perform_transition = False # whether we should perform transition for intents used for selecting RGs
    selected_responder, perform_transition = select_responder_by_intent(intent)
    print(' selected RG by intent: ', selected_responder)
    _new_last_taco_state = current_taco_state
    to_state = current_taco_state
    transit_back = False
    if perform_transition and intent in allowed_intents:
            taco_state_machine.trigger(intent, current_state=current_state, user_attributes=user_attributes, features=features)
            to_state = taco_state_machine.state
    # select by state    
    to_state_touch = None
    if selected_responder is None:
        if intent == 'Navi2StepIntent' and 'TaskPrep' in current_taco_state:
            taco_state_machine.trigger('AcknowledgeIntent')
            current_taco_state = taco_state_machine.state
        elif 'Execution' in current_taco_state and intent == 'LaunchRequestIntent' and is_launch_resume(current_state, user_attributes, features):
            intent = 'IgnoreIntent'

        if intent in allowed_intents:
            taco_state_machine.trigger(intent, current_state=current_state, user_attributes=user_attributes, features=features)
            to_state = taco_state_machine.state
        elif intent in ['Navi2StepIntent', 'NaviForwardStepsIntent', 'NaviBackStepsIntent'] and 'Execution' in current_taco_state:
            new_execution_state = _handle_advanced_navi(current_state, user_attributes, text, current_taco_state)
            print('[dm navi2step] => ', new_execution_state)
            if new_execution_state:
                to_state = new_execution_state
        
    
        # Select RG by state
        selected_responder, transit_back, to_state_touch = select_responder_by_state(current_state, user_attributes, to_state, getattr(user_attributes, 'is_wikihow', False))
        print(' selected RG by state: ', selected_responder)
    if not transit_back:
        if intent == 'UserEvent' and to_state_touch != None:
            to_state = to_state_touch
        setattr(user_attributes, 'taco_state', to_state)
        print('transition to state -->', to_state)
    else:
        print('transition to state -->', current_taco_state)
    
    if intent in REFLEXIVE_TRIGGERS or transit_back:
        # Ignore state history for reflexive transitions
        setattr(user_attributes, 'last_taco_state', _last_taco_state)
        print('[last taco state]: ', _last_taco_state)
    else:
        print('[last taco state]: ', _new_last_taco_state)
        setattr(user_attributes, 'last_taco_state', _new_last_taco_state)
    
    candidate_responders = default_responders
    if selected_responder:
        candidate_responders = candidate_responders + selected_responder


    # logger.taco_merge(f'n_candidate_responders = {n_candidate_responders}')
    # input()
    return candidate_responders


    # if selected_responder:
    #     return selected_responder + default_responders
    # else:
    #     return default_responders   


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
                #  service_module_manager: ServiceModuleManager):
        self.state_manager = state_manager
        # self.service_module_manager = service_module_manager
        self.logger = LoggerFactory.setup(self)


    def select_response_mode(self, features):
        """
        Returns:
            responders: (list[str]) a list of strings that correspond to
                        responde generators (that are added in osu_tacobot.py)
        """
        current_state = self.state_manager.current_state
        last_state = self.state_manager.last_state
        user_attributes = self.state_manager.user_attributes

        return select_strategy(current_state, last_state, user_attributes, features)
