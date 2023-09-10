import logging
from taco.core.regex.regex_template import RegexTemplate
from taco.response_generators.food.regex_templates import DoubtfulTemplate
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.core.entity_linker.entity_groups import EntityGroupsForExpectedType
from taco.core.util import infl
from taco.response_generators.taco_rp.taco_intent_by_rule import TacoIntentByRule
from taco.response_generators.taco_rp.choice.treelets.utils.general import get_and_list_prompt
import json

import random

from taco.response_generators.taco_rp.execution.treelets.taco_recipe_show_steps import taco_recipe_show_steps
from taco.response_generators.taco_rp.execution.treelets.taco_wikihow_details import taco_wikihow_details, taco_wikihow_tips
from taco.response_generators.taco_rp.execution.treelets.taco_wikihow_show_steps import taco_wikihow_show_steps
from taco.response_generators.taco_rp.execution.treelets.template_manager import DETAIL_TIP_TEMPLATES

from taco.core.state import State as Cur_State
from taco.core.user_attributes import UserAttributes as Cur_UserAttributes
from taco.response_generators.taco_rp.execution.state import *


tmp_pak = [["What is the 2 biggest fast food chain?", "List of the largest fast food restaurant chains Name 1 United States McDonald's 2 United States Subway 3 United States Starbucks 4 United States KFC 103 more rows "], ["What is Nashville chow chow?", "Their famous Tennessee Chow-Chow is a mixture of green tomatoes, cabbage, bell peppers, onions, spices and apple cider vinegar. The condiment \u2013 available in mild, hot and extra hot \u2013 is recommended for use on beans, tuna, hot dogs and bologna.May 21, 2013 "], ["Why is homemade food better?", "It's proven to be healthier "], ["Why is chow mein so different?", "Traditional lo mein recipes usually call for fresh (not dry) noodles that are thick and chewy. On the other hand, chow mein can be made with both fresh and dried noodles, but these noodles are much thinner which makes them great for stir-frying in a wok.Jun 13, 2022 "], ["What are the two types of chow mein?", "There are two main types of chow mein: steamed chow mein and crispy chow mein. To make steamed chow mein, chefs flash fry the egg noodles before tossing them with the rest of the ingredients and coating them in a light sauce. For crispy chow mein, chefs press the noodles flat while frying them. "], ["What is chow mein called in USA?", "The two may seem similar, but the ingredients, preparation, and origins are different. Chow mein is one of the signature dishes of Chinese cuisine while chop suey is an American creation using Chinese cooking techniques.Sep 13, 2022 "], ["Is chow mein just vegetables?", "Chow Mein is a Chinese dish of stir fried noodles with vegetables and sometimes shredded meat like chicken, beef, pork or seafood.Jun 21, 2022 "], ["What is the healthiest fast food place?", "10 Fast-Food Restaurants That Serve Healthy Foods Chipotle. Chipotle Mexican Grill is a restaurant chain that specializes in foods like tacos and burritos. ... Chick-fil-A. Chick-fil-A is a fast-food restaurant that specializes in chicken sandwiches. ... Wendy's. ... McDonald's. ... Ruby Tuesday. ... The Cheesecake Factory. ... KFC. ... Subway. \u2022May 3, 2019 "], ["What is in Chinese chow mein?", "What is Chow Mein made of? There are many variations of chow mein but this chow mein is made with noodles, cabbage, celery, green onions, and garlic. Chow Mein sauce is made with sesame oil, soy sauce, oyster sauce, ginger, brown sugar, and cornstarch.Jul 5, 2022 "], ["Why is chow mein so good?", "The sauce is what gives chow mein all of its seasoning and addictive flavors. It's a mix of oyster sauce, sweet soy sauce, toasted sesame oil and freshly ground black pepper. It's full of sweet and savory umami and seriously SO good.Apr 23, 2022 "], ["What is the most popular food fast food?", "McDonald's The Most Popular Fast Food Companies Rank Company Category #1 McDonald's Burger #2 Starbucks Snack #3 Chick-fil-A Chicken #4 Taco Bell Global 6 more rows\u2022Aug 31, 2022 "], ["What is the #1 fast food in the US?", "McDonald's McDonald's is by far the most popular fast food chain in the United States. It has about 13,500 locations in the U.S., 40,000 worldwide, and it operates in 118 countries.Oct 8, 2022 "], ["What are the first 10 fast food restaurants?", "10 Oldest Fast Food Chains in the World Burger King. Year Founded: 1953. ... Sonic. Year Founded: June 18, 1953. ... Jack in the Box. Year Founded: February 21, 1951. ... Dunkin' Donuts. Year Founded: 1948. ... In-N-Out Burger. Year Founded: October 22, 1948. ... Dairy Queen. Year Founded: June 22, 1940. ... McDonald's. Year Founded: May 15, 1940. ... KFC.  "], ["What are the top 5 fast food restaurant chains?", "Ranking The Top 50 Fast-Food Chains in America rank company 2018 us systemwide sales millions 1 McDonald's 38,524.05 2 Starbucks* 19,700.00 3 Subway* 10,410.34 4 Taco Bell 10,300.00 46 more rows "], ["What is Chicago style chow mein?", "CHICAGO CHOW MEIN: Slices of vegetables in a dark sauce with mushrooms, water chestnuts, and pea pods. A la carte. "], ["Why is it called chow mein?", "The term 'chow mein' means 'stir-fried noodles', also loosely translating to \"fried noodles\" in English, chow (Chinese: \u7092; pinyin: ch\u01ceo) meaning 'stir-fried' (or \"saut\u00e9ed\") and mein (simplified Chinese: \u9762; traditional Chinese: \u9eb5; pinyin: Mi\u00e0n) meaning 'noodles'. "], ["What is Full Moon chow chow?", "1. A spicy sweet relish that is staple in Southern kitchens. 2. A fabulous, crunchy zing of extra special flavor for chicken, pork, beef, fish, black-eyed peas, sandwiches, and more. Organic. "], ["Are lo mein noodles healthy?", "Worst: Lo Mein  The noodles are made from white flour, which raises your blood sugar faster than fiber-rich whole grains. Plus, they're cooked with oil and soy sauce, so you get extra fat and sodium.Mar 6, 2022 "], ["What is New York style chow mein?", "In New York, if you order it from a Chinese takeout restaurant, you'll get vegetables cooked in white sauce (with a protein of your choice) served with white rice. You'd probably find a small bag of crackers in the delivery bag.May 30, 2021 "], ["What's the healthiest fast food?", "10 Healthiest Fast-Food Menu Items Arby's Roast Chicken Entr\u00e9e Salad. ... Panera's Napa Almond Chicken Salad on Country Rustic Sourdough. ... Chick-Fil-A's Grilled Chicken Sandwich. ... Starbuck's Tomato and Mozzarella Panini. ... Dunkin's Veggie Egg White Omelet. ... Wendy's Sour Cream and Chive Baked Potato. Dec 28, 2021 "]]

