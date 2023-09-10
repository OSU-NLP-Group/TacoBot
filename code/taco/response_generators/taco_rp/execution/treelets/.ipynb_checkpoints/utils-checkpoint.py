from taco.response_generators.taco_rp.execution.treelets.template_manager import EXE_HINT_TEMPLATES, EXEC_EXCEPTION_TEMPLATES, EXEC_TEMPLATES
from taco.response_generators.taco_rp.taco_intent_by_rule import TacoIntentByRule

import random
import re


def add_period(x):
    x = x.rstrip()
    return (x + ' ') if x[-1] == '.' else (x + '. ')


def method_part_pl_or_not(has_parts, num_methods):
    if has_parts:
        if num_methods > 1:
            return 'parts'
        else:
            return 'part'
    else:
        if num_methods > 1:
            return 'methods'
        else:
            return 'method'


def count_step_and_check_exceptions(text, intent, current_state, user_attributes):
    #current_step = getattr(user_attributes, 'current_step', None)
    has_parts = getattr(user_attributes, 'has_parts', False)
    error_step_num = getattr(current_state, 'error_step_num', None)
    error_method_num = getattr(current_state, 'error_method_num', None)
    method_idx, num_methods, total_steps, current_step = TacoIntentByRule.parse_step_nums(user_attributes.taco_state)
    prev_method_idx, prev_num_methods, prev_total_steps, prev_step = TacoIntentByRule.parse_step_nums(user_attributes.last_taco_state)
    # print('[OOB error step num]: ', error_step_num)
    # print('[OOB error method num]: ', error_method_num)
    # print('[OOB #steps]: ', total_steps)
    # print('[OOB #methods]: ', num_methods)
    if 'TaskPreparation' in user_attributes.last_taco_state:
        setattr(user_attributes, 'task_started', True)
        setattr(user_attributes, 'has_prompted_commands', False)
        setattr(user_attributes, 'has_prompted_details', False)
        setattr(user_attributes, 'has_prompted_repeat', False)
        setattr(user_attributes, 'has_prompted_timer', False)

    speak_output = ''
    if error_step_num is None and error_method_num is None and not getattr(current_state, 'resume_task', False):
        if (
            current_step == 0 and 
            prev_step == 0 and 
            ((not has_parts and prev_method_idx == method_idx) or has_parts) and
            'Detail' not in user_attributes.last_taco_state
        ):
            speak_output = random.choice(EXEC_EXCEPTION_TEMPLATES['first step'])
            if (not has_parts and current_step < total_steps-1) or (has_parts and not (method_idx == num_methods-1 and current_step == total_steps-1)):
                speak_output = speak_output + random.choice(EXE_HINT_TEMPLATES['next to move on'])
        elif(
            (method_idx == num_methods - 1 or not has_parts) and
            method_idx == prev_method_idx and
            current_step == total_steps - 1 and 
            prev_step == current_step
        ):
            speak_output = random.choice(EXEC_EXCEPTION_TEMPLATES['no more step'])
    elif error_step_num and error_step_num >= total_steps:
        #TODO
        speak_output = random.choice(EXEC_EXCEPTION_TEMPLATES['step overflow'][num_methods>1]).format(
            steps=total_steps,
            is_or_are=('are' if total_steps > 1 else 'is'),
            method_or_part=('part' if has_parts else 'method'),
            method_idx=method_idx + 1
        )
        if (not has_parts and current_step < total_steps-1) or (has_parts and not (method_idx == num_methods-1 and current_step == total_steps-1)):
            if current_step < total_steps-1:
                speak_output = speak_output + random.choice(EXE_HINT_TEMPLATES['next to move on or last step'])
            else: 
                speak_output = speak_output + random.choice(EXE_HINT_TEMPLATES['next to move on'])
    elif error_step_num and error_step_num < 0 and current_step >= 0:
        speak_output = random.choice(EXEC_EXCEPTION_TEMPLATES['step underflow']).format(
            step_idx=current_step+1
        )
        if (not has_parts and current_step < total_steps-1) or (has_parts and not (method_idx == num_methods-1 and current_step == total_steps-1)):
            speak_output = speak_output + random.choice(EXE_HINT_TEMPLATES['next to move on'])
    elif error_method_num and error_method_num >= num_methods:
        speak_output = random.choice(EXEC_EXCEPTION_TEMPLATES['method overflow']).format(
            total=num_methods,
            is_or_are=('are' if num_methods > 1 else 'is'),
            method_or_part1=method_part_pl_or_not(has_parts, num_methods),
        )
        if (not has_parts and current_step < total_steps-1) or (has_parts and not (method_idx == num_methods-1 and current_step == total_steps-1)):
            if num_methods == 1:
                speak_output = speak_output + random.choice(EXE_HINT_TEMPLATES['next to move on'])
            elif num_methods > 1:
                speak_out = speak_out + random.choice(EXE_HINT_TEMPLATES['next to move on or last method_part']).format(
                    method_or_part='part' if has_parts else 'method'
                )
    else:
        setattr(user_attributes, 'current_step', current_step)

    if intent in ['CancelIntent', 'GoBackIntent', 'TaskRequestIntent'] or 'something else' in text or 'different' in text: 
        speak_output = random.choice(EXEC_EXCEPTION_TEMPLATES['switch task'])

    return current_step, speak_output

