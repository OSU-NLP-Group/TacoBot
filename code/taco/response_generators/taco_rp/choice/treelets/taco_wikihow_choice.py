from cobot_core.apl.utils.commands.image_list_scroll_to_index_directive import ImageListScrollToIndexDirective
from taco.response_generators.taco_rp.choice.treelets.taco_data_manager import get_task_recommendation
from taco.response_generators.taco_rp.choice.treelets.utils.general import check_exception, get_current_choices, select_followup_template, set_query_user_attributes, update_choice_idx
from taco.response_generators.taco_rp.choice.treelets.utils import visuals
from taco.response_generators.taco_rp.choice.treelets import template_manager
from taco.response_generators.taco_rp import apl, wikihow_helpers
from taco.response_generators.taco_rp import examples


def taco_wikihow_choice(current_state, last_state, user_attributes, toolkit_service_client):
    """
    Arguments:
        current_state
        last_state
        user_attributes
        toolkit_service_client
    Returns:
        dict with keys "response" and "shouldEndSession".
        "response" is the speaking response.
        "shouldEndSession" is always either False or None.
    """
    intent = getattr(current_state, 'parsed_intent', None)
    query = getattr(user_attributes, 'query', None)
    first_visit = getattr(user_attributes, 'first_visit', True)
    wikihow_query_result = getattr(user_attributes, 'query_result', None)

    tasks = []
    if isinstance(wikihow_query_result, list) and len(wikihow_query_result) > 0:
        # We don't need to check if there are more 9 items because if there are fewer 9 items, [:9] selects all the items.
        tasks = [item["_source"]["articleTitle"] for item in wikihow_query_result[:9]]
    else:
        wikihow_query_result = get_task_recommendation()
        tasks = [item["_source"]["articleTitle"] for item in wikihow_query_result[:9]]
        setattr(current_state, 'is_rec', True)
        setattr(current_state, 'no_result', True)

    speak_output = check_exception(intent, len(tasks), user_attributes)
    if speak_output:
        return {"response": speak_output, "shouldEndSession": False}
    
    speak_output = get_wikihow_query_speak_output(tasks, query, intent, current_state, user_attributes)
    
    is_apl_supported = current_state.supported_interfaces.get("apl", False)
    choice_start_idx = getattr(user_attributes, 'choice_start_idx', 0)
    cont_reqs = getattr(user_attributes, 'cont_reqs', 0)
    cont_reqs = 0 if cont_reqs is None else cont_reqs

    if not is_apl_supported:
        return {"response": speak_output, "shouldEndSession": False}
    elif wikihow_query_result and choice_start_idx < len(wikihow_query_result) and choice_start_idx < 9 and cont_reqs <= 3:
        wikihow_tasks = wikihow_helpers.query_to_tasks(wikihow_query_result)
        apl_directive = get_task_directive(wikihow_tasks, query)
        scroll_command_directive = ImageListScrollToIndexDirective()

        if intent == 'MoreChoiceIntent':
            scroll_command_directive = scroll_command_directive.build_directive(choice_start_idx + 2)
        else:
            scroll_command_directive = scroll_command_directive.build_directive(choice_start_idx)
        
        if first_visit or intent in ['CancelIntent', 'GoBackIntent', 'NaviPreviousIntent']:
            set_query_user_attributes(wikihow_query_result, user_attributes)
            return {"response": speak_output, "directives": [apl_directive, scroll_command_directive], "shouldEndSession": False}
        else:
            return {"response": speak_output, "directives": [scroll_command_directive], "shouldEndSession": False}
    else:
        return {"response": speak_output, "shouldEndSession": False}


def get_wikihow_query_speak_output(tasks, query, intent, current_state, user_attributes):
    """
    Gets the speaking output for a wikihow query.
    Arguments:
        tasks (list[string]) list of task titles
        query (optional string)
        intent (optional string)
        current_state
        user_attributes
    Returns:
        The speaking output as a string.
    """
    # Type asserts
    assert isinstance(tasks, list)
    assert query is None or isinstance(query, str)
    assert intent is None or isinstance(intent, str)

    num_results = len(tasks)
    cont_reqs = getattr(user_attributes, 'cont_reqs', 0)
    cont_reqs = 0 if cont_reqs is None else cont_reqs
    choice_start_idx = update_choice_idx(intent, user_attributes)

    current_tasks = get_current_choices(tasks, choice_start_idx)

    speak_output = ''

    # num_results should never be 0 now
    # if num_results == 0:
    #     speak_output = template_manager.no_results(wikihow=True).substitute(query=query)

    if choice_start_idx < num_results and choice_start_idx < 9 and cont_reqs <= 3:
        speak_output = select_wikihow_template(query, current_tasks, num_results, choice_start_idx, current_state, user_attributes)
    else:
        setattr(user_attributes, 'cont_reqs', 0)
        speak_output = template_manager.nothing_better(wikihow=True).substitute(task=examples.random_task())
    return speak_output


