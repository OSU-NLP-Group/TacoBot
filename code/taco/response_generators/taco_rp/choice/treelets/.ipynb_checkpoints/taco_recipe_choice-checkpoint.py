from cobot_core.apl.utils.commands.image_list_scroll_to_index_directive import ImageListScrollToIndexDirective
from taco.response_generators.taco_rp.choice.treelets.taco_data_manager import select_recipe_recommendation
from taco.response_generators.taco_rp.choice.treelets.utils.general import check_exception, get_and_list_prompt, get_current_choices, select_followup_template, set_query_user_attributes, update_choice_idx, get_constraints
from taco.response_generators.taco_rp.choice.treelets.utils import visuals
from taco.response_generators.taco_rp.choice.treelets import template_manager
from taco.response_generators.taco_rp import recipe_helpers, apl
from taco.response_generators.taco_rp import examples


def taco_recipe_choice(current_state, last_state, user_attributes, toolkit_service_client):
    intent = getattr(current_state, 'final_intent', None)
    query = getattr(user_attributes, 'query', None)
    first_visit = getattr(user_attributes, 'first_visit', True)
    recipe_query_result = getattr(user_attributes, 'query_result', None)

    recipes = []
    if (recipe_query_result is not None and 
        'documents' in recipe_query_result and
        len(recipe_query_result['documents']) > 0
    ):
        # We don't need to check if there are more 9 recipes because if there are fewer 9 recipes, [:9] selects all the recipes.
        recipes = recipe_helpers.query_to_recipes(recipe_query_result)[:9]
    else:
        recipes = recipe_helpers.query_to_recipes(
            select_recipe_recommendation(current_state, user_attributes)
        )
        setattr(current_state, 'is_rec', True)
        setattr(current_state, 'no_result', True)

    speak_output = check_exception(intent, len(recipes), user_attributes)
    if speak_output:
        return {"response": speak_output, "shouldEndSession": False}
    speak_output = get_recipe_query_speak_output(recipes, query, intent, current_state, user_attributes)

    is_apl_supported = current_state.supported_interfaces.get('apl', False)
    choice_start_idx = getattr(user_attributes, 'choice_start_idx', 0)
    cont_reqs = getattr(user_attributes, 'cont_reqs', 0)
    cont_reqs = 0 if cont_reqs is None else cont_reqs

    if not is_apl_supported:
        return {"response": speak_output, "shouldEndSession": False}
    elif recipe_query_result and choice_start_idx < len(recipes) and choice_start_idx < 9 and cont_reqs <= 3:
        document_directive = get_recipe_query_document(recipes, query)
        scroll_command_directive = ImageListScrollToIndexDirective()

        if intent == 'MoreChoiceIntent':
            scroll_command_directive = scroll_command_directive.build_directive(choice_start_idx + 2)
        else:
            scroll_command_directive = scroll_command_directive.build_directive(choice_start_idx)

        if first_visit or intent in ['CancelIntent', 'GoBackIntent', 'NaviPreviousIntent']:
            set_query_user_attributes(recipe_query_result, user_attributes)
            return {"response": speak_output, "directives": [document_directive, scroll_command_directive], "shouldEndSession": False}
        else:
            return {"response": speak_output, "directives": [scroll_command_directive], "shouldEndSession": False}
    else:
        return {"response": speak_output, "shouldEndSession": False}


