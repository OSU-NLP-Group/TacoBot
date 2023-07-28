from typing import *
import json
from datetime import datetime
from functools import singledispatch
from taco_event import Event
from taco_flags import SIZE_THRESHOLD
from taco_util import print_dict_linebyline
import jsonpickle
import logging

logger = logging.getLogger('tacologger')


class State(object):
    """
    Encapsulates the current state of the system, as managed by the StateManager
    """

    def __init__(self, 
                #  user_id: str,
                #  conversation_id: str,
                #  is_experiment: bool,
                 session_id: str,
                #  app_id: str,
                #  ask_access_token: str,
                 resume_task: bool = False,
                 creation_date_time: str = None,
                 request_type: str = None,
                 intent: str = None,
                 slots: dict = None,
                 topic: str = None,
                 asr: List = None,
                 text: str = '',
                 response: dict = None,
                 mode: str = None,
                 sentiment_score: dict = {},
                 supported_interfaces: dict = None,
                 user_event: dict = None,
                 visible_components: dict = None,
                 features: dict={}) -> None:
        """
        Initialize a State object with provided fields.
        :param user_id: user id
        :param conversation_id: conversation id
        :param is_experiment: IsExperiment flag
        :param resume_task: resume task flag
        :param session_id: session id
        :param creation_date_time: state creation timestamp, default to None
        :param request_type: LaunchRequest, IntentRequest, or SessionEndedRequest, default to None
        :param intent: NLU intent, default to None
        :param topic: topic, default to None
        :param asr: request from ASK lambda function
        :param text: text extracted from highest confidence asr or raw TEXT slot
        :param response: generated response
        :param sentiment_score: sentimentScore, default to empty
        """
        # self.user_id = user_id
        # self.conversation_id = conversation_id
        # self.is_experiment = is_experiment
        self.resume_task = resume_task
        self.session_id = session_id
        # self.app_id = app_id
        # self.ask_access_token = ask_access_token
        if creation_date_time is not None:
            self.creation_date_time = creation_date_time
        else:
            self.creation_date_time = str(datetime.utcnow().isoformat())
        self.request_type = request_type
        self.intent = intent
        self.slots = slots
        self.topic = topic
        self.asr = asr
        self.text = text
        self.response = response
        self.sentiment_score = sentiment_score
        self.mode = mode
        self.supported_interfaces = supported_interfaces
        self.user_event = user_event
        self.visible_components = visible_components
        self.features = features

    def to_json(self) -> str:
        """
        Serialize State object to JSON string.
        :return: JSON serialized string
        """
        return json.dumps(self.__dict__, default=serialize_to_json)

    def serialize(self):
        logger.debug(f'Running jsonpickle version {jsonpickle.__version__}')
        logger.debug(f'jsonpickle backend names: {jsonpickle.backend.json._backend_names}')
        logger.debug(f'jsonpickle encoder options: {jsonpickle.backend.json._encoder_options}')
        logger.debug(f'jsonpickle fallthrough: {jsonpickle.backend.json._fallthrough}')

        # don't serialize cache
        encoded_dict = {k: jsonpickle.encode(v) for k, v in self.__dict__.items() if k != 'cache'}
        total_size = sum(len(k) + len(v) for k, v in encoded_dict.items())
        if total_size > SIZE_THRESHOLD:
            logger.primary_info(
                f"Total encoded size of state is {total_size}, which is greater than allowed {SIZE_THRESHOLD}\n"
                f"Size of each value in the dictionary is:\n{print_dict_linebyline({k: len(v) for k, v in encoded_dict.items()})}")

            # Tries to reduce size of the current state
            self.reduce_size()
            encoded_dict = {k: jsonpickle.encode(v) for k, v in self.__dict__.items()}
            total_size = sum(len(k) + len(v) for k, v in encoded_dict.items())
        logger.primary_info(
            f"Total encoded size of state is {total_size}\n"
            f"Size of each value in the dictionary is:\n{print_dict_linebyline({k: len(v) for k, v in encoded_dict.items()})}")
        return encoded_dict

    @classmethod
    def deserialize(cls, mapping: dict): # NEW
        decoded_items = {}
        # logger.debug(mapping.items())
        for k, v in mapping.items():
            try:
                decoded_items[k] = jsonpickle.decode(v)
            except:
                logger.error(f"Unable to decode {k}: {v} from past state")
        print('***cls: ', cls)
        print("***decoded_items: ", decoded_items)
        constructor_args = ['session_id', 'creation_date_time']
        base_self = cls(**{k: decoded_items.get(k, None) for k in constructor_args})

        for k in decoded_items:
            if k not in constructor_args:
                setattr(base_self, k, decoded_items[k])
        print("***base_self: ", base_self)
        return base_self

    @classmethod
    def from_ask_request(cls, event: Event) -> 'State':
        """
        Initialize a State object from ASK request.
        :param event: ASK event
        :return: State object
        """
        # If request type is LaunchRequest, set intent to LaunchRequestIntent
        request_type = event.get('request.type', None)
        if request_type == 'LaunchRequest':
            intent = 'LaunchRequestIntent'
        elif request_type == 'Alexa.Presentation.APL.UserEvent':
            intent = 'UserEvent'
        else:
            intent = event.get('request.intent.name', None)
        asr = event.speech_recognition
        slots = event.get('request.intent.slots', None)
        text = State.extract_text_from_event(event)
        user_event = State.extract_user_event_from_event(event)
        supported_interfaces = State.extract_supported_interfaces_from_event(event)
        visible_components = State.extract_visible_components(event)
        return State(user_id=event.user_id,
                     conversation_id=event.conversation_id,
                     is_experiment=event.is_experiment,
                     resume_task=event.resume_task,
                     session_id=event.get('session.sessionId', None),
                     app_id=event.app_id,
                     ask_access_token=event.ask_access_token,
                     request_type=request_type,
                     intent=intent,
                     slots=slots,
                     asr=asr,
                     text=text,
                     user_event=user_event,
                     supported_interfaces=supported_interfaces,
                     sentiment_score=event.sentiment_score,
                     visible_components=visible_components)

    @classmethod
    def extract_text_from_event(cls, event: Event):
        asr = event.speech_recognition
        n_best_asr_text = []
        for n_best in asr:
            tokens = n_best['tokens']
            text = ""
            for token in tokens:
                value = token['value']
                text = text + " " + value
            n_best_asr_text.append(text)
        # Rule 1: extract the 1st asr text
        if n_best_asr_text:
            return n_best_asr_text[0].strip()

        # Rule 2: extract raw text (AMAZON.LITERAL/AMAZON.RAW_TEXT) slot
        text = ''
        slots = event.get('request.intent.slots', None)
        if slots and type(slots) == dict:
            # TODO: delete, this is here to extract AMAZON.LITERAL/AMAZON.RAW_TEXT for greeter_bot and non_trivial_bot before AP team's skills are whitelisted for raw asr input.
            if 'text' in slots.keys() and 'value' in slots['text']:
                text = slots['text']['value']
            elif 'all_text' in slots.keys() and 'value' in slots['all_text']:
                text = slots['all_text']['value']
            elif 'topic' in slots.keys() and 'value' in slots['topic']:
                text = slots['topic']['value']
            elif 'question_text' in slots.keys() and 'question_word' in slots.keys():
                text = slots['question_word']['value'] + " " + slots['question_text']['value']

        return text

    @classmethod
    def extract_user_event_from_event(cls, event: Event) -> dict:
        """
        This method extracts user event when user clicks on component shown on the screen
        :param event:
        :return:
        """
        user_event = {"arguments": event.get("request.arguments", []),
                      "components": event.get("request.components", {}), "source": event.get("request.source", {}),
                      "token": event.get("request.token", '')}
        return user_event

    @classmethod
    def extract_supported_interfaces_from_event(cls, event: Event) -> dict:
        """
        This method will allow us to add more supported interfaces in the future.
        :param event:
        :return:
        """
        supported_interfaces_dict = dict()
        supported_interfaces = event.get('context.System.device.supportedInterfaces')
        if supported_interfaces and supported_interfaces.get('Alexa.Presentation.APL', ''):
            supported_interfaces_dict['apl'] = True
        return supported_interfaces_dict

    @classmethod
    def extract_visible_components(cls, event: Event) -> dict:
        """
        This method extracts visible components on screen from event.
        :param event:
        :return: main components visible on screen
        """
        visible_components_on_screen = dict()
        apl_visible_components_on_screen = event.get('context', {}).get('Alexa.Presentation.APL', {})
        if apl_visible_components_on_screen:
            cls._extract_list_components(apl_visible_components_on_screen, visible_components_on_screen)
        return visible_components_on_screen

    @staticmethod
    def _extract_list_components(ind: dict, outd: dict) -> None:
        """
        This method extracts out visible components on the screen.
        For example, user says select second item, this method will return list of items currently displayed on screen
        with ordinal and listIndex number.
        :param ind: dict containing APL context
        :param outd: dict containing most useful features from apl context extracted out.
        :return:
        """
        outd["apl"] = dict()
        outd["apl"]["token"] = ind.get("token", '')
        components = ind.get("componentsVisibleOnScreen", [])
        # Current assumption is there will only be one component
        # (list based or simple image + text based visible on screen)
        visible_component = components[0] if len(components) >= 1 else {}
        children = visible_component.get("children", [])
        main_child = dict()
        list_visible_on_screen_info = list()
        for item in children:
            if item.get("tags", {}).get("list", {}):
                main_child = item
                break
        list_shown_stats = main_child.get("tags", {}).get("list", {})
        items = main_child.get("children", [])
        for item in items:
            if item.get("tags", {}).get("ordinal", ''):
                list_visible_on_screen_info.append(item.get("tags"))

        if list_shown_stats and list_visible_on_screen_info:
            outd["apl"]["list"] = list_shown_stats
            outd["apl"]["displayed_items"] = list_visible_on_screen_info

    @classmethod
    def from_json(cls, json_str: str) -> 'State':
        """
        Initialize a State Object from JSON string.
        :param json_str: JSON string contains State information
        :return: State object
        """
        json_str = json_str.replace("'", "\"")
        json_dict = json.loads(json_str)
        return cls(**json_dict)

    def set_intent(self, intent: str) -> None:
        """
        Set Intent in the State object to the provided intent
        :param intent: NLU Intent value
        :return: None
        """
        self.intent = intent

    def set_topic(self, topic: str) -> None:
        """
        Set Topic value in the State object to the provided topic
        :param topic: Topic value
        :return: None
        """
        self.topic = topic

    def set_response(self, response: Any) -> None:
        """
        Set response in the State object to the provided response.
        :param response: ASK response
        :return: None
        """
        self.response = response

    def set_mode(self, mode: Any) -> None:
        """
        Set mode in the State object to the provided mode.
        :param mode: state mode, used for dialog manager
        :return: None
        """
        self.mode = mode

    def set_new_field(self, new_key: Any, new_value: Any) -> None:
        """
        set a new key-value pair to the State object.
        :param new_key: new key
        :param new_value: new value
        :return: None
        """
        setattr(self, new_key, new_value)

    def __str__(self):
        """
        Override the default string behavior
        :return: string representation
        """
        return self.to_json()

    def __repr__(self):
        """
        Override the default string behavior
        :return: string representation
        """
        return self.__str__()


@singledispatch
def serialize_to_json(val):
    return json.dumps(val.__dict__)
