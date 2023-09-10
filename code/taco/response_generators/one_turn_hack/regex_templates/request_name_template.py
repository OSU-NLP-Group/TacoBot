from taco.core.regex.regex_template import RegexTemplate
from taco.core.regex.util import OPTIONAL_TEXT, NONEMPTY_TEXT, \
    OPTIONAL_TEXT_PRE, OPTIONAL_TEXT_POST, OPTIONAL_TEXT_MID


class RequestNameTemplate(RegexTemplate):
    slots = {
        "request": ["tell", "what's", "say", "what", "know", "repeat"],
    }
    templates = [
        OPTIONAL_TEXT_PRE + "{request}" + OPTIONAL_TEXT_MID + "my name" + OPTIONAL_TEXT_POST
    ]
    positive_examples = [
        ("hey what's my name", {"request": "what's"}),
        ("say my name", {"request": "say"}),
        ("what's my name", {'request': "what's"}),
        ("can you tell me my name", {'request': "tell"}),
        ("do you even know my name", {'request': 'know'}),
        ("what is my name", {'request': 'what'}),
        ("repeat my name", {'request': 'repeat'})
    ]
    negative_examples = [
        "what's the name of the song",
        "what's your name"
    ]
