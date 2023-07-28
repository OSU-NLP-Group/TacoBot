from enum import Enum
import logging
import datetime
from pprint import pprint
from tacobot.config import SIZE_THRESHOLD

import jsonpickle

jsonpickle.set_encoder_options('simplejson', sort_keys=True)
jsonpickle.set_encoder_options('json', sort_keys=True)

logger = logging.getLogger('tacologger')


class Transitions(Enum):
    NAVIGATE_NEXT_INTENT = 1
    NAVIGATE_PREVIOUS_INTENT = 2
    ACKNOWLEDGEMENT = 3
    DETAIL_REQUEST_INTENT = 4
    REVERSE_INTENT = 5


class State:
    def __init__(self, session_id: str, creation_date_time: str = None) -> None:
        self.session_id = session_id
        if creation_date_time is not None:
            self.creation_date_time = creation_date_time
        else:
            self.creation_date_time = str(datetime.utcnow().isoformat())

        self.history = []
        self.turn = 0
        self.turns_since_last_active = 0
        self.text = None
        self.cache = {}

    def update_from_last_state(self, last_state):
        self.history = last_state.history + [last_state.text, last_state.response]
        self.turn = last_state.turn + 1
        try:
            self.turns_since_last_active = last_state.turns_since_last_active
        except AttributeError:
            pass

    def get_cache(self, key):
        return self.cache.get(key)

    def set_cache(self, key, value):
        self.cache[key] = value

    @property
    def active_rg(self):
        """
        Returns the active RG.

        Returns:
            If two different RGs supplied the response and prompt, return the prompting RG.
            If a single RG supplied both response and prompt, return that RG.
            If neither is set, return None
        """
        try:
            last_active_rg = self.selected_prompt_rg or self.selected_response_rg
        except AttributeError:
            try:
                last_active_rg = self.selected_response_rg
            except AttributeError:
                return None
        return last_active_rg

    def serialize(self):
        logger.debug(f'Running jsonpickle version {jsonpickle.__version__}')
        logger.debug(f'jsonpickle backend names: {jsonpickle.backend.json._backend_names}')
        logger.debug(f'jsonpickle encoder options: {jsonpickle.backend.json._encoder_options}')
        logger.debug(f'jsonpickle fallthrough: {jsonpickle.backend.json._fallthrough}')

        # don't serialize cache
        encoded_dict = {k: jsonpickle.encode(v) for k, v in self.__dict__.items() if k != 'cache'}
        total_size = sum(len(k) + len(v) for k, v in encoded_dict.items())
        if total_size > SIZE_THRESHOLD:
            logger.info(
                f"Total encoded size of state is {total_size}, which is greater than allowed {SIZE_THRESHOLD}\n"
                f"Size of each value in the dictionary is:\n{pprint({k: len(v) for k, v in encoded_dict.items()})}")

            # Tries to reduce size of the current state
            self.reduce_size()
            encoded_dict = {k: jsonpickle.encode(v) for k, v in self.__dict__.items()}
            total_size = sum(len(k) + len(v) for k, v in encoded_dict.items())
        logger.info(
            f"Total encoded size of state is {total_size}\n"
            f"Size of each value in the dictionary is:\n{pprint({k: len(v) for k, v in encoded_dict.items()})}")
        return encoded_dict

    @classmethod
    def deserialize(cls, mapping: dict):
        decoded_items = {}
        # logger.debug(mapping.items())
        for k, v in mapping.items():
            try:
                decoded_items[k] = jsonpickle.decode(v)
            except:
                logger.error(f"Unable to decode {k}: {v} from past state")

        constructor_args = ['session_id', 'creation_date_time']
        base_self = cls(**{k: decoded_items.get(k, None) for k in constructor_args})

        for k in decoded_items:
            # if k not in constructor_args:
            setattr(base_self, k, decoded_items[k])
        return base_self


    def __str__(self):
        """
        Override the default string behavior
        :return: string representation
        """
        return str(self.serialize())

    def __repr__(self):
        """
        Override the default string behavior
        :return: string representation
        """
        return self.__str__()

    def reduce_size(self):
        """
        Attribute specific size reduction
        """
        purgable_attributes = ['entity_linker', 'entity_tracker', 'response_results', 'prompt_results']
        objs = []

        logger.info("Running reduce_size on the state object")
        # Collect all purgable objects from within lists and dicts
        for attr in purgable_attributes:
            try:
                attr = getattr(self, attr)
                if isinstance(attr, list):
                    objs += attr
                if isinstance(attr, dict):
                    objs += list(attr.values())
                else:
                    objs.append(attr)

            except AttributeError:
                logger.warning(f"State doesn't have purgable attribute {attr}")

        for obj in objs:
            if hasattr(obj, 'reduce_size'):
                # The max_size is supposed to be per item, but it is hard to set it from here
                # because of interactions with other items. So setting an arbitrary size of
                # SIZE_THRESHOLD/8
                old_size = len(jsonpickle.encode(obj))
                obj.reduce_size(SIZE_THRESHOLD / 8)
                logger.info(
                    f"object: {obj}'s encoded size reduced using reduce_size() from {old_size} to {len(jsonpickle.encode(obj))}")
            else:
                logger.warning(f'There is no reduce_size() fn for object={obj}')

        # The reduce_size function is supposed to be in place, and hence we don't need to
        # set to explicitly put the purged objects back into lists and dicts