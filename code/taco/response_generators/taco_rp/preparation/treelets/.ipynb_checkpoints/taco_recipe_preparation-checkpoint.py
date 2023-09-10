from taco.response_generators.taco_rp.execution.treelets.utils import add_period
from taco.response_generators.taco_rp.preparation.treelets.utils import get_query_result_selected, should_include_headline
from taco.response_generators.taco_rp.preparation.treelets import visuals, template_manager
from taco.response_generators.taco_rp import apl, time_helpers, recipe_helpers, vocab


import random


def taco_recipe_preparation(current_state, last_state, user_attributes):
    is_apl_supported = current_state.supported_interfaces.get('apl', False)
    # <<< Test VUI via interactive-CLI
    #is_apl_supported = False
    # >>> Test VUI via interactive-CLI
    query_result_selected = get_query_result_selected(
        is_apl_supported, 
        current_state, 
        last_state, 
        user_attributes
    )
    
    setattr(user_attributes, 'card_sent', False)
    intent = current_state.final_intent

    docparse = []
    if (
        hasattr(user_attributes, 'current_task_docparse') and
        user_attributes.current_task_docparse
    ):
        docparse = user_attributes.current_task_docparse
    elif (
        hasattr(current_state, 'docparse')
        and isinstance(current_state.docparse, dict)
        and 'docparse' in current_state.docparse
        and current_state.docparse['docparse']
    ):
        docparse = current_state.docparse['docparse'][query_result_selected]

    speak_out, detail_document_dict = get_recipe_speak_out(query_result_selected, is_apl_supported, user_attributes, docparse)
    if intent == 'LaunchRequestIntent' and current_state.resume_task:
        speak_out = random.choice(template_manager.RECIPE_PREP_TEMPLATES['resume_task']) + speak_out

    if is_apl_supported and detail_document_dict is not None:
        #scroll_command_directive = TextListScrollToIndexDirective()
        #scroll_command_directive = scroll_command_directive.build_directive(0)
        return {'response': speak_out, 'directives': [detail_document_dict], 'shouldEndSession': False}
    else:
        return {'response': speak_out, 'shouldEndSession': False}


def get_recipe_headline(summary, query):
    if summary:
        headlines = [add_period(sent) for sent in summary.split(". ")]
        for sent in headlines:
            if should_include_headline(sent, query.lower()):
                return sent

    return ''


def get_recipe_speak_out(list_item_selected, is_apl_supported, user_attributes, docparse):
    """
    Returns response, detail APL document with text and image, and scroll command

    Arguments:
        list_item_selected (int)
        is_apl_supported (bool)
        user_attributes
        docparse (list): A (possibly empty) list of parsed step dictionaries

    Returns:
        (response, dict)
    """

    recipe_query_result = user_attributes.query_result
    recipes = recipe_helpers.query_to_recipes(recipe_query_result)
    detail_document = None

    if list_item_selected >= 0 and list_item_selected < len(recipes):
        recipe = recipes[list_item_selected]
        set_recipe_prep_user_attr(user_attributes, recipe, docparse)
        
        speak_output = vocab.positive_exclamation() + get_recipe_headline(user_attributes.wikihow_summary, recipe.title)
        info_speak = get_speak_info(recipe)

        speak_output += (
            random.choice(template_manager.RECIPE_PREP_TEMPLATES['ingredient'][is_apl_supported]).substitute(num=len(recipe.ingredients), title=recipe.title)
            + info_speak
            + random.choice(template_manager.RECIPE_PREP_TEMPLATES['read'])
            + random.choice(template_manager.RECIPE_PREP_TEMPLATES['start']).substitute(start_question=random.choice(template_manager.START_QUESTION))
        )

        if is_apl_supported:
            detail_document = get_recipe_prep_visual(recipe, docparse)
    else:
        speak_output = "Geez! I messed up something. Would you please say cancel and let's start over? "

    return speak_output, detail_document


def set_recipe_prep_user_attr(user_attributes, recipe, docparse):
    """
    Sets some values on user_attributes for use in later turns.

    Arguments:
        user_attributes
        recipe_title (string)
        list_ingredients (list[string])
        total_steps (int)
    """
    user_attributes.current_step_details = [] # rely on ingredient QA ['. '.join(recipe.ingredients) + '. ']
    user_attributes.current_task_ingredients = ' <break time="300ms"/> '.join(recipe.ingredients) + ' <break time="300ms"/> '
    user_attributes.current_task = recipe.title
    user_attributes.total_steps = recipe.steps
    if docparse:
        user_attributes.all_total_steps = [len(docparse)]
    else:
        user_attributes.all_total_steps = [recipe.steps]
    setattr(user_attributes, 'current_step_speak', f"This recipe has {user_attributes.all_total_steps[0]} {'steps' if user_attributes.all_total_steps[0] > 1 else 'step'}. ")


def get_speak_info(recipe):
    if recipe.stars is not None:
        if recipe.minutes is not None:
            hours, minutes = time_helpers.to_hours_minutes(recipe.minutes)
            time_str = time_helpers.for_speak(hours, minutes)
            return template_manager.RECIPE_PREP_TEMPLATES['info']['two_slots'].format(recipe.stars + ' stars', time_str)
        # else:
        #     # TODO
        #     return template_manager.RECIPE_PREP_TEMPLATES['info']['two_slots'].format(recipe.stars + ' stars', recipe.steps)
    elif recipe.minutes is not None:
        hours, minutes = time_helpers.to_hours_minutes(recipe.minutes)
        time_str = time_helpers.for_speak(hours, minutes)
        return template_manager.RECIPE_PREP_TEMPLATES['info']['one_slot'].format(time_str)

    return ' '


def get_recipe_prep_visual(recipe, docparse):
    """
    Arguments:
        recipe (recipe_helpers.Recipe)
        docparse (list): A (possibly empty) list of parsed step dictionaries

    Returns:
        Dictionary representing APL visual.
    """
    
    subtitle = "Alexa Prize - Whole Foods Market"
    secondary_text = visuals.make_recipe_info(recipe, docparse)
    body_text = visuals.make_recipe_body_text(recipe)

    return visuals.get_recipe_prep_visual({
        "headerTitle": recipe.title,
        "headerSubtitle": subtitle,
        "backgroundImageSource": apl.Urls.recipe_background_image,
        "imageSource": recipe.img_url,
        "secondaryText": secondary_text,
        "primaryText": None,
        "bodyText": body_text,
        **recipe.rating_keys(),
    })
