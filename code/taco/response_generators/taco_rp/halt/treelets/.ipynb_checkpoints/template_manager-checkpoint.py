from taco.response_generators.taco_rp.templates import Template

from taco.response_generators.taco_rp import vocab

import random

GOODBYES = [
    Template("Enjoy the rest of your day! "),
    Template("Hope the rest of your day is ${pos_adj}! "),
]


def say_goodbye(pos_adj=None):
    """
    Returns a goodbye phrase with lots of linguistic diversity.
    """

    if not pos_adj:
        pos_adj = random.choice(vocab.POSITIVE_ADJECTIVES)

    return random.choice(GOODBYES).substitute(pos_adj=pos_adj)


THANK_YOU_TEMPLATES = [
    Template("That was fun! "),
    Template("That’s a job well done! "),
    Template("${pos_adj} work! "),
]

SEND_ACTIVITY_TEMPLATES = [
    Template("I’ll send a summary to your Alexa app’s activity tab. "),
]


def utterance():
    """
    Returns a complete 'thank you' utterance, including a goodbye.
    """

    pos_adj1, pos_adj2 = random.sample(vocab.POSITIVE_ADJECTIVES, 2)

    thank_you = random.choice(THANK_YOU_TEMPLATES).substitute(pos_adj=pos_adj1)
    send_activity = random.choice(SEND_ACTIVITY_TEMPLATES).substitute()

    return thank_you + send_activity + say_goodbye(pos_adj2)
