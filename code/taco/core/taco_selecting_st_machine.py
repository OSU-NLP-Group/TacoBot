import re
from transitions.extensions import HierarchicalMachine

from transitions.extensions.nesting import NestedState
from taco.core.taco_selecting_utils import *
import json

REFLEXIVE_TRIGGERS = ['AlexaCommandIntent', 'StopIntent', 'RepeatIntent', 'IngoreIntent', 'ReadIngredientIntent', 'HelpIntent']

TACO_TRANSITIONS = [
    ['RecommendIntent',           'Welcome', 'TaskChoice'], 
    ['UserEvent',                 'Welcome', 'TaskChoice'], 
    ['NegativeAcknowledgeIntent', 'Welcome', 'Welcome'],
    ['AcknowledgeIntent',         'Welcome', 'Welcome'],

    ['CancelIntent',              'TaskChoice', 'Welcome'],
    ['RecommendIntent',           'TaskChoice_Catalog', 'TaskChoice_TaskCatalog'],
    ['RecommendIntent',           'TaskChoice_Comparison', 'TaskChoice_TaskCatalog'],
    ['UserEvent',                 'TaskChoice', 'TaskChoice_TaskCatalog'],
    ['GoBackIntent',              'TaskChoice_TaskCatalog', 'Welcome'],
    ['LessChoiceIntent',          'TaskChoice_TaskCatalog', 'TaskChoice_TaskCatalog'],
    ['MoreChoiceIntent',          'TaskChoice_TaskCatalog', 'TaskChoice_TaskCatalog'],
    ['ChoiceIntent',              'TaskChoice_TaskCatalog', 'TaskPreparation'],
    ['UserEvent',                 'TaskChoice_TaskCatalog', 'TaskPreparation'],
    ['InfoRequestIntent',         'TaskChoice_TaskCatalog', 'TaskChoice_TaskComparison'],
    ['GoBackintent',              'TaskChoice_TaskComparison', 'TaskChoice_TaskCatalog'],
    ['AcknowledgeIntent',         'TaskChoice_TaskComparison', 'TaskPreparation'],
    ['ChoiceIntent',              'TaskChoice_TaskComparison', 'TaskPreparation'],
    ['UserEvent',                 'TaskChoice_TaskComparison', 'TaskPreparation'],
    ['NegativeAcknowledgeIntent', 'TaskChoice_TaskComparison', 'TaskChoice_TaskCatalog'],
    ['LessChoiceIntent',          'TaskChoice_TaskComparison', 'TaskChoice_TaskCatalog'],
    ['MoreChoiceIntent',          'TaskChoice_TaskComparison', 'TaskChoice_TaskCatalog'],
    ['InfoRequestIntent',         'TaskChoice_TaskComparison', 'TaskChoice_TaskComparison'],
    ['ClarifyIntent',             'TaskChoice_TaskClarification', 'TaskChoice_TaskCatalog'],
    ['NegativeAcknowledgeIntent', 'TaskChoice_TaskClarification', 'TaskChoice_TaskCatalog'],
    ['GoBackIntent',              'TaskChoice_TaskClarification', 'Welcome'],
    
    ['QuestionIntent',            'TaskPreparation', 'QA'],
    ['ListManageIntent',          'TaskPreparation', 'ListManagement'],
    ['NegativeAcknowledgeIntent', 'TaskPreparation_TaskPrepConfirmation', 'TaskPreparation_TaskPrepConfirmation'],
    ['CancelIntent',              'TaskPreparation', 'Welcome'],
    ['GoBackIntent',              'TaskPreparation_TaskPrepConfirmation', 'TaskChoice_TaskCatalog'],
    ['NaviPreviousIntent',        'TaskPreparation_TaskPrepConfirmation', 'TaskChoice_TaskCatalog'],
    ['AcknowledgeIntent',         'TaskPreparation_TaskPrepConfirmation', 'TaskExecution'],
    ['NaviNextIntent',            'TaskPreparation_TaskPrepConfirmation', 'TaskExecution'],
    ['UserEvent',                 'TaskPreparation_TaskPrepConfirmation', 'TaskPreparation_MethodSelection'],
 
    ['QuestionIntent',            'TaskExecution', 'QA'],
    ['ListManageIntent',          'TaskExecution', 'ListManagement'],
    ['SetTimerIntent',            'TaskExecution', 'TimerManagement'],

    ['LaunchRequestIntent',       'TaskChoice', 'Welcome'], # Other launch transitions are defined in selecting_strategy
]

