import logging
import json
import random

from taco.core.regex.regex_template import RegexTemplate
from taco.response_generators.food.regex_templates import DoubtfulTemplate
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.core.entity_linker.entity_groups import EntityGroupsForExpectedType
from taco.core.util import infl

# from cobot_core.service_module import LocalServiceModule

from taco.response_generators.taco_rp.welcome.treelets import template_manager
from taco.response_generators.taco_rp import apl

from taco.response_generators.taco_rp.welcome.state import State, ConditionalState

logger = logging.getLogger('tacologger')


def restart(user_attributes):
    setattr(user_attributes, 'current_step_details', None)
    setattr(user_attributes, 'query', '')
    setattr(user_attributes, 'query_result', None)
    setattr(user_attributes, 'use_evi', False)
    setattr(user_attributes, 'choice_start_idx', 0)
    setattr(user_attributes, 'cont_reqs', 0)
    setattr(user_attributes, 'current_task', None)
    setattr(user_attributes, 'list_item_selected', -1)
    setattr(user_attributes, 'list_item_rec', -1)
    setattr(user_attributes, 'current_step', None)
    setattr(user_attributes, 'started_cooking', None)
    setattr(user_attributes, 'task_started', False)
    setattr(user_attributes, 'wikihow_summary', '')


HINTS = [
    "Mexican recipes",
    "Chinese recipes",
    "Indian recipes",
    "Italian recipes",
    "gluten-free chicken recipes",
    "low-carb recipes",
    "vegetarian pizza recipes",
    "how to wallpaper a room",
    "how to grow plants faster",
    "how to build a model ship",
]


def build_directive(task, task_img_url, recipe, recipe_img_url):
    """
    Returns an APL directives as a dictionary.

    Arguments: 
    task (string) an example task.
    task_url (string) image for the task.
    recipe (string) an example recipe.
    recipe_url (string) image for the recipe.
    """

    hint_choice = random.choice(HINTS)
    hint_text = f"Try “{hint_choice}”"

    return {
        "document": {
            "type": "APL",
            "version": "1.8",
            "import": [{"name": "alexa-layouts", "version": "1.3.0"}],
            "settings": {"idleTimeout": 60000},
            "mainTemplate": {
                "items": [
                    {
                        "type": "AlexaImageList",
                        "headerTitle": "Welcome! What would you like to do today? (Alexa Prize)",
                        "backgroundImageSource": apl.Urls.launch_background_image,
                        "defaultImageSource": apl.Urls.default_task_image,
                        "headerAttributionPrimacy": False,
                        "headerBackButton": False,
                        "headerDivider": False,
                        "hideOrdinal": True,
                        "backgroundBlur": False,
                        "backgroundOverlayGradient": True,
                        "backgroundColorOverlay": True,
                        "imageAspectRatio": "square",
                        "imageScale": "best-fill",
                        "imageRoundedCorner": True,
                        "listImagePrimacy": True,

                        "listItems": [
                            {
                                "primaryText": "DIY at Home",
                                "secondaryText": task,
                                "imageSource": task_img_url,
                            },
                            {
                                "primaryText": "Cooking",
                                "secondaryText": recipe,
                                "imageSource": recipe_img_url,
                            },
                            {
                                "primaryText": "Favorites",
                                "secondaryText": "My Recommendations",
                                "imageSource": apl.Urls.favorites_task_image,
                            },
                        ],
                        "imageBlurredBackground": True,
                        "imageMetadataPrimacy": False,
                        "primaryAction": {
                            "type": "SendEvent",
                            "arguments": ["ListItemSelected", "${ordinal}"],
                        },

                        "hintText": hint_text,
                    }
                ],
            },
        },
        "type": "Alexa.Presentation.APL.RenderDocument",
        "token": "ImageListDocumentToken",
        "datasources": {},
    }


class WELCOME_Treelet(Treelet):

    def __init__(self, rg):
        super().__init__(rg)
        self.name = 'welcome_Treelet'
        
        self.continue_intents = ['LaunchRequestIntent']
        self.restart_intents = ['AcknowledgeIntent', 'NegativeAcknowledgeIntent', 'CancelIntent', 'GoBackIntent']
        self.cache = json.load(open('./taco/response_generators/taco_rp/welcome/data/example_cache.json'))   
        self.can_prompt = False    
#         taco.response_generators
#         taco.response_generators.taco_rp.welcome

    def classify_user_response(self):
        assert False, "This should never be called."


    def get_response(self, state_manager, priority=ResponsePriority.WEAK_CONTINUE, **kwargs) -> ResponseGeneratorResult:
        """ Returns the response. """
        state, utterance, response_types = self.get_state_utterance_response_types()
        intent = "LaunchRequestIntent"

        speak_out = None
        task = None
        recipe = None
        
        print('state = ', state)

        if intent in self.continue_intents:
            restart(state_manager.user_attributes)
            speak_out, task, recipe = template_manager.select_template()
        elif intent in self.restart_intents:
            restart(state_manager.user_attributes)
            speak_out, task, recipe = template_manager.select_template(revisited=True)
        else:
            self.logger.warning("Intent was not valid. [intent: %s]", intent)
            return ''
        
#         is_apl_supported = state_manager.current_state.supported_interfaces.get('apl', False)
#         if not is_apl_supported:
#             return ResponseGeneratorResult(text=speak_output, priority=priority,
#                                            needs_prompt=False, state=state,
#                                            conditional_state=ConditionalState(
#                                                prompt_treelet=self.name,))

#         else:

        task_img_url = self._get_cached_url(task=task)
        recipe_img_url = self._get_cached_url(recipe=recipe)
        directives = [build_directive(task, task_img_url, recipe, recipe_img_url)]

        setattr(state_manager.user_attributes, 'welcome_task', task.lower()) 
        setattr(state_manager.user_attributes, 'welcome_recipe', recipe.lower()) 


        return ResponseGeneratorResult(text=speak_out, priority=priority,
                                       needs_prompt=False, state=state, cur_entity=None,
                                       conditional_state=ConditionalState(
                                           prompt_treelet=self.name,))


    def _get_cached_url(self, *, task=None, recipe=None):
        if task is not None:
            key = task
            cache = self.cache['welcome_tasks']
        elif recipe is not None:
            key = recipe
            cache = self.cache['welcome_recipes']
        else:
            self.logger.warning("Didn't request a task or a recipe.")
            return apl.Urls.default_task_image

        if key not in cache:
            self.logger.warning(
                "Key not in image cache. [key: '%s', cache: '%s']",
                key,
                ", ".join(cache.keys()),
            )
            return apl.Urls.default_task_image

        return cache[key]
    
    

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
