from taco.response_generators.personal_issues.response_templates.response_components import STATEMENTS_OFFER_LISTEN, \
   BEGIN_LISTEN, STATEMENTS_VALIDATE, FIRST_TURN_VALIDATE
from taco.core.regex.regex_template import RegexTemplate
from taco.core.regex.util import OPTIONAL_TEXT, OPTIONAL_TEXT_PRE, OPTIONAL_TEXT_POST
from taco.core.response_generator.response_template import ResponseTemplateFormatter

import logging

logger = logging.getLogger('tacologger')


class FirstTurnResponseTemplate(ResponseTemplateFormatter):
    slots = {
        "begin_listen": BEGIN_LISTEN,
        "validate": FIRST_TURN_VALIDATE,
        "encourage_sharing": STATEMENTS_OFFER_LISTEN
    }

    templates = [
        "{begin_listen} {validate} {encourage_sharing}"
    ]

