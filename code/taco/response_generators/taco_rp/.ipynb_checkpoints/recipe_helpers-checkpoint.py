"""
Module with a bunch of recipe helpers. Stuff like getting the recipe time, recipe steps, etc. 

Also includes a utility class Recipe that represents a recipe nicely.
"""
import json
import re

from taco.response_generators.taco_rp import apl, helpers

WHOLE_FOODS_DIFFICULTIES = ["easy", "average", "difficult", None]


class Recipe(helpers.Choice):
    """
    Utility class to represent a recipe.
    """

    default_servings_str = "N/A"

    def __init__(self, raw_result):
        self.item = raw_result["recipe"]

        self.rating, self.rating_count = _get_ratings(raw_result)
        self.img_url = _get_image_url(self.item)

        self.description = None
        if "description" in self.item and self.item["description"]:
            self.description = self.item["description"]

        # Other attributes
        self.minutes = None
        if "totalTimeMinutes" in self.item and self.item["totalTimeMinutes"]:
            self.minutes = self.item["totalTimeMinutes"]

        self.title = self.item["displayName"]
        self.name = self.title.lower()

        self.step_list = _get_steps(self.item)
        self.steps = len(self.step_list)
        self.ingredients = list(_get_ingredients(self.item["ingredients"]))

        if self.item["difficulty"]:
            self.difficulty = WHOLE_FOODS_DIFFICULTIES.index(
                self.item["difficulty"].lower()
            )
        else:
            self.difficulty = (
                3  # WHOLE_FOODS_DIFFICULTIES.index(self.recipe['difficulty'])
            )

        self.servings = None
        if self.item["servings"]:
            self.servings = self.item["servings"]

        self.diets = self.item["diets"]
        # TODO: parse recipe nutrition
        # if self.item["nutrition"] and self.item["nutrition"]["nutrients"]:
        #     print(self.item["nutrition"])

    @classmethod
    def from_query(cls, item):
        return cls(json.loads(item))

    @property
    def stars(self):
        """
        Gets a string representing the number of stars a recipe has.

        Returns:
            Either None or a string represenation of a floating point number. It has at most one decimal point, and if it is .0, then it has no decimal points.

            For example, it could return '4.1', '5', None, but never '4.0'.
        """
        if self.rating == 0.0:
            return None

        # This returns up to two significant digits. Luckily for us, if the rating is 4.04, this returns "4". I've included other examples below that you can try in a REPL.
        # f"{4.56:.2g}" == '4.6'
        # f"{4.05:.2g}" == '4'
        # f"{4.06:.2g}" == '4.1'
        return f"{self.rating:.2g}"

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (
            self.rating == other.rating
            and self.title == other.title
            and self.minutes == other.minutes
            and self.steps == other.steps
            and self.difficulty == other.difficulty
        )

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return f"Recipe(name={self.name}, minutes={self.minutes}, steps={self.steps})"


class Step:
    def __init__(self, number, text, ingredients, images):
        self.number = number
        self.display_number = number + 1
        self.text = text
        self.ingredients = ingredients
        self.images = images

    @property
    def utterance(self):
        return re.sub(r"\(.*?\)", "", self.text)

    @property
    def short(self):
        return len(self.utterance.split()) <= 30


def _get_steps(recipe_item):
    steps = []
    step_number = 0

    for raw_step in recipe_item["instructions"]:
        step_text = raw_step["stepText"].replace("approx.", "approximately")
        step_ingredients = raw_step["stepIngredients"]

        for sentence in re.split(r"\.\s+", step_text):
            sentence = sentence.strip().capitalize()
            if re.search("[a-zA-Z]", sentence) is None:
                continue

            images = [image["url"] for image in raw_step["stepImages"]]
            steps.append(Step(step_number, sentence, step_ingredients, images))
            step_number += 1

    return steps


def _get_ratings(raw_recipe):
    rating, rating_count = 0.0, 0.0
    if "rating" not in raw_recipe or not raw_recipe["rating"]:
        return rating, rating_count

    rating_dct = raw_recipe["rating"]
    if "ratingValue" in rating_dct and isinstance(rating_dct["ratingValue"], float):
        rating = rating_dct["ratingValue"]

    if "ratingCount" in rating_dct and isinstance(rating_dct["ratingCount"], int):
        rating_count = rating_dct["ratingCount"]

    return rating, rating_count


def _get_image_url(recipe_item):
    if "images" not in recipe_item or not recipe_item["images"]:
        return apl.Urls.default_recipe_image

    for image in recipe_item["images"]:
        # This image is a generic food network image. We don't want it.
        # https://m.media-amazon.com/images/S/alexa-kitchen-msa-na-prod/recipes/foodnetwork/a81c5fd822c5815ec08c7599e36448d6fd581e8d3486aa05dd6474173946d6a4.jpg
        if (
            "a81c5fd822c5815ec08c7599e36448d6fd581e8d3486aa05dd6474173946d6a4"
            in image["url"]
        ):
            continue
        return image["url"]

    return apl.Urls.default_recipe_image


