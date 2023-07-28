from typing import Any, TypeVar, Type
import json
import decimal
from injector import singleton, inject
from taco_event import Event
from taco_flags import SIZE_THRESHOLD
from taco_util import print_dict_linebyline
import jsonpickle
import logging

logger = logging.getLogger('tacologger')

# https://stackoverflow.com/questions/44640479/mypy-annotation-for-classmethod-returning-instance
UserAttributesType = TypeVar('UserAttributesType', bound='UserAttributes')

@singleton
class UserAttributes(object):
    name = 'attributes'

    @inject(event=Event)
    def __init__(self, user_id='', map_attributes=None, event=None):
        # type: (str, dict, Event) -> None
        """
        Initialize a UserAttributes object with provided fields.
        :param user_id: user id
        :param map_attributes session attributes in dict
        """
        
        self.user_id = user_id
        if map_attributes is None:
            self.map_attributes = {}
        else:
            self.map_attributes = map_attributes
        if event is not None:
            self.user_id = event.user_id
            # Store conversation_id in map_attributes for LaunchRequest and IntentRequest
            self.conversationId = event.conversation_id

    def __setattr__(self, key: str, value: Any) -> None:
        """
        Allow quick update on the key-value pair in the UserAttributes object. i.e. attributes.mode = 'START_MODE'
        :param key: user_id or map_attributes or any attribute key to be saved in the map_attributes dict
        :param value: value
        :return: None
        """
        if key == 'user_id' or key == 'map_attributes' or key == '__injector__':
            self.__dict__[key] = value
        else:
            self.map_attributes[key] = value

    def __getattr__(self, key: str) -> Any:
        """
        Allow quick access on the value for the given key, which can be any key in the map_attributes dict
        :param key: any attribute key in the map_attributes dict
        :return: value associated with the key
        """
        if key != '__injector__':
            # TODO: This function is called when creating instance. Need to figure out why it's called.
            return self.map_attributes.get(key, None)

    def serialize_to_json(self) -> str:
        """
        Serialize UserAttributes object to a JSON string.
        :return: JSON serialized string
        """
        return json.dumps({
            'user_id': self.user_id,
            'map_attributes': self.map_attributes
        })

    def serialize(self):
        logger.debug(f'Running jsonpickle version {jsonpickle.__version__}')
        logger.debug(f'jsonpickle backend names: {jsonpickle.backend.json._backend_names}')
        logger.debug(f'jsonpickle encoder options: {jsonpickle.backend.json._encoder_options}')
        logger.debug(f'jsonpickle fallthrough: {jsonpickle.backend.json._fallthrough}')

        encoded_dict = {k: jsonpickle.encode(v) for k, v in self.__dict__.items()}
        total_size = sum(len(k) + len(v) for k, v in encoded_dict.items())

        if total_size > SIZE_THRESHOLD:
            logger.primary_info(
                f"Total encoded size of state is {total_size}, which is greater than allowed {SIZE_THRESHOLD}. \n"
                f"Size of each value in the dictionary is:\n{print_dict_linebyline({k: len(v) for k, v in encoded_dict.items()})}. \n")

            # Tries to reduce size of the current state
            self.prune_jsons()
            encoded_dict = {k: jsonpickle.encode(v) for k, v in self.__dict__.items()}
            total_size = sum(len(k) + len(v) for k, v in encoded_dict.items())
        logger.primary_info(
            f"Total encoded size of state is {total_size}\n"
            f"Size of each value in the dictionary is:\n{print_dict_linebyline({k: len(v) for k, v in encoded_dict.items()})}. \n")
        return encoded_dict

    @classmethod
    def deserialize(cls, mapping: dict):
        decoded_items = {}
        for k, v in mapping.items():
            try:
                decoded_items[k] = jsonpickle.decode(v)
            except:
                logger.error(f"Unable to decode {k}:{v} from past state")

        constructor_args = ['user_id']
        base_self = cls(**{k: decoded_items[k] for k in constructor_args})
        for k in decoded_items:
            if k not in constructor_args:
                setattr(base_self, k, decoded_items[k])
        return base_self

    @classmethod
    def deserialize_from_json(cls, input: dict) -> UserAttributesType:
        """
        Deserialize a UserAttribute object from a JSON input in dict.
        :param json_str: JSON string contains State information
        :return: State object
        """
        json_str = json.dumps(input, cls=DecimalEncoder)
        json_dict = json.loads(json_str)
        return cls(**json_dict)

    def merge(self, other_instance: UserAttributesType) -> None:
        """
        Merge other instance of UserAttributes object to this UserAttributes object if the user id is the same.
        i.e. this_instance = {
                user_id: "user_id",
                map_attributes: {'key': 'value'}
            }

            other_instance = {
                user_id: "user_id",
                map_attributes: {'key2':'value2'}
            }

            after merge:
            this_instance = {
                user_id: "user_id",
                map_attributes: {
                    'key':'value',
                    'key2': 'value2'
                    }
            }
        :param other_instance: other instance of UserAttributes object
        :return: the merged UserAttributes
        """
        if self.user_id == other_instance.user_id:
            self.map_attributes.update(other_instance.map_attributes)

    def __str__(self):
        """
        Override the default string behavior
        :return: string representation
        """
        return json.dumps(self.__dict__)

    def __repr__(self):
        """
        Override the default string behavior
        :return: string representation
        """
        return self.__str__()

    def __eq__(self, other):
        """Override the default Equals behavior"""
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __ne__(self, other):
        """Define a non-equality test"""
        if isinstance(other, self.__class__):
            return not self.__eq__(other)
        return NotImplemented

    def __hash__(self):
        """Override the default hash behavior (that returns the id or the object)"""
        return hash(tuple(sorted(self.__dict__.items())))

class DecimalEncoder(json.JSONEncoder):
    
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)
