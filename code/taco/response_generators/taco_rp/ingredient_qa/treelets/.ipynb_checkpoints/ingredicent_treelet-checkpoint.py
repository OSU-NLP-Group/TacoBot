import logging
from taco.core.regex.regex_template import RegexTemplate
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.core.entity_linker.entity_groups import EntityGroupsForExpectedType
from taco.core.util import infl

from taco.response_generators.taco_rp.ingredient_qa.state import State, ConditionalState

logger = logging.getLogger('tacologger')


def add_period(x):
    x = x.rstrip()
    return (x + ' ') if x[-1] == '.' else (x + '. ')


def get_and_list_prompt(items:list):
    '''
    Convert a list of strs to a English str.
    !!! The returned string does not have punctuation or trailing white spaces. 
    '''
    if len(items) == 0:
        return ''
    if len(items) == 1:
        return items[0]
    else:
        return ', '.join(items[:-1]) + ' and ' + items[-1]

class IngredientTreelet(Treelet):
    name = "ingredient_type_treelet"

    def classify_user_response(self):
        assert False, "This should never be called."


    def get_response(self, state_manager, priority=ResponsePriority.WEAK_CONTINUE, **kwargs) -> ResponseGeneratorResult:
        """ Returns the response. """
        state, utterance, response_types = self.get_state_utterance_response_types()
        user_utterance = state_manager.current_state.text
        cur_entity = state_manager.current_state.entity_tracker.cur_entity
        
        recipe_query_result = state_manager.user_attributes.query_result
        list_item_selected = state_manager.user_attributes.list_item_selected
        is_wikihow = state_manager.user_attributes.is_wikihow
        
        matched_ingredients = recipe_query_result['documents'][list_item_selected]['recipe']['ingredients']
        print('[ingredients list] matched:', matched_ingredients)
        matched_ingredients =   get_and_list_prompt(matched_ingredients).replace('.0', '')
        speak_output = add_period(f'We need: {matched_ingredients}. ')
        

        return ResponseGeneratorResult(text=speak_output, priority=priority,
                                       needs_prompt=False, state=state,
                                       cur_entity=cur_entity,
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
