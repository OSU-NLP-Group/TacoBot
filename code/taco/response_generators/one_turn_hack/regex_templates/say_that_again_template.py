from taco.core.regex import word_lists
from taco.core.regex.regex_template import RegexTemplate
from taco.core.regex.util import OPTIONAL_TEXT, NONEMPTY_TEXT, \
    OPTIONAL_TEXT_PRE, OPTIONAL_TEXT_POST, OPTIONAL_TEXT_MID

class SayThatAgainTemplate(RegexTemplate):
    slots = {
        "say_that_again": word_lists.SAY_THAT_AGAIN
    }
    templates = [
        "{say_that_again}",
        OPTIONAL_TEXT_PRE + "{say_that_again}" + OPTIONAL_TEXT_POST,
    ]
    positive_examples = [
        ("what did you just say", {"say_that_again": "what did you just say"}),
        ("could you please repeat yourself", {"say_that_again": "could you please repeat yourself"}),
        ("can you ask me that again", {"say_that_again": "can you ask me that again"}),
        ("repeat what you just said", {"say_that_again": "repeat what you just said"}),
        ("say that again", {"say_that_again": "say that again"}),
        ("say that again please", {"say_that_again": "say that again please"}),
        ("what can you say that again please i didn't catch you", {"say_that_again": "can you say that again please"}),
    ]
    negative_examples = []