starter_question_p1 = [
        "Incidentally, allow me to present a fascinating piece of information. Would you happen to be intrigued by the following inquiry? ",
        "Hey, I've got a fun fact for you! Are you interested in learning ",
        "I have an interesting piece of information for you. Would you be interested in knowing this question? ",
        "Allow me to present a noteworthy piece of information. May I inquire as to whether you would be interested in learning this question? "
        ]

starter_question_p2 = [
        "In the event that this topic fails to pique your interest, feel free to respond with next in order to proceed."
        "If not, no worries, just say next and we can move on.",
        "If not, please feel free to say next and we can proceed to next step.",
        "If this topic fails to capture your attention, please do not hesitate to say next and we can move on."
]


logger = logging.getLogger('tacologger')

class Taco_pak_Treelet(Treelet):
    name = "Taco_pak_prompt_Treelet"

    def classify_user_response(self): 
        assert False, "This should never be called."


    def get_prompt(self, state_manager, state, for_launch: bool = False) -> Optional[PromptResult]:
        """
        If this treelet has a starter question, returns a prompt asking the starter question.
        Otherwise, returns None.

        If for_launch, will give version of starter question that's appropriate for launch sequence.
        """
        # state, utterance, response_types = self.get_state_utterance_response_types()

        # people_also_a_q = state_manager.user_attributes.people_also_ask_question

        people_also_a_q = getattr(state_manager.user_attributes, 'people_also_ask_question', [])

        if len(people_also_a_q) == 0:
            people_also_a_q = tmp_pak.copy()

        random.shuffle(people_also_a_q)

        state_manager.user_attributes.PAK_selected_qus = people_also_a_q[-1][0] 
        state_manager.user_attributes.PAK_selected_ans = people_also_a_q[-1][-1] 

        # starter_question = 'By the way, show you a fun fact. Are you interested in this question? ' +  people_also_a_q[-1][0]
        
        # starter_question = starter_question + ' If you are not interested, you can say next to skip it :)'

        start_que_p1 = self.choose(starter_question_p1)
        start_que_p2 = self.choose(starter_question_p2)

        starter_question = start_que_p1 + people_also_a_q[-1][0] + " " + start_que_p2
        if len(state_manager.user_attributes.people_also_ask_question) > 1:
            state_manager.user_attributes.people_also_ask_question.pop()

        taco_state = getattr(state_manager.current_state, 'status', None)
        if 'Instruction' in taco_state:
            prompt_priority = PromptType.CURRENT_TOPIC
        else:
            prompt_priority = PromptType.NO

        # return PromptResult(text=starter_question, prompt_type=PromptType.FORCE_START)
        # n_current_state = Cur_State.deserialize(state_manager.current_state.serialize(logger_print=False))
        n_user_attributes = Cur_UserAttributes.deserialize(state_manager.user_attributes.serialize(logger_print=False))

        return PromptResult(text=starter_question,
                            prompt_type=prompt_priority, state=state, cur_entity=None,
                            conditional_state=ConditionalState(
                                   prev_treelet_str=self.name,
                                   used_people_also_ask=state.used_people_also_ask+1,
                                   n_user_attributes=n_user_attributes),
                            answer_type=AnswerType.ENDING)


    def treet_update_current_state(self, state_manager, conditional_state):
        assert state_manager is not None, "state_manager should not be None for updating the current state"
        assert conditional_state is not None, "conditional_state should not be None if the response/prompt was chosen"

        # user_attributes
        for k in ['people_also_ask_question']:
            v = getattr(conditional_state.n_user_attributes, k, None)
            if v != None:
                setattr(state_manager.user_attributes, k, v)

