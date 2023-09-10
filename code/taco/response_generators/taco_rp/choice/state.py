from typing import Optional

from taco.core.user_attributes import UserAttributes
from taco.core.state import State as C_State
from taco.core.response_generator.state import *

@dataclass
class State(BaseState):
    cur_food: Optional['WikiEntity'] = None

@dataclass
class ConditionalState(BaseConditionalState):
    cur_food: Optional['WikiEntity'] = NO_UPDATE
    prompt_treelet: Optional[str] = NO_UPDATE
    n_current_state: Optional[C_State] = None
    n_user_attributes: Optional[UserAttributes] = None