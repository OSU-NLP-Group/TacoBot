import logging
from taco.core.regex.regex_template import RegexTemplate
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.core.entity_linker.entity_groups import EntityGroupsForExpectedType
from taco.core.util import infl

import re
import json
# from taco.response_generators.ingredient_qa.treelets.taco_intent_by_rule import TacoIntentByRule
# from taco.response_generators.taco_rp.ingredient_qa.state import State, ConditionalState

from taco.response_generators.taco_rp.ingredient_qa.state import State, ConditionalState
from taco.response_generators.taco_rp.ingredient_qa.treelets.taco_intent_by_rule import TacoIntentByRule

data_path = "/users/PAA0201/johnnyjana730/github/tacocardinal/taco/response_generators/taco_rp/ingredient_qa/data"

with open(data_path + "/all_ingredients.json", "r") as f:
    ALL_INGREDIENTS = json.load(f)

with open(data_path + "/ingredients_match_table_after_merge_w_auxiliary_search_deduplicate.json", "r") as f:
    SUBSTITUTION_DB = json.load(f)

REPLACE_INGREDIENTS1 = r'[ \w]*(which ingredient)?[ \w]*(use as)?[ \w]*(alternative[s]?|substitute[s]?|substitution[s]?|replacement|replace|other ingredient[s]?|instead)[ \w]*(for|of|with)?[ \w]*'
REPLACE_INGREDIENTS2 = r'[ \w]*(don\'t have|have no|do not have)[ \w]*'
REPLACE_INGREDIENTS3 = r'[ \w]*(necessary for )(the )?(dish|meal)[ \w]*'
REPLACE_INGREDIENTS4 = r'[ \w]*(similar recipe without)[ \w]*'

logger = logging.getLogger('tacologger')
	
def match_w_all_ingredients(text, ingredient_corpus):
    """
        Check if text is a substitional question. 

        Args: 
            text: (str) input user utterance.
            ingredient_corpus: (dict) data imported from "all_ingredients.json"
        
        Returns:
            longest_match: longest food name in the match_list or None
            match_list: detected food name in user utterance (by matching predefined ingredient list) or return an empty list
        """
    match_list = []
    print('[sub QA] text: ', text)
    for word in ingredient_corpus:  
        if word in text:
            match_list.append(word)
    print('[sub QA] matched list: ', match_list)
    # print(match_list)
    longest_match = None
    if len(match_list) > 0:
        longest_match = max(match_list, key = len, default = 'None')
    
    print('[sub QA] matched food: ', longest_match)
    return longest_match, match_list
	
def substitution_search(food):
    """
        Check if the longest detected food name has a substitution in the substitutional ingredient corpus, 
        by first match the key "ingredient_category". If not match, then try to match the key "auxiliary_search".
        Otherwise, returned count equals to 0 and response_info_list is [].

        Args: 
        
        Returns:
            count: returns varient size for food. Eg.chocolate has 3 varients: semisweet, unsweeted, chips semisweet 
            response_info_list: substitional list contained all raw information for this food
            exact_match: True or False will decide bot response (exact or related/possible substitutions)
        """
    response_info_list = []
    count = 0
    exact_match = False
    for substitute_food in SUBSTITUTION_DB:
        if substitute_food["ingredient_category"] == food:
            count += 1
            response_info_list.append(substitute_food)
            exact_match = True
    if count == 0:
        for substitute_food in SUBSTITUTION_DB:
            if isinstance(substitute_food["auxiliary_search"], list):
                if food in substitute_food["auxiliary_search"]:
                    count += 1
                    response_info_list.append(substitute_food)
            else:
                if substitute_food["auxiliary_search"] == food:
                    count += 1
                    response_info_list.append(substitute_food)
    return count, response_info_list, exact_match