def _get_ingredients(raw_ingredients):
    """
    Sometimes recipes have decimal points in their description:

    1.0 Tbsp Honey Powder

    This fixes that if possible.
    """
    ingredients = []
    for ingredient in raw_ingredients:
        if ".0" not in ingredient["displayText"]:
            ingredients.append(ingredient["displayText"])
            continue

        unit_table = {
            "TABLESPOON": "tbsp",
            "TEASPOON": "tsp",
            "CUP": "cup",
            "SLICE": "slice",
            "POUND": "lb",
            "OUNCE": "oz",
            "COUNT": "",
            "CLOVE": "clove",
            "PINCH": "pinch",
        }

        if (
            ingredient["unit"] not in unit_table
            or not ingredient["ingredient"]
            or not ingredient["quantity"]
        ):
            helpers.logic_exception("Ingredient quantity missing from unit table: " + ingredient["displayText"])
            ingredients.append(ingredient["displayText"])
            continue

        quantity = ingredient["quantity"]
        unit = unit_table[ingredient["unit"]]
        name = ingredient["ingredient"]

        parts = [part for part in (quantity, unit, name) if part]
        if quantity > 1:
            ingredients.append(" ".join(map(str, parts)))
            continue

        quantity_char = quantity_unicode(quantity)
        if quantity_char is None:
            helpers.logic_exception("Ingredient missing from unicode table:", ingredient)
            ingredients.append(ingredient["displayText"])
            continue

        ingredients.append(f"{quantity_char} {unit} {name}")

    ingredients = [replace_ascii_fractions(ingredient) for ingredient in ingredients]
    return ingredients


def disambiguate_two_recipes(first, second):
    if first.name == second.name:
        if first.minutes and second.minutes and first.minutes != second.minutes:
            return f"the first with {first.minutes} minutes, or the second with {second.minutes} minutes? "

        return f"the first with {first.rating:.2g} stars, or the second with {second.rating:.2g} stars? "

    return f"the first, {first.name}, or the second, {second.name}? "


def disambiguate_three_recipes(first, second, third):
    if first.name == third.name:
        if second.name == third.name:
            if (
                first.minutes
                and second.minutes
                and third.minutes
                and len(set([first.minutes, second.minutes, third.minutes])) == 3
            ):
                return f"the first with {first.minutes} minutes, the second with {second.minutes} minutes, or the third with {third.minutes} minutes? "

            return f"the first with {first.rating:.2g} stars, the second with {second.rating:.2g} stars, or the third with {third.rating:.2g} stars? "

        if first.minutes and third.minutes and first.minutes != third.minutes:
            return f"the first, {first.name} with {first.minutes} minutes, the second, {second.name}, or the third, {third.name} with {third.minutes} minutes? "

        return f" the first, {first.name} with {first.rating:.2g} stars, the second, {second.name}, or the third, {third.name} with {third.rating:.2g} stars? "

    if first.name == second.name:
        if first.minutes and second.minutes and first.minutes != second.minutes:
            return f"the first, {first.name} with {first.minutes} minutes, the second, {second.name} with {second.minutes} minutes, or the third, {third.name}? "

        return f"the first, {first.name} with {first.rating:.2g} stars, the second, {second.name} with {second.rating:.2g} stars, or the third, {third.name}? "

    if second.name == third.name:
        if third.minutes and second.minutes and second.minutes != third.minutes:
            return f"the first, {first.name}, the second, {second.name} with {second.minutes} minutes, or the third, {third.name} with {third.minutes} minutes? "

        return f"the first, {first.name}, the second, {second.name} with {second.rating:.2g} stars, or the third, {third.name} with {third.rating:.2g} stars? "

    return f"the first, {first.name}, the second, {second.name}, or the third, {third.name}? "


def query_to_recipes(query_result):
    """
    Converts a query result to a list of Recipes.
    """
    return [Recipe.from_query(item) for item in query_result["documents"]]


def quantity_unicode(quantity):
    lookup = {
        0.5: "\u00bd",
        # Thirds
        0.33: "\u2153",
        0.66: "\u2154",
        0.67: "\u2154",
        # Fourths
        0.25: "\u00bc",
        0.75: "\u00be",
        # Fifths
        0.2: "\u2155",
        0.4: "\u2156",
        0.6: "\u2157",
        0.8: "\u2158",
        # Eighths
        0.125: "\u215b",
        0.375: "\u215c",
        0.625: "\u215d",
        0.875: "\u215e",
        # Tenths
        0.1: "\u2152",
        1: "1",
    }

    if quantity not in lookup:
        return None

    return lookup[quantity]


def replace_ascii_fractions(text):
    """
    Replaces ascii fractions like 1/3 with unicode fraction characters.
    """

    lookup = {
        "1/2": "\u00bd",
        # Thirds
        "1/3": "\u2153",
        "2/3": "\u2154",
        # Fourths
        "1/4": "\u00bc",
        "3/4": "\u00be",
        # Fifths
        "1/5": "\u2155",
        "2/5": "\u2156",
        "3/5": "\u2157",
        "4/5": "\u2158",
        # Sixths
        "1/6": "\u2159",
        "5/6": "\u215a",
        # Sevenths
        "1/7": "\u2150",
        # Eighths
        "1/8": "\u215b",
        "3/8": "\u215c",
        "5/8": "\u215d",
        "7/8": "\u215e",
        # Ninths
        "1/9": "\u2151",
        # Tenths
        "1/10": "\u2152",
    }

    for ascii_frac, unicode_frac in lookup.items():
        text = text.replace(ascii_frac, unicode_frac)

    frac_pattern = r"\d+/\d+"

    if re.search(frac_pattern, text):
        helpers.logic_exception(
            f"Text '{text}' has a fraction in it!"
        )  # pragma: nocover

    return text
