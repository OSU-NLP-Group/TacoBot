from taco.core.response_generator.state import BaseState
from taco.response_generators.acknowledgment.state import State as AcknowledgmentState
from taco.response_generators.aliens.state import State as AliensState
from taco.response_generators.categories.state import State as CategoriesState
from taco.response_generators.closing_confirmation.state import State as ClosingConfirmationState
from taco.response_generators.fallback.state import State as FallbackState
from taco.response_generators.food.state import State as FoodState
from taco.response_generators.launch.state import State as LaunchState
from taco.response_generators.neural_chat.state import State as NeuralChatState
from taco.response_generators.neural_fallback.state import State as NeuralFallbackState
from taco.response_generators.offensive_user.state import State as OffensiveUserState
from taco.response_generators.one_turn_hack.state import State as OneTurnHackState
from taco.response_generators.opinion2.state_actions import State as OpinionState
from taco.response_generators.personal_issues.state import State as PersonalIssuesState
from taco.response_generators.sports.state import State as SportsState
from taco.response_generators.pets.state import State as PetsState
from taco.response_generators.transition.state import State as TransitionState
from taco.response_generators.music.state import State as MusicState
from taco.response_generators.wiki2.state import State as WikiState
from taco.response_generators.reopen.state import State as ReopenState

DEFAULT_RG_STATES = {
    'ACKNOWLEDGMENT': AcknowledgmentState(),
    'ALEXA_COMMANDS': BaseState(),
    'ALIENS': AliensState(),
    'CATEGORIES': CategoriesState(),
    'CLOSING_CONFIRMATION': ClosingConfirmationState(),
    'COMPLAINT': BaseState(),
    'FALLBACK': FallbackState(),
    'FOOD': FoodState(),
    'LAUNCH': LaunchState(),
    'MUSIC': MusicState(),
    'NEURAL_CHAT': NeuralChatState(),
    'NEURAL_FALLBACK': NeuralFallbackState(),
    'OFFENSIVE_USER': OffensiveUserState(),
    'ONE_TURN_HACK': OneTurnHackState(),
    'OPINION': OpinionState(),
    'PERSONAL_ISSUES': PersonalIssuesState(),
    'RED_QUESTION': BaseState(),
    'TRANSITION': TransitionState(),
    'WIKI': WikiState(),
    'REOPEN': ReopenState(),
}


def is_default_state(rg_name, state):
    return DEFAULT_RG_STATES[rg_name] == state
