from taco.response_generators.taco_rp.execution.treelets.utils import add_period, method_part_pl_or_not
from taco.response_generators.taco_rp.preparation.treelets.template_manager import START_QUESTION, WIKIHOW_PREP_TEMPLATES
from taco.response_generators.taco_rp.preparation.treelets.utils import get_query_result_selected, should_include_headline
from taco.response_generators.taco_rp.preparation.treelets.visuals import get_wikihow_prep_visual
from taco.response_generators.taco_rp import wikihow_helpers, vocab


import random


def taco_wikihow_preparation(current_state, last_state, user_attributes):
    is_apl_supported = current_state.supported_interfaces.get('apl', False)
    query_result_selected = get_query_result_selected(
        is_apl_supported, 
        current_state, 
        last_state, 
        user_attributes
    )
    
    setattr(user_attributes, 'card_sent', False)
    intent = current_state.final_intent

    speak_out, detail_document = get_wikihow_speak_out(is_apl_supported, query_result_selected, user_attributes)

    if intent == 'LaunchRequestIntent' and current_state.resume_task:
        speak_out = random.choice(WIKIHOW_PREP_TEMPLATES['resume_task']) + speak_out

    if is_apl_supported and detail_document is not None:
        return {'response': speak_out, 'directives': [detail_document], 'shouldEndSession': False}
    else:
        return {'response': speak_out, 'shouldEndSession': False}


def get_popularity(wikihow_task):
    speak_out = ""

    if wikihow_task.views >= 1000000:
        speak_out = random.choice(WIKIHOW_PREP_TEMPLATES["views"]["million"])
    elif wikihow_task.views >= 100000:
        speak_out = random.choice(WIKIHOW_PREP_TEMPLATES["views"]["many_thousands"])
    elif wikihow_task.views >= 1000:
        speak_out = random.choice(WIKIHOW_PREP_TEMPLATES["views"]["few_thousands"])
    else:
        speak_out = random.choice(WIKIHOW_PREP_TEMPLATES["views"]["not_many"])

    return speak_out


def get_summary_headline(wikihow_task):
    if wikihow_task.has_summary:
        headlines = [add_period(sent) for sent in wikihow_task.item["summaryText"].split(". ")]
        for sent in headlines:
            if should_include_headline(sent, wikihow_task.title.lower()):
                return sent

    return ''


def get_wikihow_speak_out(is_apl_supported, query_result_selected, user_attributes):
    if query_result_selected >= 0 and query_result_selected < len(user_attributes.query_result):
        wikihow_task = wikihow_helpers.WikiHowTask(user_attributes.query_result[query_result_selected])
        popularity_speak_out = get_popularity(wikihow_task)

        speak_out = vocab.positive_exclamation() + get_summary_headline(wikihow_task) + (
            (
                random.choice(WIKIHOW_PREP_TEMPLATES['rating']['default']).format(wikihow_task.title) 
                if wikihow_task.stars is None 
                else random.choice(WIKIHOW_PREP_TEMPLATES['rating']['has_rating']).format(wikihow_task.title, wikihow_task.stars)
            ) +
            popularity_speak_out
        ) 

        detail_document = None
        if is_apl_supported:
            detail_document = get_wikihow_prep_visual(wikihow_task)
            if not wikihow_task.has_parts:
                if len(wikihow_task.all_steps) > 1:
                    speak_out += random.choice(WIKIHOW_PREP_TEMPLATES["methods"])
        speak_out += random.choice(START_QUESTION)

        setattr(user_attributes, 'all_total_steps', wikihow_task.all_steps)
        setattr(user_attributes, 'has_parts', wikihow_task.has_parts)
        setattr(user_attributes, 'total_steps', wikihow_task.steps)
        setattr(user_attributes, 'current_task', wikihow_task.title)
        if len(wikihow_task.all_steps) > 1:
            setattr(user_attributes, 'current_step_speak', f"This task has {len(wikihow_task.all_steps)} {method_part_pl_or_not(wikihow_task.has_parts, len(wikihow_task.all_steps))}. The first {'part' if wikihow_task.has_parts else 'method'} has {wikihow_task.steps} steps. ")
        elif len(wikihow_task.all_steps) == 1:
            setattr(user_attributes, 'current_step_speak', f"This task has {wikihow_task.steps} {'steps' if wikihow_task.steps > 1 else 'step'}. ")
    else:
        detail_document = None
        speak_out = "Geez! I messed up something. Would you please say cancel and let's start over? "

    return speak_out, detail_document