def get_recipe_query_speak_output(recipes, query, intent, current_state, user_attributes):
    """
    Gets the text to say, as well as whether to continue the interaction.

    Args:
        recipes : Recipe list
            A list of recipes retrieved from Whole Foods.
        search_query : str
            User text.
        taco_state : str
            Current state machine state.
        intent : str
            Classified intent.
        text : str
            Current user text.
        user_attribues :
            User attributes object.
    """
    num_results = len(recipes)
    cont_reqs = getattr(user_attributes, 'cont_reqs', 0)
    cont_reqs = 0 if cont_reqs is None else cont_reqs
    choice_start_idx = update_choice_idx(intent, user_attributes)

    current_recipes = get_current_choices(recipes, choice_start_idx)

    speak_output = ''

    # num_results should never be 0 now

    if choice_start_idx < num_results and choice_start_idx < 9 and cont_reqs <= 3:
        speak_output = select_recipe_template(query, current_recipes, num_results, choice_start_idx, current_state, user_attributes)
    else:
        setattr(user_attributes, 'cont_reqs', 0)
        speak_output = template_manager.nothing_better(recipe=True).substitute(recipe=examples.random_recipe())

    return speak_output


def select_recipe_template(query, recipes, num_results, choice_start_idx, current_state, user_attributes):
    is_rec = getattr(current_state, 'is_rec', False)
    satisfied_constraints = get_constraints(current_state)
    first_visit = getattr(user_attributes, 'first_visit', True)

    speak_output = (
        select_segment1(query, first_visit, is_rec, current_state, user_attributes.last_taco_state) + 
        (
            select_segment2_w_constraints(choice_start_idx, query, num_results, recipes, satisfied_constraints, current_state)
            if user_attributes.last_taco_state and 'TaskClarification' in user_attributes.last_taco_state
            else select_segment2(choice_start_idx, is_rec, num_results, recipes) 
        ) +
        add_inst(choice_start_idx, num_results, first_visit) +
        select_segment3(recipes, user_attributes)
        #select_followup_template(num_results, choice_start_idx, first_visit)
    )

    setattr(user_attributes, 'first_visit', False)
    return speak_output


def select_segment1(query, first_visit, is_rec, current_state, last_taco_state):
    search_timeout = getattr(current_state, 'search_timeout', False)
    no_result = getattr(current_state, 'no_result', False)
    cat = getattr(current_state, 'recipe_rec_cat', '')

    speak_output = ''
    if first_visit:
        if is_rec:
            if search_timeout:
                speak_output = template_manager.search_timeout(recipe=True).substitute(query=query)
            elif no_result:
                speak_output = template_manager.no_results(recipe=True).substitute(query=query)
            else:
                speak_output = template_manager.first_visit_recommend(recipe=True).substitute(cat=cat)
        elif last_taco_state and 'TaskClarification' not in last_taco_state:
                speak_output = template_manager.help_with_query(recipe=True, has_query=bool(query)).substitute(query=query)

    return speak_output


def select_segment2(choice_start_idx, is_rec, num_results, recipes):
    speak_output = ''

    if choice_start_idx == 0:
        if is_rec:
            speak_output = template_manager.option_intro(recipe=True).substitute()
        elif num_results == 1:
            speak_output = "I found only one recipe in Whole Foods. "
        elif num_results == 2:
            speak_output = 'I only found two recipes in Whole Foods. '
            if recipes[0].name == recipes[1].name:
                speak_output += f'They are both called {recipes[0].name}. '
        else:
            speak_output = 'I found several recipes in Whole Foods. '
            if recipes[0].name == recipes[1].name and recipes[0].name == recipes[2].name:
                speak_output += f'They are all called {recipes[0].name}. '
    else:
        if num_results - choice_start_idx == 1:
            speak_output = "Here is the only recipe left. "
        elif num_results - choice_start_idx == 2:
            speak_output = 'Here are the remaining two recipes. '
            if recipes[0].name == recipes[1].name:
                speak_output += f'They are both called {recipes[0].name}. '
        else:
            speak_output = 'Here are the next three recipes. '
            if recipes[0].name == recipes[1].name and recipes[0].name == recipes[2].name:
                speak_output += f'They are all called {recipes[0].name}. '
    
    return speak_output