state_dict = {}
state_to_add = {}
TMP_TRANSITIONS = []
for _, taco_state, _ in TACO_TRANSITIONS:
    if taco_state not in state_dict and "TaskExecution" != taco_state and "TaskChoice" != taco_state and "TaskPreparation" != taco_state:
        state_dict[taco_state] = 1
        # taco_state = taco_state.replace('_', "")
        state_to_add[taco_state + 'chat'] = 1
        TMP_TRANSITIONS.append(["USERWANTTOCHAT", taco_state, taco_state + 'chat'])
        TMP_TRANSITIONS.append(["GOBACKMAINTASKINENT", taco_state + 'chat', taco_state])


def _get_execution_states_and_transitions_wikihow(article, has_parts):

    if not article:
        return None, []

    step_transitions = []
    methods = article 
    N_prev_method_steps = 0
    N_steps = 0
    execution_states = []
    N_methods = len(methods)
    for method_idx, method in enumerate(methods):
        step_states = []
        N_prev_method_steps = N_steps
        N_steps = len(method)

        for step_idx, step in enumerate(method):
            if step_idx > 0:
                step_transitions.append(['NaviNextIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx-1}_Instruction', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}'])
                step_transitions.append(['AcknowledgeIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx-1}_Instruction', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}'])
                step_transitions.append(['NaviPreviousIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Instruction', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx-1}'])
            if step_idx == len(method)-1 and not has_parts:
                step_transitions.append(['NaviNextIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Instruction', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Instruction'])

            detail_json = None

            #if len(sentences) >= 3 and len(step.split())>30:
            if step['detail']:
                tips_list = []
                step_transitions.append(['DetailRequestIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Instruction', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips'])
                step_transitions.append(['NaviPreviousIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Detail', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Instruction'])
                #num_tips = len(re.split(r'\n+', step)) - 1
                num_tips = len(step['tips'])
                step_detail_tips_children = [f'Detail']
                if num_tips > 0:
                    # detail w/ tips
                    step_transitions.append(['NaviNextIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Detail', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Tips'])
                    step_transitions.append(['NaviPreviousIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Tips_tipNo0', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Detail'])
                    step_transitions.append(['AcknowledgeIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Detail', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Tips'])
                    if step_idx < len(method)-1:
                        # detail --nak--> next step
                        step_transitions.append(['NegativeAcknowledgeIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Detail', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx+1}'])
                    elif step_idx == len(method)-1:
                        if method_idx < len(methods)-1 and has_parts:
                            # detail of last step of a part --nak--> step 1 of the next part
                            step_transitions.append(['NegativeAcknowledgeIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Detail', f'TaskExecution_MethodNo{method_idx+1}of{N_methods}w{len(methods[method_idx+1])}steps_StepAt{0}'])
                        else:
                            # detail of last step of a method --nak--> last step of the method
                            step_transitions.append(['NegativeAcknowledgeIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Detail', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Instruction'])
                        
                    tips_json = None
                    for tip_idx in range(num_tips):
                        if tip_idx > 0:
                            step_transitions.append(['NaviNextIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Tips_tipNo{tip_idx-1}', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Tips_tipNo{tip_idx}'])
                            step_transitions.append(['NaviPreviousIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Tips_tipNo{tip_idx}', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Tips_tipNo{tip_idx-1}'])
                            step_transitions.append(['AcknowledgeIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Tips_tipNo{tip_idx-1}', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Tips_tipNo{tip_idx}'])
                        tips_list.append(f'tipNo{tip_idx}')
                    tips_json = {
                        'name':f'Tips',
                        'children': tips_list,
                        'initial': tips_list[0]
                    }
                    step_detail_tips_children.append(tips_json)
                    if step_idx < len(method)-1:
                        # Last tip --Ack/NaviNext--> next step
                        step_transitions.append(['AcknowledgeIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Tips_tipNo{num_tips-1}', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx+1}'])
                        step_transitions.append(['NaviNextIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Tips_tipNo{num_tips-1}', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx+1}'])
                    elif step_idx == len(method)-1:
                        if method_idx < len(methods)-1 and has_parts:
                            # Last tip of the last step of a part --Ack/NaviNext--> first step of the next part
                            step_transitions.append(['AcknowledgeIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Tips_tipNo{num_tips-1}', f'TaskExecution_MethodNo{method_idx+1}of{N_methods}w{len(methods[method_idx+1])}steps_StepAt{0}'])
                            step_transitions.append(['NaviNextIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Tips_tipNo{num_tips-1}', f'TaskExecution_MethodNo{method_idx+1}of{N_methods}w{len(methods[method_idx+1])}steps_StepAt{0}'])
                        else:
                            # Last tip of the last step of the a method --Ack/NaviNext--> the last step of the method
                            step_transitions.append(['AcknowledgeIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Tips_tipNo{num_tips-1}', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Instruction'])
                            step_transitions.append(['NaviNextIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Tips_tipNo{num_tips-1}', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Instruction'])
                        
                else:
                    # detail w/o tips
                    if step_idx < len(method)-1:
                        # Detail --Ack/NaviNext--> next step.
                        step_transitions.append(['AcknowledgeIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Detail', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx+1}'])
                        step_transitions.append(['NaviNextIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Detail', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx+1}'])
                    elif step_idx == len(method)-1:
                        if method_idx < len(methods)-1 and has_parts:
                            # Detail of last step of a part --Ack/NaviNext--> step 1 of the next part.
                            step_transitions.append(['AcknowledgeIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Detail', f'TaskExecution_MethodNo{method_idx+1}of{N_methods}w{len(methods[method_idx+1])}steps_StepAt{0}'])
                            step_transitions.append(['NaviNextIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Detail', f'TaskExecution_MethodNo{method_idx+1}of{N_methods}w{len(methods[method_idx+1])}steps_StepAt{0}'])
                        elif method_idx == len(methods)-1:
                            # detail of the last step of the last method --nak--> last step of the last part/method
                            step_transitions.append(['NegativeAcknowledgeIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips_Detail', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Instruction'])
                        
                detail_json = {
                    'name': f'Detail&Tips',
                    'children': step_detail_tips_children,
                    'initial': f'Detail'
                }

            step_transitions.append(['PAK_AcknowledgeIntent',f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx-1}_Instruction', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx-1}PAK'])
            step_transitions.append(['GOBACKMAINTASKINENT', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx-1}PAK', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Instruction'])
            

            step_transitions.append(['USERWANTTOCHAT',f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx-1}_Instruction', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx-1}chat'])
            step_transitions.append(['GOBACKMAINTASKINENT', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx-1}chat', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Instruction'])

            if detail_json != None:
                step_children = [detail_json, f'Instruction']
                # Detail&Tips --Resume--> next step.
                if step_idx < len(method)-1:            
                    step_transitions.append(['ResumeIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx+1}'])
                elif step_idx == len(method)-1:
                    if method_idx < len(methods)-1 and has_parts:
                        # Detail&Tips --Resume--> first step of the next part. 
                        step_transitions.append(['ResumeIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips', f'TaskExecution_MethodNo{method_idx+1}of{N_methods}w{len(methods[method_idx+1])}steps_StepAt{0}'])
                    else:
                        # Detail&Tips of the last step of a method --Resume--> first step of the next part. 
                        step_transitions.append(['ResumeIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Detail&Tips', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{step_idx}_Instruction'])
            else:
                step_children = [f'Instruction']
            step_json = {
                'name': f'StepAt{step_idx}',
                'children': step_children,
                'initial': f'Instruction'
            }
            
            step_states.append(step_json)
            step_states.append( {'name': f'StepAt{step_idx}PAK',})   # we ask pak question if user interests and we would go to PAK  and allows user to chitchat
            step_states.append( {'name': f'StepAt{step_idx}chat',})  # we ask pak question if user interests and we would go to chat and allows user to chitchat

        execution_states.append({
            'name': f'MethodNo{method_idx}of{N_methods}w{N_steps}steps',
            'children': step_states,
            'initial': step_states[0]['name']
        })

        if has_parts and method_idx > 0:
            step_transitions.append(['NaviNextIntent', f'TaskExecution_MethodNo{method_idx-1}of{N_methods}w{N_prev_method_steps}steps_StepAt{N_prev_method_steps-1}_Instruction', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{0}'])
            step_transitions.append(['NaviPreviousIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{0}_Instruction', f'TaskExecution_MethodNo{method_idx-1}of{N_methods}w{N_prev_method_steps}steps_StepAt{N_prev_method_steps-1}'])
            step_transitions.append(['AcknowledgeIntent', f'TaskExecution_MethodNo{method_idx-1}of{N_methods}w{N_prev_method_steps}steps_StepAt{N_prev_method_steps-1}_Instruction', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{0}'])
        if method_idx > 0:
            step_transitions.append(['NaviNextMethodIntent', f'TaskExecution_MethodNo{method_idx-1}of{N_methods}w{N_prev_method_steps}steps', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps_StepAt{0}'])
            step_transitions.append(['NaviPreviousMethodIntent', f'TaskExecution_MethodNo{method_idx}of{N_methods}w{N_steps}steps', f'TaskExecution_MethodNo{method_idx-1}of{N_methods}w{N_prev_method_steps}steps_StepAt{0}'])
            
    return execution_states, step_transitions

def _get_execution_states_and_transitions_recipe(article):
    if not article:
        return None, []
    
    step_transitions = []
    step_states = []
    N_steps = len(article)

    for i in range(N_steps):
        if i > 0:
            step_transitions.append(['NaviNextIntent', f'TaskExecution_MethodNo0of1w{N_steps}steps_StepAt{i-1}_Instruction', f'TaskExecution_MethodNo0of1w{N_steps}steps_StepAt{i}'])
            step_transitions.append(['AcknowledgeIntent', f'TaskExecution_MethodNo0of1w{N_steps}steps_StepAt{i-1}_Instruction', f'TaskExecution_MethodNo0of1w{N_steps}steps_StepAt{i}'])
            step_transitions.append(['NaviPreviousIntent', f'TaskExecution_MethodNo0of1w{N_steps}steps_StepAt{i}_Instruction', f'TaskExecution_MethodNo0of1w{N_steps}steps_StepAt{i-1}'])
            step_transitions.append(['PAK_AcknowledgeIntent',f'TaskExecution_MethodNo0of1w{N_steps}steps_StepAt{i-1}_Instruction', f'TaskExecution_MethodNo0of1w{N_steps}steps_StepAt{i-1}PAK'])
            step_transitions.append(['GOBACKMAINTASKINENT', f'TaskExecution_MethodNo0of1w{N_steps}steps_StepAt{i-1}PAK', f'TaskExecution_MethodNo0of1w{N_steps}steps_StepAt{i}_Instruction'])
            
            step_transitions.append(['USERWANTTOCHAT',f'TaskExecution_MethodNo0of1w{N_steps}steps_StepAt{i-1}_Instruction', f'TaskExecution_MethodNo0of1w{N_steps}steps_StepAt{i-1}chat'])
            step_transitions.append(['GOBACKMAINTASKINENT', f'TaskExecution_MethodNo0of1w{N_steps}steps_StepAt{i-1}chat', f'TaskExecution_MethodNo0of1w{N_steps}steps_StepAt{i}_Instruction'])
            

        step_states.append(
            {
                'name': f'StepAt{i}',
                'children': f'Instruction',
                'initial': f'Instruction'
            }
        )
        step_states.append(
            {
                'name': f'StepAt{i}PAK',  # we ask pak question if user interests and we would go to PAK and allows user to chitchat
            }
        )

        step_states.append(
            {
                'name': f'StepAt{i}chat',  # we ask pak question if user interests and we would go to PAK and allows user to chitchat
            }
        )

    step_state = [{
        'name': f'MethodNo0of1w{N_steps}steps',
        'children': step_states,
        'initial': step_states[0]['name']
    }]


    return step_state, step_transitions

def _get_states(steps_state):
    states = [{
        'name': 'Welcome',
    }, 
    {
        'name': 'TaskChoice',
        'children': ['TaskRecommendation', 'TaskCatalog', 'TaskComparison', 'TaskClarification',
                    'TaskRecommendationchat', 'TaskCatalogchat', 'TaskComparisonchat', 'TaskClarificationchat'],
        'initial': 'TaskCatalog' #'TaskRecommendation'
    }, {
        'name': 'TaskPreparation',
        'children': ['MethodSelection', 'TaskPrepConfirmation', 'MethodSelectionchat', 'TaskPrepConfirmationchat'],
        'initial': 'TaskPrepConfirmation'
    }, {
        'name': 'IngredientQA'
    }, {
        'name': 'QA'
    }, {
        'name': 'PAK' # we ask pak question if user interests and we would go to PAK and allows user to chitchat
    }, {
        'name': 'ListManagement'
    }, {
        'name': 'TimerManagement'
    }, {
        'name': 'Halt'
    }]

    for taco_state in state_to_add:
        if "TaskChoice" not in taco_state and "TaskPreparation" not in taco_state:
            states.append({'name': taco_state})

    if steps_state:
        states.append({
            'name': 'TaskExecution',
            'children':steps_state,            
            'initial': steps_state[0]['name']
        })
    else:
        states.append({
            'name': 'TaskExecution',
        })
    return states


def get_init_state_machine(build_steps = False, is_wikihow = None, article=None, has_parts=False, initial_state = 'Welcome'):
    NestedState.separator = '_'
    step_transitions = []
    steps_state = None
    if build_steps:
        assert (is_wikihow is not None)
        print('[taco sm] build execution states')
        if is_wikihow:
            steps_state, step_transitions = _get_execution_states_and_transitions_wikihow(article, has_parts)
        else:
            steps_state, step_transitions = _get_execution_states_and_transitions_recipe(article)

    # ['xxx', '*', '='] transitions doesn't work for nested states, just ignore them
    transitions = TACO_TRANSITIONS
    transitions.extend(step_transitions)
    transitions.extend(TMP_TRANSITIONS)

    states = _get_states(steps_state)
    machine = HierarchicalMachine (states=states, transitions=transitions, initial=initial_state, ignore_invalid_triggers=True)
    
    # taco_state_machine.add_transition('LaunchRequestIntent', taco.taco_states.TacoStates.TaskExecution,        taco.taco_states.TacoStates.TaskExecution, conditions=[self._is_launch_resume]) # handled by rule
    machine.add_transition('LaunchRequestIntent', 'TaskExecution',                        'Welcome', unless=[Is_launch_resume])
    machine.add_transition('LaunchRequestIntent', 'TaskPreparation_TaskPrepConfirmation', 'TaskPreparation_TaskPrepConfirmation', conditions=[Is_launch_resume_prep])
    machine.add_transition('LaunchRequestIntent', 'TaskPreparation_TaskPrepConfirmation', 'Welcome', unless=[Is_launch_resume_prep])
    machine.add_transition('TaskCompleteIntent', 'TaskExecution', 'Halt', conditions=[Is_confirmed_complete])
    machine.add_transition('TaskRequestIntent', 'Welcome', 'TaskChoice_TaskCatalog', unless=[has_clarification_question]) #unless = False, transition
    machine.add_transition('TaskRequestIntent', 'Welcome', 'TaskChoice_TaskClarification', conditions=[has_clarification_question])
    machine.add_transition('TaskRequestIntent', 'TaskChoice_TaskCatalog', 'TaskChoice_TaskCatalog', unless=[has_clarification_question])
    machine.add_transition('TaskRequestIntent', 'TaskChoice_TaskCatalog', 'TaskChoice_TaskClarification', conditions=[has_clarification_question])
    machine.add_transition('TaskRequestIntent', 'TaskChoice_TaskComparison', 'TaskChoice_TaskCatalog', unless=[has_clarification_question])
    machine.add_transition('TaskRequestIntent', 'TaskChoice_TaskComparison', 'TaskChoice_TaskClarification', conditions=[has_clarification_question])
    machine.add_transition('TaskRequestIntent', 'TaskPreparation', 'TaskChoice_TaskCatalog', unless=[has_clarification_question])
    machine.add_transition('TaskRequestIntent', 'TaskPreparation', 'TaskChoice_TaskClarification', conditions=[has_clarification_question])
    machine.add_transition('AcknowledgeIntent', 'TaskChoice_TaskCatalog', 'TaskPreparation_TaskPrepConfirmation', conditions=[Only_one_query_result])
    machine.add_transition('NegativeAcknowledgeIntent', 'TaskChoice_TaskCatalog', 'Welcome', conditions=[Only_one_query_result])


    return machine
