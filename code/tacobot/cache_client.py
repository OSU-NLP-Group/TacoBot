from typing import List

from tacobot.state import State
from tacobot.user_attributes import UserAttributes
import json
import redis
from injector import inject
from tacobot.utils import deserialize_from_json

class Cache:
    def __init__(self, host="127.0.0.1", port=6339):
        self.cache = redis.StrictRedis(host=host, port=port, charset="utf-8", decode_responses=True)

    def cache_state(self, state: State):
        session_id = state.session_id

        num_cached_sessions = self.cache.get('num_sessions')
        if num_cached_sessions:
            num_cached_sessions = int(num_cached_sessions)
        else:
            num_cached_sessions = 0

        cached_state_item = self.cache.get(str(session_id))

        if cached_state_item:
            cached_state_dict = cached_state_item.__dict__
            cached_state_dict[num_cached_sessions + 1] = state.__dict__
            self.cache.set(str(session_id), json.dumps(cached_state_item))
            self.cache.incr('num_cached_sessions')

    def retrieve_state(self, user_id: str, conversation_id: str, session_id: str) -> List[State]:
        cached_state_item = self.cache.get(str(session_id))

        if cached_state_item is None:
            return []

        cached_state_dict = cached_state_item.__dict__
        cached_states = []
        for session_count, cached_state in cached_state_dict.items():
            retrieved_state = State(user_id, conversation_id, session_id)

            for k, v in cached_state.items():
                setattr(retrieved_state, k, v)

            cached_states.append(retrieved_state)

        return cached_states