def select_wikihow_template(query, tasks, num_results, choice_start_idx, current_state, user_attributes):
    """
    Arguments:
        query
        tasks: (list of string)
    """
    is_rec = getattr(current_state, 'is_rec', False)
    search_timeout = getattr(current_state, 'search_timeout', False)
    no_result = getattr(current_state, 'no_result', False)
    first_visit = getattr(user_attributes, 'first_visit', True)

    speak_output = (
        select_segment1(query, first_visit, is_rec, search_timeout, no_result) + 
        select_segment2(choice_start_idx, is_rec, num_results, first_visit) +
        select_segment3(tasks, user_attributes)
        #select_followup_template(num_results, choice_start_idx, first_visit)
    )

    setattr(user_attributes, 'first_visit', False)
    return speak_output


def select_segment1(query, first_visit, is_rec, search_timeout, no_result):
    speak_output = ''

    if first_visit:
        if is_rec:
            if search_timeout:
                speak_output = template_manager.search_timeout(wikihow=True).substitute(query=query)
            elif no_result:
                speak_output = template_manager.no_results(wikihow=True).substitute(query=query)
            else:
                speak_output = template_manager.first_visit_recommend(wikihow=True).substitute()
        else:
            speak_output = template_manager.help_with_query(wikihow=True, has_query=bool(query)).substitute(query=query)

    return speak_output


def select_segment2(choice_start_idx, is_rec, num_results, first_visit):
    speak_output = ''
    if choice_start_idx == 0:
        if is_rec:
            speak_output = template_manager.option_intro(wikihow=True).substitute()
        elif num_results - choice_start_idx == 1:
            speak_output = "I found only one article in Wikihow. "
        elif num_results - choice_start_idx == 2:
            speak_output = 'I only found two articles in Wikihow. '
        else:
            speak_output = 'I found several articles in Wikihow. '
    else:
        if num_results - choice_start_idx == 1:
            speak_output = "Here is the only article left. "
        elif num_results - choice_start_idx == 2:
            speak_output = 'Here are the remaining two articles. '
        else:
            speak_output = 'Here are the next three articles. '
    
    if first_visit:
        if num_results - choice_start_idx >= 3:
            speak_output += 'You can ask me to compare them or tell you more options. '
        elif num_results - choice_start_idx > 1:
            speak_output += 'You can ask me to compare them. '
    
    if num_results - choice_start_idx > 1:
        speak_output += 'Which one do you want: '
    
    return speak_output


def select_segment3(tasks, user_attributes):
    proposed_tasks = None

    if len(tasks) == 1:
        proposed_tasks = [
            {"title" : tasks[0]}
        ]
        speak_output = f'Do you want this option, {tasks[0]}? '
        user_attributes.list_item_rec = getattr(user_attributes, 'choice_start_idx', 0)
    elif len(tasks) == 2:
        proposed_tasks = [
            {"title" : tasks[0]},
            {"title" : tasks[1]}
        ]
        speak_output = f'the first, {tasks[0]}, or the second, {tasks[1]}? '
        user_attributes.list_item_rec = -1
    elif len(tasks) == 3:
        proposed_tasks = [
            {"title" : tasks[0]},
            {"title" : tasks[1]},
            {"title" : tasks[2]}
        ]
        speak_output = f'the first, {tasks[0]}, the second, {tasks[1]}, or the third, {tasks[2]}? '
        user_attributes.list_item_rec = -1
    else: #should never happen
        speak_output = ''
        user_attributes.list_item_rec = -1

    if proposed_tasks:
        user_attributes.proposed_tasks = proposed_tasks
                        
    return speak_output


def get_task_directive(wikihow_tasks, query):
    """
    Arguments:
        wikihow_tasks (List of WikiHowTask)
        query (string|None) original user query
    Returns:
        Dictionary representing APL visual.
    """
    list_items = [visuals.make_list_item(task) for task in wikihow_tasks]
    title = f"WikiHow Results for “{query}” (Alexa Prize)"
    if not query:
        title = "Recommended DIY Tasks from WikiHow (Alexa Prize)"

    return visuals.base({
        "listItems": list_items,
        "headerTitle": title,
        "defaultImageSource": apl.Urls.default_task_image,
        "backgroundImageSource": apl.Urls.wikihow_background_image,
    })