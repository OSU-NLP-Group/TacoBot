from typing import Optional

from taco.core.response_generator.state import *

@dataclass
class State(BaseState):
    asked_name_counter: int = 0  # how many times we've asked the user's name
    user_intent = None

@dataclass
class ConditionalState(BaseConditionalState):
    sampled_task: str = ''
    sampled_recipe: str = ''

