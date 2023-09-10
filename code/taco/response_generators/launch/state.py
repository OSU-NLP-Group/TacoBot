from dataclasses import dataclass
from typing import Optional
from taco.core.response_generator.state import BaseState, BaseConditionalState, NO_UPDATE
from taco.response_generators.launch.launch_helpers import UserIntent

@dataclass
class State(BaseState):
    asked_name_counter: int = 0  # how many times we've asked the user's name
    user_intent = None

@dataclass
class ConditionalState(BaseConditionalState):
    user_intent: Optional[UserIntent] = None # determines if the user wants to give name or not

