from taco.response_generators.personal_issues.response_templates.response_components import *
from taco.core.regex.regex_template import RegexTemplate
from taco.core.regex.util import OPTIONAL_TEXT, OPTIONAL_TEXT_PRE, OPTIONAL_TEXT_POST
from taco.core.response_generator.response_template import ResponseTemplateFormatter

import logging

logger = logging.getLogger('tacologger')

PRIMER = [
    "hopefully",
    "I hope"
]

class GPTPrefixResponseTemplate(ResponseTemplateFormatter):
    slots = {
        "validate": STATEMENTS_VALIDATE,
        "primer": PRIMER
    }

    templates = [
        "{validate} {primer}"
    ]