def get_substitution_info(text, all_ingredients):
    """
        If the longest detected food name has no substitutions in the substitutional ingredient corpus, 
        search again for the second longest detected food name in the match_list. 
        For example, "plain yogurt", the match_list is ["yogurt", "plain yogurt"]. If no match for "plain yogurt",
        will search again for "yogurt".
        
        Args: 
            text: (str) input user utterance.
            ingredient_corpus: (dict) data imported from "all_ingredients.json"   
        Returns:
            response_info_list: substitional list contained all raw information for this food
                                or []
            exact_match: True or False will decide bot response (exact or related/possible substitutions)
        """
    matched_ingredient, match_list = match_w_all_ingredients(text, all_ingredients)
    # print("match_list:", match_list, "isMatchTemplates:", isMatch)
    original_match_list = match_list.copy()
    if matched_ingredient is not None:
        count, response_info_list, exact_match = substitution_search(matched_ingredient)
        if count == 0 and matched_ingredient is not None and len(match_list) > 0:
            # longest match fail, fallback to second longest match (if any)
            match_list.remove(matched_ingredient)
            if len(match_list) > 0:
                count, response_info_list, exact_match = substitution_search(max(match_list, key = len, default = "None"))
        # print(count)
        return response_info_list, exact_match, original_match_list
    else:
        return None, None, original_match_list  ##"templates are not been recognized as substitute question"


def compose_string(sub):
    result = ''
    if sub['ingredient_property']:
        result += sub['ingredient_property'] + ' '

    result += (sub['ingredient_category'] +  " with " + sub['amount_substitution'][1])
    return result

    
class IngredientSubstituteTreelet(Treelet):
    name = "ingredient_Substitute_treelet"

    def classify_user_response(self):
        assert False, "This should never be called."


    def get_response(self, state_manager, priority=ResponsePriority.WEAK_CONTINUE, **kwargs) -> ResponseGeneratorResult:
           
        """ Returns the response. """
        state, text, response_types = self.get_state_utterance_response_types()
        
        recipe_query_result = state_manager.user_attributes.query_result
        list_item_selected = state_manager.user_attributes.list_item_selected
        is_wikihow = state_manager.user_attributes.is_wikihow
        
        speak_out = ''
        matched_ingredients_root = []
        if not is_wikihow:
            
            ingredients = recipe_query_result['documents'][list_item_selected]['recipe']['ingredients']
            _, matched_ingredients_root = TacoIntentByRule.match_ingredients(text, ingredients, is_all=False)
            # we only consider one match here, for brevity
            ingredient_needed = False
            exact_match = False
            if len(matched_ingredients_root) > 0:
                response_info_list, exact_match, match_list = get_substitution_info(matched_ingredients_root[0], ALL_INGREDIENTS)
                ingredient_needed = True
            else:
                response_info_list, exact_match, match_list = get_substitution_info(text, ALL_INGREDIENTS)

            if response_info_list and len(response_info_list) > 0:
                substitute_str = '; '.join([compose_string(sub) for sub in response_info_list])
                if ingredient_needed:
                    if exact_match:
                        speak_out = f"we can substitute {substitute_str}. "
                    else:
                        speak_out = f"I can't find a good substitute for {matched_ingredients_root[0]}. But relatedly, we can substitute {substitute_str}. "
                else:
                    speak_out = f"We can substitute {substitute_str}. It's not needed in this recipe though."
            else:
                if ingredient_needed:
                    current_taco_state = getattr(self.state_manager.user_attributes, 'taco_state', None)
                    if current_taco_state and 'Execution' in current_taco_state:
                        speak_out = f"Unfortunately, I can't find a good substitute for {matched_ingredients_root[0]}. You can continue with other ingredients. After all, cooking is a science experiment! "
                    else:
                        speak_out = f"Unfortunately, I can't find a good substitute for {matched_ingredients_root[0]}. You can go back and choose another recipe, or continue with other ingredients. After all, cooking is a science experiment! "
                else:
                    speak_out = f"Oops, I can't find a good substitute. But luckily, we don't need it in this recipe. "
        
        return ResponseGeneratorResult(text=speak_output, priority=priority,
                                       needs_prompt=False, state=state, cur_entity=None,
                                       conditional_state=ConditionalState(
                                           prompt_treelet=self.name,))

    def get_best_candidate_user_entity(self, utterance, cur_food):
        def condition_fn(entity_linker_result, linked_span, entity):
            return EntityGroupsForExpectedType.food_related.matches(entity) and entity.name != cur_food
        entity = self.rg.state_manager.current_state.entity_linker.top_ent(condition_fn) or self.rg.state_manager.current_state.entity_linker.top_ent()
        if entity is not None:
            user_answer = entity.talkable_name
            plural = entity.is_plural
        else:
            nouns = self.rg.state_manager.current_state.corenlp['nouns']
            if len(nouns):
                user_answer = nouns[-1]
                plural = True
            else:
                user_answer = utterance.replace('i like', '').replace('my favorite', '').replace('i love', '')
                plural = True

        return user_answer, plural
