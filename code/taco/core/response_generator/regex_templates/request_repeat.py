from taco.core.regex import word_lists
from taco.core.regex.regex_template import RegexTemplate
from taco.core.regex.util import OPTIONAL_TEXT_POST, OPTIONAL_TEXT_PRE, OPTIONAL_TEXT_MID
from taco.core.regex.word_lists import CONTINUER

class RequestRepeatTemplate(RegexTemplate):
    slots = {
        "say_that_again": word_lists.SAY_THAT_AGAIN
    }
    templates = [
        OPTIONAL_TEXT_PRE + "{say_that_again}",
    ]
    positive_examples = [
        ("what did you just say", {"say_that_again": "what did you just say"}),
        ("could you please repeat yourself", {"say_that_again": "please repeat yourself"}),
        ("can you ask me that again", {"say_that_again": "can you ask me that again"}),
        ("repeat what you just said", {"say_that_again": "repeat what you just said"}),
        ("say that again", {"say_that_again": "say that again"}),
        ("say that again please", {"say_that_again": "say that again please"}),
        ("what was the question",  {"say_that_again": "what was the question"}),
        ("sorry what was that", {"say_that_again": "what was that"}),
        ("whoops i didn't quite catch that", {"say_that_again": "i didn't quite catch that"}),
        ("wait sorry could you please just say that one more time", {"say_that_again": "say that one more time"}),
        ("i'm sorry i couldn't hear that", {"say_that_again": "i couldn't hear that"}),
        ("what", {"say_that_again": "what"}),
        ("what can you repeat again sorry can i hear you", {"say_that_again": "can you repeat again"})
    ]
    negative_examples = [
        "i'm sorry to hear that"
    ]
