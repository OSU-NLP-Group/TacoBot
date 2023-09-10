from taco.response_generators.taco_rp.execution.treelets.template_manager import DETAIL_TIP_TEMPLATES
from taco.response_generators.taco_rp.execution.treelets import visuals, utils
from taco.response_generators.taco_rp import apl

import random
import re

from taco.response_generators.taco_rp.taco_intent_by_rule import TacoIntentByRule


def taco_wikihow_details(current_state, last_state, user_attributes):
    current_task_docparse = user_attributes.current_task_docparse
    assert (current_task_docparse is not None)

    speaker_output = ''
    is_apl_supported = current_state.supported_interfaces.get('apl', False)
    method_idx, N_methods, total_steps, current_step = TacoIntentByRule.parse_step_nums(user_attributes.taco_state)

    speaker_output = get_shared_detail_text(current_task_docparse[method_idx][current_step])

    if not speaker_output:
        return {'response': random.choice(DETAIL_TIP_TEMPLATES['no detail']), 
            'shouldEndSession': False}
    
    # remove contents in brackets if too long
    if len(speaker_output.split()) >= 40:
        speaker_output = re.sub(r'\(.*?\)', '', speaker_output)
    # add warning if still very long
    if len(speaker_output.split()) >= 40:
        speaker_output = random.choice(DETAIL_TIP_TEMPLATES['long detail']) + speaker_output
    
    # Say something about this step having tips.
    num_tips = len(current_task_docparse[method_idx][current_step]['tips'])
    if num_tips > 0:
        speaker_output += random.choice(DETAIL_TIP_TEMPLATES['ask more tips']).format(
            num_tips if num_tips > 1 else "",
            "tips" if num_tips > 1 else "tip"
        )
    else:
        speaker_output += random.choice(DETAIL_TIP_TEMPLATES['no more tips'])

    if not is_apl_supported:
        return {'response': speaker_output, 'shouldEndSession': False}
    else:
        document = get_details_apl_doc(user_attributes)
        return {'response': speaker_output, 
            'directives': [document], 
            'shouldEndSession': False}


def get_shared_detail_text(step_dict):
    """
    Get any text shared between the APL screen and the utterance.
    """
    if step_dict['detail']:
        return step_dict['detail']
    
    return None


def taco_wikihow_tips(current_state, last_state, user_attributes):
    current_task_docparse = user_attributes.current_task_docparse
    assert (current_task_docparse is not None)

    speaker_output = ''
    is_apl_supported = current_state.supported_interfaces.get('apl', False)

    method_idx, N_methods, total_steps, current_step = TacoIntentByRule.parse_step_nums(user_attributes.taco_state)
    tip_no = int(re.findall(r'tipNo(\d+)', user_attributes.taco_state)[0])
    
    speaker_output = get_shared_tips_text(current_task_docparse[method_idx][current_step], tip_no)

    num_tips = len(current_task_docparse[method_idx][current_step]['tips'])
    if tip_no == num_tips - 1:
        if num_tips > 1:
            speaker_output = 'Last tip! ' + speaker_output
        speaker_output += random.choice(DETAIL_TIP_TEMPLATES['no more tips'])
    else:
        speaker_output += random.choice(DETAIL_TIP_TEMPLATES['next tip'])

    if not is_apl_supported:
        return {'response': speaker_output, 'shouldEndSession': False}
    else:
        document = get_tips_apl_doc(user_attributes)
        return {'response': speaker_output, 
            'directives': [document], 
            'shouldEndSession': False}


def get_shared_tips_text(step_dict, tip_number):
    """
    Get the text shared between the tips APL screen and the utterance.

    Arguments:
        step_dict (dict)
        tip_number (int): current tip selected
    """
    if len(step_dict['tips']) > 1:
        return f'Tip {tip_number + 1}: ' + step_dict['tips'][tip_number]
    else:
        return step_dict['tips'][tip_number]


def get_details_apl_doc(user_attributes):
    method_number, _, total_steps, step_number = TacoIntentByRule.parse_step_nums(user_attributes.taco_state)
    step_dict = user_attributes.current_task_docparse[method_number][step_number]

    image_source = user_attributes.current_step_details_image
    header_title = f"Details for “{user_attributes.current_task}”"
    step_text = f'Details for Step {step_number + 1} of {total_steps}'

    body_text = get_shared_detail_text(step_dict)
    # This should never happen, because taco_wikihow_details() checks if
    # the step has details first.
    if not body_text:
        body_text = ''

    # If this step has tips, then we want to override the next button's text.
    # It should say "Tips" rather than "Next" or "Complete".
    overrides = {}
    if step_dict['tips']:
        overrides["button2Text"] = "Tips"

    return visuals.base(
        {
            "headerTitle": header_title,
            "headerSubtitle": "Alexa Prize - WikiHow",
            "imageSource": image_source,
            "defaultImageSource": apl.Urls.default_task_image,
            "backgroundImageSource": apl.Urls.wikihow_background_image,
            "primaryText": None,
            "secondaryText": step_text,
            "bodyText": body_text,
            **overrides,
        }, 
        last_step=utils.is_last_step(
            user_attributes.current_task_docparse,
            method_number,
            step_number, 
            user_attributes.has_parts,
        )
    )


def get_tips_apl_doc(user_attributes):
    method_number, _, total_steps, step_number = TacoIntentByRule.parse_step_nums(user_attributes.taco_state)
    tip_number = int(re.findall(r'tipNo(\d+)', user_attributes.taco_state)[0])
    step_dict = user_attributes.current_task_docparse[method_number][step_number]

    image_source = user_attributes.current_step_details_image
    header_title = f"Tips for “{user_attributes.current_task}”"
    step_text = f"Tip {tip_number + 1} of {len(step_dict['tips'])} (Step {step_number + 1} of {total_steps})"

    body_text = get_shared_tips_text(step_dict, tip_number)
    
    next_button = 'Next Step'
    if tip_number < len(step_dict['tips']) - 1:
        next_button = 'Next Tip'

    return visuals.base(
        {
            "headerTitle": header_title,
            "headerSubtitle": "Alexa Prize - WikiHow",
            "imageSource": image_source,
            "defaultImageSource": apl.Urls.default_task_image,
            "backgroundImageSource": apl.Urls.wikihow_background_image,
            "primaryText": None,
            "secondaryText": step_text,
            "bodyText": body_text,
            "button2Text": next_button,
        }, 
        last_step=utils.is_last_step(
            user_attributes.current_task_docparse,
            method_number,
            step_number, 
            user_attributes.has_parts,
        )
    )