# depreciated
# def update_step_number(current_step, text, intent, user_attributes):
#     total_steps = getattr(user_attributes, 'total_steps', 0)
#     navi_intent, step_num = TacoIntentByRule.parse_navi_intents(text, total_steps)
#     if current_step is None:
#         setattr(user_attributes, 'has_prompted_commands', False)
#         setattr(user_attributes, 'has_prompted_details', False)
#         setattr(user_attributes, 'has_prompted_repeat', False)
#         setattr(user_attributes, 'has_prompted_timer', False)
#         return 0
#     elif navi_intent == "NaviNextIntent" or intent == "AcknowledgeIntent":
#         return current_step + 1
#     elif navi_intent == "NaviPreviousIntent":
#         return current_step - 1
#     elif navi_intent == "Navi2StepIntent" and step_num > 0:
#         return step_num - 1 # steps are 0-indexed
#     elif navi_intent == "NaviForwardStepsIntent" and step_num > 0:
#         return current_step + step_num
#     elif navi_intent == "NaviBackStepsIntent" and step_num < current_step and step_num > 0:
#         return current_step - step_num
#     elif user_attributes.last_taco_state == "TaskDetails":
#         return current_step + 1
    
#     # if parsing fails, do nothing
#     return current_step


def add_step_markers(current_step, total_steps, method_idx, num_methods, speak_output, user_attributes):
    has_parts = user_attributes.has_parts
    
    if current_step == 0 and 'TaskPreparation' not in user_attributes.last_taco_state:
        if has_parts:
            speak_output = random.choice(EXEC_TEMPLATES['method and part markers']['part']).format(method_idx + 1) + speak_output
        else:
            speak_output = random.choice(EXEC_TEMPLATES['method and part markers']['method']).format(method_idx + 1) + speak_output
  
    if total_steps >= 5 and current_step == ((total_steps - 1) // 2):
        speak_output = random.choice(EXEC_TEMPLATES['step markers']['half']) + speak_output
    elif total_steps >= 7 and (total_steps - current_step) == 3:
        speak_output = random.choice(EXEC_TEMPLATES['step markers']['three more']) + speak_output
    elif current_step == (total_steps - 1):
        if has_parts:
            if method_idx < num_methods -1:
                speak_output += random.choice(EXEC_TEMPLATES['last step inst']['last step of part'])
            else:
                speak_output = random.choice(EXEC_TEMPLATES['step markers']['last']) + speak_output
                speak_output += random.choice(EXEC_TEMPLATES['last step inst']['ending step'])
        else:
            speak_output = random.choice(EXEC_TEMPLATES['step markers']['last']) + speak_output
            speak_output += random.choice(EXEC_TEMPLATES['last step inst']['ending step'])
    
    return speak_output


def decorate_speak_output(user_attributes, speak_output, has_parts = False):
    method_idx, num_methods, total_steps, current_step = TacoIntentByRule.parse_step_nums(user_attributes.taco_state)
    speak_output = f'Step {current_step + 1}. ' + speak_output

    is_wikihow = getattr(user_attributes, 'is_wikihow', False)
    has_prompted_commands = getattr(user_attributes, 'has_prompted_commands', False)
    has_prompted_details = getattr(user_attributes, 'has_prompted_details', False)
    has_prompted_timer = getattr(user_attributes, 'has_prompted_timer', False)
    all_total_steps = getattr(user_attributes, 'all_total_steps', None)

    if 'TaskPreparation' in user_attributes.last_taco_state:
    #if method_idx == 0 and current_step == 0 and not has_prompted_commands:
        if has_parts:
            speak_output = (
                f'The <say-as interpret-as=\"ordinal\"> {method_idx + 1} </say-as> part has {total_steps} steps. ' + 
                EXEC_TEMPLATES['warning'][0] +
                speak_output + 
                random.choice(EXEC_TEMPLATES['navi'])
            )
        else:
            if not is_wikihow:
                speak_output = (
                    f'This recipe has {total_steps} steps. ' + 
                    EXEC_TEMPLATES['warning'][0] +
                    speak_output + 
                    random.choice(EXEC_TEMPLATES['navi'])
                )
            else:                
                speak_output = (
                    f'The <say-as interpret-as=\"ordinal\"> {method_idx + 1} </say-as> method has {total_steps} steps. ' + 
                    EXEC_TEMPLATES['warning'][0] +
                    speak_output + 
                    random.choice(EXEC_TEMPLATES['navi'])
                )
        setattr(user_attributes, 'has_prompted_commands', True)
    elif method_idx < num_methods and current_step < total_steps - 1:
        if is_wikihow:
            if (
                user_attributes.current_task_docparse[method_idx][current_step]['detail'] and 
                not has_prompted_details
            ):
                speak_output += random.choice(EXEC_TEMPLATES['details'])
                setattr(user_attributes, 'has_prompted_details', True)
        elif not has_prompted_timer:
            timer_prompt = add_timer_prompt(speak_output)
            speak_output += timer_prompt
            if timer_prompt:
                setattr(user_attributes, 'has_prompted_timer', True)
            

    speak_output = add_step_markers(current_step, total_steps, method_idx, num_methods, speak_output, user_attributes)
    
    return speak_output


def add_timer_prompt(speak_output):
    # TODO need text2num
    time_phrases = re.findall(
        r'(\d+ seconds|1 minute|\d+ minutes|1 hour|\d+ hours|\d+ hours \d+ minutes|1 hour \d+ minutes|\d+ minutes \d+ seconds|1 minute \d+ seconds)', 
        speak_output
    )

    if len(time_phrases) > 0:
        prompt = random.choice(EXEC_TEMPLATES['timer']).format(time_phrases[-1])
        return prompt
    else:
        return ''

def check_resume_task(current_state, intent, current_step, speak_output, current_task, total_steps):
    # Add a welcome prompt for RETURNING users before giving instructions.
    resume_task = getattr(current_state, 'resume_task', False)
    if intent == 'LaunchRequestIntent' and resume_task:  
        if current_task != None:
            setattr(current_state, 'resume_task', False) # otherwise, the following turns all have this field as True.
            speak_output = add_resume_prompt(current_task, current_step, total_steps) + speak_output
    return speak_output

def add_resume_prompt(current_task, current_step, total_steps):
    return random.choice(EXEC_TEMPLATES['resume']).format(current_task, current_step + 1, total_steps)


def is_last_step(docparse, method_number, step_number, has_parts):
    """
    Assumes method_number and step_number are 0-indexed.

    Arguments:
        docparse (list[list[dict]]): List of methods, which have a list of steps, which are dictionaries.
        method_number (int): Recipes are always method 0.
        step_number (int): current step.
        has_parts (bool): Recipes are always false.

    Returns (bool) Whether we are at the last step.
    """

    if not docparse:
        return True

    if method_number >= len(docparse):
        return True

    if has_parts:
        # We have to be on the final part AND be past the last step
        return method_number == len(docparse) - 1 and step_number >= len(docparse[method_number]) - 1
    else:
        return step_number >= len(docparse[method_number]) - 1
