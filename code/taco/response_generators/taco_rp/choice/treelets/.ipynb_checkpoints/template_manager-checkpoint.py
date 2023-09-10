import random

from taco.response_generators.taco_rp import vocab
from taco.response_generators.taco_rp.templates import Template


def search_timeout(*, recipe=False, wikihow=False):
    template = None

    if recipe:
        template = Template(
            "${sad_exclamation}! I can’t access the internet. We can try searching again if you repeat, or, "
        )
    elif wikihow:
        template = Template(
            "${sad_exclamation}! I can’t access the internet. We can try searching again if you repeat, or, "
        )
    else:  # pragma: no cover
        assert False

    return template.partial(sad_exclamation=random.choice(vocab.SAD_EXCLAMATIONS))


WIKIHOW_FIRST_VISIT_RECOMMEND_TEMPLATES = [
    Template(f"{vocab.say_interjection('achoo!')} It’s definitely spring time! "),
    Template("I don’t know about you, but I love spring! "),
    Template(vocab.say_excited("Spring is in the air! ")),
    Template(vocab.say_excited("Spring is here! ")),
]


def first_visit_recommend(*, recipe=False, wikihow=False):
    if recipe:
        return Template(
            '<amazon:emotion name="excited" intensity="low"> It’s ${cat} time! </amazon:emotion> '
        )
    elif wikihow:
        template = random.choice(WIKIHOW_FIRST_VISIT_RECOMMEND_TEMPLATES)
        return template
    else:  # pragma: no cover
        assert False


def nothing_better(*, recipe=False, wikihow=False):
    if recipe:
        return Template(
            "${sad_exclamation}! I can’t find any good recipes. Let’s try something else, like recipes for ${recipe}. Or, you can say, stop, and come back later. "
        ).partial(sad_exclamation=random.choice(vocab.SAD_EXCLAMATIONS))
    elif wikihow:
        return Template(
            "${sad_exclamation}! I can’t find any good tasks. Please try another task with me, such as how to ${task}. Or, you can say, stop, and come back later. "
        ).partial(sad_exclamation=random.choice(vocab.SAD_EXCLAMATIONS))
    else:  # pragma: no cover
        assert False


def no_results(*, recipe=False, wikihow=False):
    template = None
    if recipe:
        template = Template("${sad_exclamation}! I couldn’t find any recipes I liked. ")
    elif wikihow:
        template = Template("${sad_exclamation}! I couldn’t find any tasks I liked. ")
    else:  # pragma: no cover
        assert False

    return template.partial(sad_exclamation=random.choice(vocab.SAD_EXCLAMATIONS))


# Ron: MUST attribute wikihow/wholefoods (Amazon), also changing to period do to question rephrase (see the *_choice.py)
def option_intro(*, recipe=False, wikihow=False):
    template = None
    if recipe:
        template = random.choice([Template("Here are some of my favorite whole foods recipes. ")])
    elif wikihow:
        template = random.choice(
            [
                Template("Here are some fun wikihow tasks for the season. "),
                Template("Here are some wikihow tasks I think are really fun. "),
            ]
        )
        return template
    else:  # pragma: no cover
        assert False

    return template

# Ron: we are removing this
def cancel_to_start_over():
    return Template("Please say cancel whenever you’d like to start over. ")


# Ron: let's use "Sure!" here as we are using "Okay!" if we say cancel -- which will become okays in a row
HELP_WITH_RECIPE_QUERY_TEMPLATE = [
    Template("Sure! ${query} sounds delicious. "),
    Template("Sure! ${query} sounds yummy. ")
]

HELP_WITH_RECIPE_REC_TEMPLATE = [
    Template("Sure! "),
]

# Ron: adding the word "learning" because it might be a "sad" task e.g. fixing sth around the home, 
# but learning it sounds better imo
HELP_WITH_WIKIHOW_QUERY_TEMPLATE = [
    Template("Sure! Learning how to ${query} is a great idea. "),
    Template("Sure! Learning how to ${query} sounds fun. ")
]

HELP_WITH_WIKIHOW_REC_TEMPLATE = [Template("Sure! ")]

# Ron: the extracted query (verb phrase) will be in (to) do form, so the templates here won't be grammatical?
# TEMPLATE-TODO
# Okay -> X sounds fun, X is a great idea, I love this one, I'm excited to help with
# Okay -> X sounds fun, X is a great idea, I like making X, etc.
# (Ash hates the word tasty)
def help_with_query(*, has_query, recipe=False, wikihow=False):
    """
    Arguments:
        has_query (bool): whether there is a non-empty query
        recipe, wikihow (bool): which setting we are in (recipe or wikihow). Only one should be True.
    """

    if recipe:
        if has_query:
            template = random.choice(HELP_WITH_RECIPE_QUERY_TEMPLATE)
        else:
            template = random.choice(HELP_WITH_RECIPE_REC_TEMPLATE)
    elif wikihow:
        if has_query:
            template = random.choice(HELP_WITH_WIKIHOW_QUERY_TEMPLATE)
        else:
            template = random.choice(HELP_WITH_WIKIHOW_REC_TEMPLATE)
    else:  # pragma: no cover
        assert False

    return template #+ cancel_to_start_over()
