"""
Shared visuals between recipe and wikihow prep screens.
"""

from taco.response_generators.taco_rp import apl, helpers, time_helpers


def get_recipe_prep_visual(main_template_item):
    """
    Creates the dictionary representing the APL visual.

    Arguments:
        main_template_item (dict) key-value pairs that are recipe-specific.
    """
    assert isinstance(main_template_item, dict)

    assert "headerTitle" in main_template_item
    assert "headerSubtitle" in main_template_item

    assert "imageSource" in main_template_item
    assert "backgroundImageSource" in main_template_item

    assert "primaryText" in main_template_item
    assert "secondaryText" in main_template_item
    assert "bodyText" in main_template_item

    return {
        "document": {
            "type": "APL",
            "version": "1.8",
            "import": [{"name": "alexa-layouts", "version": "1.3.0"}],
            "settings": {"idleTimeout": 60000},
            "mainTemplate": {
                "items": [
                    {
                        **apl.shared_keys(),
                        "scrollViewId": "AlexaTextListSequence",
                        "type": "AlexaDetail",
                        "detailImageAlignment": "right",
                        "detailType": "generic",
                        "headerBackButton": True,
                        "imageScale": "best-fill",
                        "button1Text": "Start",
                        "button1PrimaryAction": [
                            {
                                "type": "SendEvent",
                                "arguments": ["StartRecipeButtonPressed"],
                            }
                        ],
                        "button1Style": "ingress",
                        **main_template_item,
                    }
                ],
            },
        },
        "type": "Alexa.Presentation.APL.RenderDocument",
        "token": "taco_prep_document_token",
    }


def make_recipe_info(recipe, docparse):
    """
    Makes a nicely formatted string with information about the recipe for screen devices.

    Arguments:
        recipe (recipe_helpers.Recipe)
        docparse (list): A (possibly empty) list of parsed step dictionaries

    Examples:

    1h 12m | 15 steps
    """

    items = []

    time_str = recipe.default_time_str
    if recipe.minutes is not None:
        hours, minutes = time_helpers.to_hours_minutes(recipe.minutes)
        time_str = time_helpers.for_screen(hours, minutes)
    items.append(time_str)

    servings_str = recipe.default_servings_str
    if recipe.servings:
        servings_str = (
            f" {recipe.servings} {helpers.simple_plural(recipe.servings, 'serving')}"
        )

    steps = recipe.steps
    if docparse:
        steps = len(docparse)

    return f"{time_str} {apl.Emoji.clipboard} {steps} {helpers.simple_plural(steps, 'step')} {apl.Emoji.fork_knife}{servings_str}"


def make_recipe_body_text(recipe):
    ingredients = "<br>".join(
        f'<span fontSize="28dp">\u2022 {ingredient}</span>'
        for ingredient in recipe.ingredients
    )

    return f'<span fontSize="48dp"><b>Ingredients</b><br> </span>{ingredients}'


def _make_task_list_items(task):
    """
    Makes a list of items with keys 'ingredientsContentText' and 'ingredientsPrimaryAction' (even though they are not ingredients).

    If the task has methods, then each method is an 'ingredient'. If the task has parts, then each part is an 'ingredient'.

    This function probably shouldn't be called with a task that has one method and one part. It will work, but it will only return one item, which isn't good for user experience.
    """

    list_items = []
    if task.has_parts:
        for i, method in enumerate(task.methods):
            list_items.append(
                {
                    "ingredientsContentText": f"Part {i+1}: {method.name} ({len(method)} steps)",
                    "ingredientsPrimaryAction": {
                        "type": "SendEvent",
                        "arguments": ["PartSelected", i + 1],
                    },
                }
            )
    else:
        for i, method in enumerate(task.methods):
            list_items.append(
                {
                    "ingredientsContentText": f"Method {i+1}: {method.name} ({len(method)} steps)",
                    "ingredientsPrimaryAction": {
                        "type": "SendEvent",
                        "arguments": ["MethodSelected", i + 1],
                    },
                }
            )

    return list_items


# WIKIHOW SUMMARY


def get_wikihow_prep_visual(wikihow_task):
    """
    Creates the dictionary representing the APL visual for wikihow.

    Arguments:
        wikihow_task (WikiHowTask)
    """

    subtitle = "Alexa Prize - wikiHow"

    if len(wikihow_task.methods) > 1:
        return {
            "document": {
                "type": "APL",
                "version": "1.8",
                "import": [{"name": "alexa-layouts", "version": "1.3.0"}],
                "settings": {"idleTimeout": 60000},
                "mainTemplate": {
                    "items": [
                        {
                            **apl.shared_keys(),
                            "type": "AlexaDetail",
                            "detailImageAlignment": "right",
                            "detailType": "recipe",
                            "headerBackButton": True,
                            "imageScale": "best-fill",
                            "scrollViewId": "AlexaTextListSequence",
                            "headerTitle": wikihow_task.title,
                            "headerSubtitle": subtitle,
                            "backgroundImageSource": apl.Urls.wikihow_background_image,
                            "imageSource": wikihow_task.img_url,
                            "primaryText": None,
                            "secondaryText": None,
                            "ingredientsText": None,
                            "ingredientListItems": _make_task_list_items(wikihow_task),
                            **wikihow_task.rating_keys(),
                        }
                    ],
                },
            },
            "type": "Alexa.Presentation.APL.RenderDocument",
            "token": "taco_prep_document_token",
        }

    helpers.logic_exception(
        f"Wikihow Task {wikihow_task.title} ({wikihow_task.url}) has no summary and only one method!"
    )

    return {
        "document": {
            "type": "APL",
            "version": "1.8",
            "import": [{"name": "alexa-layouts", "version": "1.3.0"}],
            "settings": {"idleTimeout": 60000},
            "mainTemplate": {
                "items": [
                    {
                        **apl.shared_keys(),
                        "type": "AlexaDetail",
                        "detailImageAlignment": "right",
                        "detailType": "location",
                        "headerBackButton": True,
                        "imageScale": "best-fill",
                        "scrollViewId": "AlexaTextListSequence",
                        "headerTitle": wikihow_task.title,
                        "headerSubtitle": subtitle,
                        "backgroundImageSource": apl.Urls.wikihow_background_image,
                        "imageSource": wikihow_task.img_url,
                        # Blank text forces a new line (for spacing).
                        "secondaryText": " ",
                        "bodyText": wikihow_task.summary,
                        "locationText": None,
                        **wikihow_task.rating_keys(),
                    }
                ],
            },
        },
        "type": "Alexa.Presentation.APL.RenderDocument",
        "token": "taco_prep_document_token",
    }
