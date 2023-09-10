from taco.response_generators.taco_rp.execution.treelets.template_manager import EXEC_EXCEPTION_TEMPLATES
from taco.response_generators.taco_rp.execution.treelets.utils import (
    add_period, 
    check_resume_task, 
    count_step_and_check_exceptions, 
    decorate_speak_output
)
from taco.response_generators.taco_rp import apl, helpers, recipe_helpers
from taco.response_generators.taco_rp.execution.treelets import visuals

import random
import re

from taco.response_generators.taco_rp.taco_intent_by_rule import TacoIntentByRule


def taco_recipe_show_steps(current_state, last_state, user_attributes):
    intent = current_state.parsed_intent
    text = current_state.text
    
    setattr(user_attributes, 'confirmed_complete', False) #reset this flag for every step
    current_step, speak_output = count_step_and_check_exceptions(text, intent, current_state, user_attributes)
    print("RG Show Step @ step ", current_step)
    # user_attributes.current_step_num = current_step
    setattr(user_attributes, 'current_step_num', int(current_step))
    print('user_attributes = ', user_attributes.current_step_num)
    if speak_output != '':
        return {'response': speak_output, 'shouldEndSession': False}

    current_task = user_attributes.current_task
    current_task_docparse = user_attributes.current_task_docparse
    assert (current_task_docparse is not None)
    
    method_idx, N_methods, total_steps, current_step_num = TacoIntentByRule.parse_step_nums(current_state.status)
    speak_output, document = get_recipe_steps(current_task_docparse, current_step, current_state, user_attributes)
    # print('speak_output = ', speak_output)
    speak_output = check_resume_task(current_state, intent, current_step, speak_output, current_task, total_steps)

    # print('speak_output = ', speak_output)

    # Check whether device is APL supported or not
    # If device is not APL supported, we should return only voice response
    is_apl_supported = current_state.supported_interfaces.get('apl', False)
    if is_apl_supported and document:
        return {'response': speak_output, 'directives': [document], 'shouldEndSession': False}
    else:
        return {'response': speak_output, 'shouldEndSession': False}


def get_recipe_steps(current_task_docparse, current_step, current_state, user_attributes):
    """
    Arguments:
        current_task_docparse: list of
        {
            'instruction': '',
            'image': '',
            'ingredients': ''
        }
    """

    primary_text = current_task_docparse[current_step]['instruction']
    update_recipe_user_attrs(current_step, user_attributes, primary_text, len(current_task_docparse))
    
    speak_output = re.sub(r"\(.*?\)", "", primary_text)
    speak_output = decorate_speak_output(current_state, user_attributes, speak_output)

    directive = get_directive(user_attributes.current_task, current_task_docparse, current_step)

    return speak_output, directive


def get_step_image(recipe, step):
    if step.images:
        return step.images[0]

    if len(recipe.item['images']) > 0:
        return recipe.item['images'][0]['url']

    return None


def get_recipe_step_info(step):
    if not step['ingredients']:
        return ''

    ingredients = ' <br> '.join(['- ' + item['displayText'] for item in step['ingredients']])
    ingredient_display = f'<br><b>Ingredients: </b> <br> {ingredients}'

    return ingredient_display


def update_recipe_user_attrs(current_step, user_attributes, primary_text, step_number):
    current_step_details = getattr(user_attributes, "current_step_details", [])
    if len(current_step_details) >= 2:
        current_step_details.pop(0)
    current_step_details.append(primary_text)

    setattr(
        user_attributes, 
        'current_step_details', 
        current_step_details
    )
    setattr(
        user_attributes, 
        'current_step_speak', 
        random.choice(EXEC_EXCEPTION_TEMPLATES['steps left'][False]).format(
            current_step=current_step + 1, 
            total_step=step_number
        )
    )
    #setattr(user_attributes, 'current_task', recipe_title)


def get_directive(recipe_title, current_task_docparse, current_step):
    """
    Arguments:
        recipe_title (str): the recipe title
        current_task_docparse (list[dict]): a list of dicts containing keys 'instruction', 'image', 'ingredients'
        current_step (int): the current step (0-indexed)
        total_steps (int): total recipe steps
    """

    subtitle = "Alexa Prize - Whole Foods Market"
    step_text = f'Step {current_step + 1} of {len(current_task_docparse)}'

    step = current_task_docparse[current_step]

    image = step['image'] if 'image' in step else None

    body_text = step['instruction']

    ingredient_display = get_recipe_step_info(step)
    if ingredient_display:
        body_text += ' <br> ' + ingredient_display

    hint_text = visuals.get_hint_text([current_task_docparse], 0, current_step, False)
    # \u3164 is an invisible unicode character: 
    # https://invisible-characters.com/3164-HANGUL-FILLER.html
    # Without the character, the spacing of the last line of the speak_output 
    # is weird (probably because the hint_text is a larger font size)
    body_text += ' <br> <br> \u3164' + hint_text

    last_step = current_step + 1 >= len(current_task_docparse)

    return visuals.base(
        {
            "scrollViewId": "AlexaTextListSequence",
            "headerTitle": recipe_title,
            "headerSubtitle": subtitle,
            "backgroundImageSource": apl.Urls.recipe_background_image,
            "defaultImageSource": apl.Urls.default_recipe_image,
            "imageSource": image,
            "primaryText": None,
            "secondaryText": step_text,
            "bodyText": body_text,
        }, 
        last_step=last_step,
    )
