import logging
from taco.core.regex.regex_template import RegexTemplate
from taco.response_generators.food.regex_templates import DoubtfulTemplate
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.core.entity_linker.entity_groups import EntityGroupsForExpectedType
from taco.core.util import infl

from ask_sdk_model.services.timer_management import *
from ask_sdk_model.services.service_exception import ServiceException

from taco.response_generators.taco_rp.timer.state import State, ConditionalState

logger = logging.getLogger('tacologger')


class taco_timer_Treelet(Treelet):
    name = "taco_timer_treelet"

    def classify_user_response(self):
        assert False, "This should never be called."


    def get_response(self, state_manager, timer_manager, priority=ResponsePriority.WEAK_CONTINUE, **kwargs) -> ResponseGeneratorResult:
        """ Returns the response. """
            
            
        state, utterance, response_types = self.get_state_utterance_response_types()
        
        text = state_manager.current_state.text
#         final_intent = state_manager.current_state.final_intent
        
#         if final_intent == 'TimerApprovedIntent':
#             return 'Please repeat the command to set a timer. Or, you can say next to continue your task. '
        
        text = 'set ' + text 
        
        speech_output = ''
        try:
            if 'set' in text:
                setattr(state_manager.user_attributes, 'is_displaying_details', True)
#                 slots = state_manager.current_state.slots
#                 duration = slots['duration']['value']
                duration = 30
                timer_response = self._send_create_timer_request(timer_manager, duration, "task bot")
                speech_output = f"{timer_response['timer_label']} timer is created"
                if getattr(state_manager.current_state, "nounphrases", None):
                    if state_manager.current_state.nounphrases.get("user_input_noun_phrases"):
                        # Simple heuristic: choose the last entity
                        speech_output = f"{timer_response['timer_label']} timer is created for {state_manager.current_state.nounphrases.get('user_input_noun_phrases')[-1]}"

            if "read all" in text:
                read_all_response = timer_manager.read_all_timers()
                speech_output = "Total timers read: {} ".format(read_all_response['total_count'])

            if "stop" in text:
                read_all_response = timer_manager.read_all_timers()
                timers = read_all_response['timers']
                timer_manager.pause_timer(timer_id=timers[0])
                speech_output = "Timer {} paused successfully ".format(timers[0])

            if "read" in text and "all" not in text:
                read_all_response = timer_manager.read_all_timers()
                timers = read_all_response['timers']
                read_response = self.read_timer(timer_id=timers[0])
                speech_output = "Timer {} read successful ".format(read_response['timer_label'])

            if "resume" in text:
                read_all_response = timer_manager.read_all_timers()
                timers = read_all_response['timers']
                timer_manager.resume_timer(timer_id=timers[0])
                speech_output = "Timer {} resumed successfully ".format(timers[0])

            if "cancel" in text:
                read_all_response = timer_manager.read_all_timers()
                timers = read_all_response['timers']
                timer_manager.cancel_timer(timer_id=timers[0])
                speech_output = "Timer {} cancelled ".format(timers[0])

            if "cancel all" in text:
                timer_manager.cancel_all_timers()
                speech_output = "All timers cancelled successfully "
        except ServiceException as se:
            if 'Unauthorized' in str(se):
                speak_output = (
                    "I need your permission to do this. " + 
                    "After this chat, you may turn it on in your Alexa app, settings, Alexa privacy, manage skill permissions. " + 
                    "If you are wondering what to say next, you may ask me, help. "
                )
                return ResponseGeneratorResult(text=speech_output, priority=priority,
                                       needs_prompt=False, state=state, cur_entity=None,
                                       conditional_state=ConditionalState(
                                           prompt_treelet=self.name,))
                #return self._add_voice_permissions()

        return ResponseGeneratorResult(text=speech_output, priority=priority,
                                       needs_prompt=False, state=state, cur_entity=None,
                                       conditional_state=ConditionalState(
                                           prompt_treelet=self.name,))
        
        
    def _send_create_timer_request(self, timer_manager, duration, timer_label) -> TimerResponse:
        """
        Creating timer request object -
        https://developer.amazon.com/en-US/docs/alexa/smapi/alexa-timers-api-reference.html

        :param duration: Duration for which timer is set
        :param timer_label: Timer name
        :return: TimerResponse
        """

        response = timer_manager.create_timer(duration, timer_label)
        return response

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
