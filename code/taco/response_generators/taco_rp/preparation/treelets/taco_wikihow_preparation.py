from taco.response_generators.taco_rp.execution.treelets.utils import add_period, method_part_pl_or_not
from taco.response_generators.taco_rp.preparation.treelets.template_manager import START_QUESTION, WIKIHOW_PREP_TEMPLATES
from taco.response_generators.taco_rp.preparation.treelets.utils import get_query_result_selected, should_include_headline
from taco.response_generators.taco_rp.preparation.treelets.visuals import get_wikihow_prep_visual
from taco.response_generators.taco_rp import wikihow_helpers, vocab


import random

tmp_pak = [["What is the 2 biggest fast food chain?", "List of the largest fast food restaurant chains Name 1 United States McDonald's 2 United States Subway 3 United States Starbucks 4 United States KFC 103 more rows "], ["What is Nashville chow chow?", "Their famous Tennessee Chow-Chow is a mixture of green tomatoes, cabbage, bell peppers, onions, spices and apple cider vinegar. The condiment \u2013 available in mild, hot and extra hot \u2013 is recommended for use on beans, tuna, hot dogs and bologna.May 21, 2013 "], ["Why is homemade food better?", "It's proven to be healthier "], ["Why is chow mein so different?", "Traditional lo mein recipes usually call for fresh (not dry) noodles that are thick and chewy. On the other hand, chow mein can be made with both fresh and dried noodles, but these noodles are much thinner which makes them great for stir-frying in a wok.Jun 13, 2022 "], ["What are the two types of chow mein?", "There are two main types of chow mein: steamed chow mein and crispy chow mein. To make steamed chow mein, chefs flash fry the egg noodles before tossing them with the rest of the ingredients and coating them in a light sauce. For crispy chow mein, chefs press the noodles flat while frying them. "], ["What is chow mein called in USA?", "The two may seem similar, but the ingredients, preparation, and origins are different. Chow mein is one of the signature dishes of Chinese cuisine while chop suey is an American creation using Chinese cooking techniques.Sep 13, 2022 "], ["Is chow mein just vegetables?", "Chow Mein is a Chinese dish of stir fried noodles with vegetables and sometimes shredded meat like chicken, beef, pork or seafood.Jun 21, 2022 "], ["What is the healthiest fast food place?", "10 Fast-Food Restaurants That Serve Healthy Foods Chipotle. Chipotle Mexican Grill is a restaurant chain that specializes in foods like tacos and burritos. ... Chick-fil-A. Chick-fil-A is a fast-food restaurant that specializes in chicken sandwiches. ... Wendy's. ... McDonald's. ... Ruby Tuesday. ... The Cheesecake Factory. ... KFC. ... Subway. \u2022May 3, 2019 "], ["What is in Chinese chow mein?", "What is Chow Mein made of? There are many variations of chow mein but this chow mein is made with noodles, cabbage, celery, green onions, and garlic. Chow Mein sauce is made with sesame oil, soy sauce, oyster sauce, ginger, brown sugar, and cornstarch.Jul 5, 2022 "], ["Why is chow mein so good?", "The sauce is what gives chow mein all of its seasoning and addictive flavors. It's a mix of oyster sauce, sweet soy sauce, toasted sesame oil and freshly ground black pepper. It's full of sweet and savory umami and seriously SO good.Apr 23, 2022 "], ["What is the most popular food fast food?", "McDonald's The Most Popular Fast Food Companies Rank Company Category #1 McDonald's Burger #2 Starbucks Snack #3 Chick-fil-A Chicken #4 Taco Bell Global 6 more rows\u2022Aug 31, 2022 "], ["What is the #1 fast food in the US?", "McDonald's McDonald's is by far the most popular fast food chain in the United States. It has about 13,500 locations in the U.S., 40,000 worldwide, and it operates in 118 countries.Oct 8, 2022 "], ["What are the first 10 fast food restaurants?", "10 Oldest Fast Food Chains in the World Burger King. Year Founded: 1953. ... Sonic. Year Founded: June 18, 1953. ... Jack in the Box. Year Founded: February 21, 1951. ... Dunkin' Donuts. Year Founded: 1948. ... In-N-Out Burger. Year Founded: October 22, 1948. ... Dairy Queen. Year Founded: June 22, 1940. ... McDonald's. Year Founded: May 15, 1940. ... KFC.  "], ["What are the top 5 fast food restaurant chains?", "Ranking The Top 50 Fast-Food Chains in America rank company 2018 us systemwide sales millions 1 McDonald's 38,524.05 2 Starbucks* 19,700.00 3 Subway* 10,410.34 4 Taco Bell 10,300.00 46 more rows "], ["What is Chicago style chow mein?", "CHICAGO CHOW MEIN: Slices of vegetables in a dark sauce with mushrooms, water chestnuts, and pea pods. A la carte. "], ["Why is it called chow mein?", "The term 'chow mein' means 'stir-fried noodles', also loosely translating to \"fried noodles\" in English, chow (Chinese: \u7092; pinyin: ch\u01ceo) meaning 'stir-fried' (or \"saut\u00e9ed\") and mein (simplified Chinese: \u9762; traditional Chinese: \u9eb5; pinyin: Mi\u00e0n) meaning 'noodles'. "], ["What is Full Moon chow chow?", "1. A spicy sweet relish that is staple in Southern kitchens. 2. A fabulous, crunchy zing of extra special flavor for chicken, pork, beef, fish, black-eyed peas, sandwiches, and more. Organic. "], ["Are lo mein noodles healthy?", "Worst: Lo Mein  The noodles are made from white flour, which raises your blood sugar faster than fiber-rich whole grains. Plus, they're cooked with oil and soy sauce, so you get extra fat and sodium.Mar 6, 2022 "], ["What is New York style chow mein?", "In New York, if you order it from a Chinese takeout restaurant, you'll get vegetables cooked in white sauce (with a protein of your choice) served with white rice. You'd probably find a small bag of crackers in the delivery bag.May 30, 2021 "], ["What's the healthiest fast food?", "10 Healthiest Fast-Food Menu Items Arby's Roast Chicken Entr\u00e9e Salad. ... Panera's Napa Almond Chicken Salad on Country Rustic Sourdough. ... Chick-Fil-A's Grilled Chicken Sandwich. ... Starbuck's Tomato and Mozzarella Panini. ... Dunkin's Veggie Egg White Omelet. ... Wendy's Sour Cream and Chive Baked Potato. Dec 28, 2021 "]]