def select_segment2_w_constraints(choice_start_idx, query, num_results, recipes, satisfied_constraints, current_state):
    text = getattr(current_state, 'text', '')
    intent = getattr(current_state, 'final_intent', '')
    clarify = getattr(current_state, 'clarify', False)
    speak_output = ''

    if satisfied_constraints is None or not clarify:
        if intent == 'ClarifyIntent':
            speak_output = f"You said {text}, but I can't understand that as a diet constraint. "
        elif not clarify and satisfied_constraints:
            attr_str = get_and_list_prompt(satisfied_constraints)
            speak_output = f'Unfortunately, I can\'t find anything {attr_str}. '

        if choice_start_idx == 0:
            if num_results == 1:
                speak_output += f"Here is only one {query} recipe in Whole Foods. "
            elif num_results == 2:
                speak_output += f'Here are the only two {query} recipes in Whole Foods. '
                if recipes[0].name == recipes[1].name:
                    speak_output += f'They are both called {recipes[0].name}. '
            else:
                speak_output += f'Here are the top {query} recipes in Whole Foods. '
                if recipes[0].name == recipes[1].name and recipes[0].name == recipes[2].name:
                    speak_output += f'They are all called {recipes[0].name}. '
    else:
        attr_str = get_and_list_prompt(satisfied_constraints)

        if choice_start_idx == 0:
            if num_results == 1:
                speak_output = f"I found only one {query} recipe that is {attr_str} in Whole Foods. "
            elif num_results == 2:
                speak_output = f'I only found two {query} recipes that are {attr_str} in Whole Foods. '
                if recipes[0].name == recipes[1].name:
                    speak_output += f'They are both called {recipes[0].name}. '
            else:
                speak_output = f'I found several {query} recipes that are {attr_str} in Whole Foods. '
                if recipes[0].name == recipes[1].name and recipes[0].name == recipes[2].name:
                    speak_output += f'They are all called {recipes[0].name}. '
    
    return speak_output


def add_inst(choice_start_idx, num_results, first_visit):
    speak_output = ''

    if first_visit:
        if num_results - choice_start_idx >= 3:
            speak_output += 'You can ask me to compare them or tell you more options. '
        elif num_results - choice_start_idx > 1:
            speak_output += 'You can ask me to compare them. '
    
    if num_results - choice_start_idx > 1:
        speak_output += 'Which recipe do you want: '

    return speak_output


def select_segment3(recipes, user_attributes):
    proposed_tasks = None

    if len(recipes) == 1:
        proposed_tasks = [
            {"title" : recipes[0].name}
        ]
        speak_output = f'Do you want this recipe, {recipes[0].title}? '
        # setattr(user_attributes, 'list_item_rec', 0)
        user_attributes.list_item_rec = getattr(user_attributes, 'choice_start_idx', 0)
    else:
        speak_output, proposed_tasks = disambiguate_recipes(recipes)
        user_attributes.list_item_rec = -1

    if proposed_tasks:
        user_attributes.proposed_tasks = proposed_tasks
                        
    return speak_output


def disambiguate_recipes(recipes):
    if len(recipes) == 2:
        proposed_tasks = [
            {"title": recipes[0].name},
            {"title": recipes[1].name},
        ]

        return recipe_helpers.disambiguate_two_recipes(recipes[0], recipes[1]), proposed_tasks
    elif len(recipes) == 3:
        proposed_tasks = [
            {"title": recipes[0].name},
            {"title": recipes[1].name},
            {"title": recipes[2].name},
        ]

        return recipe_helpers.disambiguate_three_recipes(recipes[0], recipes[1], recipes[2]), proposed_tasks
    else:
        return '', None


def get_recipe_query_document(recipes, query):
    title = f'Whole Foods Recipes for “{query}” (Alexa Prize)'
    if not query:
        title = "Recommended Recipes from Whole Foods (Alexa Prize)"

    list_items = [visuals.make_list_item(recipe) for recipe in recipes]

    return visuals.base({
        "backgroundImageSource": apl.Urls.launch_background_image,
        "defaultImageSource": apl.Urls.default_recipe_image,
        "headerTitle": title,
        "listItems": list_items,
    })
