from taco.response_generators.taco_rp.templates import Template

from taco.response_generators.taco_rp import examples

import random

HELP_WITH = [
    Template("What can I help with? "),
    Template("What can I help you with? "),
    Template("How can I help? "),
    Template("How can I help you? "),
]

WELCOME = [
    Template(
        "${help} For example, ask me how to ${task}, or search for ${recipe} recipes. "
    ),
    Template(
        "My passion is helping humans with cooking and do-it-yourself tasks around the house. ${help} For example, ask me for recipes for ${recipe} or how to ${task}. "
    ),
    Template(
        "I like to help humans with cooking and do-it-yourself tasks around the house. ${help} For instance, ask me for recipes for ${recipe} or how to ${task}. "
    ),
]
RECOMMEND = [
    Template("I can also tell you my favorite tasks or recipes. "),
    Template("I also have favorite tasks and recipes you might like. "),
]
REVISIT = [
    Template(
        "Okay, let’s try something else. For example, ask me how to ${task} or search recipes for ${recipe}. "
    ),
]


def select_template(revisited=False):
    task = examples.random_task()
    recipe = examples.random_recipe()

    if revisited:
        utterance = random.choice(REVISIT).substitute(task=task.lower(), recipe=recipe.lower())
    else:
        utterance = random.choice(WELCOME).substitute(
            task=task.lower(), recipe=recipe.lower(), help=random.choice(HELP_WITH).substitute()
        )

    return utterance + random.choice(RECOMMEND).substitute(), task, recipe
