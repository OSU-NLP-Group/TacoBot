"""
This file has vocabulary that can be used in a variety of locations. This improves the diversity of tacobot's utterances.
"""

import random


POSITIVE_ADJECTIVES = [
    "great",
    "awesome",
    "nice",
    "magnificent",
    "fantastic",
    "outstanding",
    "marvelous",
    "stupendous",
    "amazing",
    "incredible",
    "spectacular",
    "terrific",
    "wonderful",
    "excellent",
    "tremendous",
    "fabulous",
    "stellar",
    "sensational",
    "cool",
    "brilliant",
]

SAD_EXCLAMATIONS = [
    "geez",
    "darn",
    "blimey",
    "gosh",
    "cripes",
    "yikes",
    "golly",
]


def say_as(utterance, type, **kwargs):
    """
    Generic say-as f-string
    """
    kwargs_str = " ".join([f'{key}="{value}"' for key, value in kwargs.items()])

    return f"<{type} {kwargs_str}> {utterance} </{type}> "


def say_excited(utterance, intensity="low"):
    """
    Says utterance excitedly
    """
    return say_as(utterance, "amazon:emotion", name="excited", intensity="low")


def say_interjection(interjection):
    kwargs = {"interpret-as": "interjection"}
    return say_as(interjection, type="say-as", **kwargs)


def positive_exclamation():
    return random.choice(POSITIVE_ADJECTIVES) + "! "
