import logging
from tacobot.state import State
from tacobot.user_attributes import UserAttributes
from tacobot.log.logger import setup_logger, LoggerSettings

logger = logging.getLogger('tacologger')
from injector import inject, singleton


class StateManager:
    def __init__(self, current_state: State = None, last_state: State = None, user_attributes: UserAttributes = None):
        self.current_state = current_state
        self.last_state = last_state
        self.user_attributes = user_attributes

    @property
    def last_state_active_rg(self):
        return self.last_state and self.last_state.active_rg

    @property
    def last_state_response(self):
        if not self.last_state: return None
        if hasattr(self.last_state, 'prompt_results'): return self.last_state.prompt_results[self.last_state.active_rg]
        else: return self.last_state.response_results[self.last_state.active_rg]