from taco.response_generators.aliens.regex_templates import *
from taco.core.response_generator.response_type import add_response_types, ResponseType
import logging
logger = logging.getLogger('tacologger')

ADDITIONAL_RESPONSE_TYPES = ['OPINION']

ResponseType = add_response_types(ResponseType, ADDITIONAL_RESPONSE_TYPES)

def is_opinion(rg, utterance):
    top_da = rg.state_manager.current_state.dialogact['top_1']
    return len(utterance.split()) >= 10 or top_da == 'opinion'