def taco_wikihow_preparation(current_state, last_state, user_attributes):
    is_apl_supported = current_state.supported_interfaces.get('apl', False)
    query_result_selected = get_query_result_selected(
        is_apl_supported, 
        current_state, 
        last_state, 
        user_attributes
    )
    
    setattr(user_attributes, 'card_sent', False)
    intent = current_state.parsed_intent

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


        # PAKS = user_attributes.query_result[query_result_selected]['PAKs']
        PAKS = tmp_pak

        setattr(user_attributes, 'all_total_steps', wikihow_task.all_steps)
        setattr(user_attributes, 'has_parts', wikihow_task.has_parts)
        setattr(user_attributes, 'total_steps', wikihow_task.steps)
        setattr(user_attributes, 'current_task', wikihow_task.title)
        setattr(user_attributes, 'people_also_ask_question', PAKS)

        if len(wikihow_task.all_steps) > 1:
            setattr(user_attributes, 'current_step_speak', f"This task has {len(wikihow_task.all_steps)} {method_part_pl_or_not(wikihow_task.has_parts, len(wikihow_task.all_steps))}. The first {'part' if wikihow_task.has_parts else 'method'} has {wikihow_task.steps} steps. ")
        elif len(wikihow_task.all_steps) == 1:
            setattr(user_attributes, 'current_step_speak', f"This task has {wikihow_task.steps} {'steps' if wikihow_task.steps > 1 else 'step'}. ")
    else:
        detail_document = None
        speak_out = "Geez! I messed up something. Would you please say cancel and let's start over? "

    return speak_out, detail_document
