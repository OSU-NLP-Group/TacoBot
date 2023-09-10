from taco.response_generators.taco_rp.execution.treelets.utils import add_period
from taco.response_generators.taco_rp.preparation.treelets.utils import get_query_result_selected, should_include_headline
from taco.response_generators.taco_rp.preparation.treelets import visuals, template_manager
from taco.response_generators.taco_rp import apl, time_helpers, recipe_helpers, vocab


import random


tmp_pak = [["What is the 2 biggest fast food chain?", "List of the largest fast food restaurant chains Name 1 United States McDonald's 2 United States Subway 3 United States Starbucks 4 United States KFC 103 more rows "], ["What is Nashville chow chow?", "Their famous Tennessee Chow-Chow is a mixture of green tomatoes, cabbage, bell peppers, onions, spices and apple cider vinegar. The condiment \u2013 available in mild, hot and extra hot \u2013 is recommended for use on beans, tuna, hot dogs and bologna.May 21, 2013 "], ["Why is homemade food better?", "It's proven to be healthier "], ["Why is chow mein so different?", "Traditional lo mein recipes usually call for fresh (not dry) noodles that are thick and chewy. On the other hand, chow mein can be made with both fresh and dried noodles, but these noodles are much thinner which makes them great for stir-frying in a wok.Jun 13, 2022 "], ["What are the two types of chow mein?", "There are two main types of chow mein: steamed chow mein and crispy chow mein. To make steamed chow mein, chefs flash fry the egg noodles before tossing them with the rest of the ingredients and coating them in a light sauce. For crispy chow mein, chefs press the noodles flat while frying them. "], ["What is chow mein called in USA?", "The two may seem similar, but the ingredients, preparation, and origins are different. Chow mein is one of the signature dishes of Chinese cuisine while chop suey is an American creation using Chinese cooking techniques.Sep 13, 2022 "], ["Is chow mein just vegetables?", "Chow Mein is a Chinese dish of stir fried noodles with vegetables and sometimes shredded meat like chicken, beef, pork or seafood.Jun 21, 2022 "], ["What is the healthiest fast food place?", "10 Fast-Food Restaurants That Serve Healthy Foods Chipotle. Chipotle Mexican Grill is a restaurant chain that specializes in foods like tacos and burritos. ... Chick-fil-A. Chick-fil-A is a fast-food restaurant that specializes in chicken sandwiches. ... Wendy's. ... McDonald's. ... Ruby Tuesday. ... The Cheesecake Factory. ... KFC. ... Subway. \u2022May 3, 2019 "], ["What is in Chinese chow mein?", "What is Chow Mein made of? There are many variations of chow mein but this chow mein is made with noodles, cabbage, celery, green onions, and garlic. Chow Mein sauce is made with sesame oil, soy sauce, oyster sauce, ginger, brown sugar, and cornstarch.Jul 5, 2022 "], ["Why is chow mein so good?", "The sauce is what gives chow mein all of its seasoning and addictive flavors. It's a mix of oyster sauce, sweet soy sauce, toasted sesame oil and freshly ground black pepper. It's full of sweet and savory umami and seriously SO good.Apr 23, 2022 "], ["What is the most popular food fast food?", "McDonald's The Most Popular Fast Food Companies Rank Company Category #1 McDonald's Burger #2 Starbucks Snack #3 Chick-fil-A Chicken #4 Taco Bell Global 6 more rows\u2022Aug 31, 2022 "], ["What is the #1 fast food in the US?", "McDonald's McDonald's is by far the most popular fast food chain in the United States. It has about 13,500 locations in the U.S., 40,000 worldwide, and it operates in 118 countries.Oct 8, 2022 "], ["What are the first 10 fast food restaurants?", "10 Oldest Fast Food Chains in the World Burger King. Year Founded: 1953. ... Sonic. Year Founded: June 18, 1953. ... Jack in the Box. Year Founded: February 21, 1951. ... Dunkin' Donuts. Year Founded: 1948. ... In-N-Out Burger. Year Founded: October 22, 1948. ... Dairy Queen. Year Founded: June 22, 1940. ... McDonald's. Year Founded: May 15, 1940. ... KFC.  "], ["What are the top 5 fast food restaurant chains?", "Ranking The Top 50 Fast-Food Chains in America rank company 2018 us systemwide sales millions 1 McDonald's 38,524.05 2 Starbucks* 19,700.00 3 Subway* 10,410.34 4 Taco Bell 10,300.00 46 more rows "], ["What is Chicago style chow mein?", "CHICAGO CHOW MEIN: Slices of vegetables in a dark sauce with mushrooms, water chestnuts, and pea pods. A la carte. "], ["Why is it called chow mein?", "The term 'chow mein' means 'stir-fried noodles', also loosely translating to \"fried noodles\" in English, chow (Chinese: \u7092; pinyin: ch\u01ceo) meaning 'stir-fried' (or \"saut\u00e9ed\") and mein (simplified Chinese: \u9762; traditional Chinese: \u9eb5; pinyin: Mi\u00e0n) meaning 'noodles'. "], ["What is Full Moon chow chow?", "1. A spicy sweet relish that is staple in Southern kitchens. 2. A fabulous, crunchy zing of extra special flavor for chicken, pork, beef, fish, black-eyed peas, sandwiches, and more. Organic. "], ["Are lo mein noodles healthy?", "Worst: Lo Mein  The noodles are made from white flour, which raises your blood sugar faster than fiber-rich whole grains. Plus, they're cooked with oil and soy sauce, so you get extra fat and sodium.Mar 6, 2022 "], ["What is New York style chow mein?", "In New York, if you order it from a Chinese takeout restaurant, you'll get vegetables cooked in white sauce (with a protein of your choice) served with white rice. You'd probably find a small bag of crackers in the delivery bag.May 30, 2021 "], ["What's the healthiest fast food?", "10 Healthiest Fast-Food Menu Items Arby's Roast Chicken Entr\u00e9e Salad. ... Panera's Napa Almond Chicken Salad on Country Rustic Sourdough. ... Chick-Fil-A's Grilled Chicken Sandwich. ... Starbuck's Tomato and Mozzarella Panini. ... Dunkin's Veggie Egg White Omelet. ... Wendy's Sour Cream and Chive Baked Potato. Dec 28, 2021 "]]

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
    intent = current_state.parsed_intent

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

    # print('proposed_tasks = ', user_attributes.proposed_tasks)
    # print('recipes 1 = ', repr(recipes[0])[:200])
    # print('recipes 2 = ', repr(recipes[1])[:200])
    # print('recipes 3 = ', repr(recipes[2])[:200])

    if list_item_selected >= 0 and list_item_selected < len(recipes):
        recipe = recipes[list_item_selected]
        set_recipe_prep_user_attr(user_attributes, recipe, docparse)

        PAKS_lt = [item['PAKs'] for item in recipe_query_result["documents"]]
        PAKS = PAKS_lt[list_item_selected]
        if len(PAKS) == 0:
            PAKS = tmp_pak
        setattr(user_attributes, 'people_also_ask_question', PAKS)
        
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
    '''
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
    '''
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
