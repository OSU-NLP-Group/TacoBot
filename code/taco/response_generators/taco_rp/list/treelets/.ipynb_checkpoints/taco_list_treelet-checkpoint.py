import logging
from taco.core.regex.regex_template import RegexTemplate
from taco.response_generators.food.regex_templates import DoubtfulTemplate
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.core.entity_linker.entity_groups import EntityGroupsForExpectedType
from taco.core.util import infl
# from cobot_core.service_module import ToolkitServiceModule
# from cobot_core.service_module import LocalServiceModule

from ask_sdk_model.services.service_exception import ServiceException
from cobot_core.alexa_list_management import AlexaListManagement
from taco.response_generators.taco_rp.taco_intent_by_rule import TacoIntentByRule

from taco.response_generators.taco_rp.choice.treelets.utils.general import get_and_list_prompt
# from taco.response_modules.choice.utils.general import get_and_list_prompt
import json

# treelets
from taco.response_generators.taco_rp.list.state import State, ConditionalState

import random

logger = logging.getLogger('tacologger')


class Taco_list_Treelet(Treelet):
    name = "Taco_list_Treelet"
    

    def classify_user_response(self):
        assert False, "This should never be called."


    def get_response(self, state_manager, priority=ResponsePriority.WEAK_CONTINUE, **kwargs) -> ResponseGeneratorResult:
        """ Returns the response. """
        state, utterance, response_types = self.get_state_utterance_response_types()
        
        text = state_manager.current_state.text

        recipe_query_result = state_manager.user_attributes.query_result
        list_item_selected = state_manager.user_attributes.list_item_selected
        
        recipe_query_result = state_manager.user_attributes.query_result
        
        ingredients = recipe_query_result['documents'][list_item_selected]['recipe']['ingredients']
        
#         ingredients = json.loads(recipe_query_result['documents'][list_item_selected])['recipe']['ingredients']
         
#         text += ' add all ingredient into list'
        
#         print('text = ', text)
#         print('ingredients = ', ingredients)
        
#         is_all, matched_ingredients, list_name = TacoIntentByRule.parse_list_intents(text, ingredients)
        is_all, matched_ingredients, list_name = True, ingredients, 'Alexa shopping list'
        print('[list]    is_all: ', is_all)
        print('[list]   matched:', matched_ingredients )
        print('[list] list name: ',  list_name)
        
        speak_output = "I need your permission to do this. " +  "After this chat, you may turn it on in your Alexa app, settings, Alexa privacy, manage skill permissions. " + "If you are wondering what to say next, you may ask me, help. "
#                 return {'response': speak_output, 'shouldEndSession': False}
        return ResponseGeneratorResult(text=speak_output, priority=priority,
                   needs_prompt=False, state=state, cur_entity=None,conditional_state=ConditionalState(prompt_treelet=self.name,))

        try:
            list_metadata = self.get_lists_metadata()
        except ServiceException as err:
            if str(err) == 'Forbidden' or True:
                speak_output = (
                    "I need your permission to do this. " + 
                    "After this chat, you may turn it on in your Alexa app, settings, Alexa privacy, manage skill permissions. " + 
                    "If you are wondering what to say next, you may ask me, help. "
                )
#                 return {'response': speak_output, 'shouldEndSession': False}
                return ResponseGeneratorResult(text=speak_output, priority=priority,
                           needs_prompt=False, state=state, cur_entity=None,conditional_state=ConditionalState(prompt_treelet=self.name,))
            raise

        list_exists = False
        speak_output = ''
        
        for shopping_list in list_metadata.to_dict()['lists']:
            if shopping_list['name'] == list_name and shopping_list['state'] == 'active':
                list_exists = True
        if not list_exists:
            self.create_list(list_name=list_name)

        for item in matched_ingredients:
                self.create_item_util(
                    list_name=list_name,
                    item_name=item
                )

        if list_name == 'Alexa shopping list':
            list_name = 'Alexa shopping'
        if is_all:
            speak_output = f"OK, I have added all the ingredients to your {list_name} list." 
        else:
            speak_output = f"OK, I have added {get_and_list_prompt(matched_ingredients)} to your {list_name} list."        
        

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

