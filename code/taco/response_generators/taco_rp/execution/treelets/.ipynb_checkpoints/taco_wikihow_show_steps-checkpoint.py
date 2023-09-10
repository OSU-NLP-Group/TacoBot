# from taco.response_modules.execution.template_manager import EXEC_EXCEPTION_TEMPLATES
from taco.response_generators.taco_rp.execution.treelets.template_manager import EXEC_EXCEPTION_TEMPLATES
from taco.response_generators.taco_rp.execution.treelets.utils import (
    add_period, 
    check_resume_task, 
    count_step_and_check_exceptions, 
    decorate_speak_output
)
from cobot_core.apl.utils.documents.detail_apl_document import DetailAplDocument
from cobot_core.apl.utils.items.text_detail_item import TextDetailItem
from taco.response_generators.taco_rp import wikihow_helpers, apl
from taco.response_generators.taco_rp.execution.treelets import visuals, utils

import random
import re

from taco.response_generators.taco_rp.taco_intent_by_rule import TacoIntentByRule


def taco_wikihow_show_steps(current_state, last_state, user_attributes):
    intent = current_state.final_intent
    text = current_state.text
    
    setattr(user_attributes, 'confirmed_complete', False) #reset this flag for every step
    current_step, speak_output = count_step_and_check_exceptions(text, intent, current_state, user_attributes)
    print("RG Show Step @ step ", current_step)
    if speak_output != '':
        return {'response': speak_output, 'shouldEndSession': False}

    current_task = user_attributes.current_task
    current_task_docparse = user_attributes.current_task_docparse
    assert (current_task_docparse is not None)

    method_idx, N_methods, total_steps, current_step_num = TacoIntentByRule.parse_step_nums(user_attributes.taco_state)
    #task = wikihow_helpers.WikiHowTask(user_attributes.query_result[user_attributes.list_item_selected])
    speak_output, document = get_wikihow_steps(current_task_docparse, user_attributes)

    speak_output = check_resume_task(current_state, intent, current_step, speak_output, current_task, total_steps)

    # Check whether device is APL supported or not
    # If device is not APL supported, we should return only voice response
    is_apl_supported = current_state.supported_interfaces.get('apl', False)
    if is_apl_supported and document:
        return {'response': speak_output, 'directives': [document], 'shouldEndSession': False}
    else:
        return {'response': speak_output, 'shouldEndSession': False}


def get_step_text(method, current_step):
    step_text = method.steps[current_step]
    try:
        step_text = add_period(method.headlines[current_step]) + step_text
    except Exception:
        pass

    return step_text


def get_sentences(step_text):
    return re.split(r'\.\s+', re.split(r'\n+', step_text)[0])   


def is_short_step(step_text):
    return len(step_text.split()) <= 30 or len(get_sentences(step_text)) <= 2


def get_speak_output(step_text):
    if is_short_step(step_text):
        speak_output = re.split(r'\n+', step_text)[0]
    else:
        sentences = get_sentences(step_text)
        speak_output = add_period(sentences[0]) + add_period(sentences[1])
    return speak_output


def get_wikihow_steps(current_task_docparse, user_attributes):
    """
    current_task_docparse: (method) list of (step) list of
    {
        'instruction': '',
        'detail': '',
        'tips': [],
        'image': '',
        'qa_context': ''
    }
    """
    method_number, _, total_steps, current_step = TacoIntentByRule.parse_step_nums(user_attributes.taco_state)

    step_text = current_task_docparse[method_number][current_step]['qa_context']
    update_wikihow_user_attrs(user_attributes, current_task_docparse, step_text)
    
    speak_output = current_task_docparse[method_number][current_step]['instruction']
    directive = get_directive(current_task_docparse, speak_output, method_number, current_step, user_attributes)

    speak_output = decorate_speak_output(user_attributes, speak_output, has_parts=user_attributes.has_parts)
    return speak_output, directive


def get_directive(current_task_docparse, speak_output, method_number, current_step, user_attributes):
    is_last_step = utils.is_last_step(current_task_docparse, method_number, current_step, user_attributes.has_parts)

    hint_text = visuals.get_hint_text(current_task_docparse, method_number, current_step, user_attributes.has_parts)

    # \u3164 is an invisible unicode character:
    # https://invisible-characters.com/3164-HANGUL-FILLER.html
    # Without the character, the spacing of the last line of the speak_output
    # is weird (probably because the hint_text is a larger font size)
    body_text = speak_output + ' <br><br> \u3164' + hint_text

    image_source = user_attributes.current_step_details_image
    subtitle = "Alexa Prize - WikiHow"
    step_text = f'Step {current_step + 1} of {len(current_task_docparse[method_number])}'
    if user_attributes.has_parts:
        step_text += f" (Part {method_number + 1} of {len(user_attributes.all_total_steps)})"

    return visuals.base(
        {
            "scrollViewId": "AlexaTextListSequence",
            "headerTitle": user_attributes.current_task,
            "headerSubtitle": subtitle,
            "imageSource": image_source, 
            "defaultImageSource": apl.Urls.default_task_image,
            "backgroundImageSource": apl.Urls.wikihow_background_image,
            "primaryText": None,
            "secondaryText": step_text,
            "bodyText": body_text,
        }, 
        last_step=is_last_step
    )


def update_wikihow_user_attrs(user_attributes, current_task_docparse, step_text):
    current_step_details = getattr(user_attributes, "current_step_details", [])
    if len(current_step_details) >= 2:
        current_step_details.pop(0)
    current_step_details.append(step_text)
    setattr(
        user_attributes,
        "current_step_details",
        current_step_details,
    )

    method_idx, num_methods, total_steps, current_step = TacoIntentByRule.parse_step_nums(user_attributes.taco_state)
    setattr(
        user_attributes,
        "current_step_details_image",
        (
            current_task_docparse[method_idx][current_step]['image']
            if 'image' in current_task_docparse[method_idx][current_step]
            else None
        )
    )

    setattr(
        user_attributes, 
        'current_step_speak', 
        random.choice(EXEC_EXCEPTION_TEMPLATES['steps left'][True]).format(
            method_or_part='part' if user_attributes.has_parts else 'method',
            method_idx=method_idx + 1,
            current_step=current_step + 1,
            total_step=total_steps,
            total_parts=f'There are {num_methods} parts in total.' if user_attributes.has_parts and num_methods > 1 else ''
        )
    )
    setattr(user_attributes, 'current_tip', 0)
    #setattr(user_attributes, 'current_task', task.title)
