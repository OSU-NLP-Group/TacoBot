"""
Visual helpers for the choice screen (where multiple options are presented in a list).
"""

from taco.response_generators.taco_rp import (
    apl,
    helpers,
    recipe_helpers,
    time_helpers,
    wikihow_helpers,
)


def base(main_template_item):
    assert isinstance(main_template_item, dict)
    assert "listItems" in main_template_item
    assert "headerTitle" in main_template_item
    assert "defaultImageSource" in main_template_item
    assert "backgroundImageSource" in main_template_item

    return {
        "document": {
            "type": "APL",
            "version": "1.8",
            "import": [{"name": "alexa-layouts", "version": "1.3.0"}],
            "settings": {"idleTimeout": 60000},
            "mainTemplate": {
                "items": [
                    {
                        "scrollViewId": "AlexaImageListSequence",
                        "type": "AlexaImageList",
                        # Background
                        "backgroundBlur": False,
                        "backgroundOverlayGradient": True,
                        "backgroundColorOverlay": True,
                        # Header
                        "headerAttributionPrimacy": False,
                        "headerBackButton": True,
                        "headerDivider": False,
                        "hideOrdinal": True,
                        # Image
                        "imageAlignment": "center",
                        "imageAspectRatio": "square",
                        "imageBlurredBackground": True,
                        "imageMetadataPrimacy": True,
                        "imageRoundedCorner": True,
                        "imageScale": "best-fill",
                        "hintText": "Try, “compare them”",
                        "listImagePrimacy": True,
                        # Action
                        "primaryAction": {
                            "type": "SendEvent",
                            "arguments": ["ListItemSelected", "${ordinal}"],
                        },
                        **main_template_item,
                    }
                ],
            },
        },
        "type": "Alexa.Presentation.APL.RenderDocument",
        # Must be this value because scroll directives look for this token
        "token": "ImageListDocumentToken",
    }


def make_list_item(item):
    if isinstance(item, recipe_helpers.Recipe):
        return _make_recipe_item(item)

    elif isinstance(item, wikihow_helpers.WikiHowTask):
        return _make_task_item(item)


def _make_recipe_item(recipe):
    """
    Returns a list item with keys primaryText, secondaryText, and imageSource.
    """

    return {
        "primaryText": recipe.title,
        "secondaryText": make_subtitle(recipe),
        "imageSource": recipe.img_url,
    }


def _make_task_item(task):
    return {
        "primaryText": task.name,
        "secondaryText": make_subtitle(task),
        "imageSource": task.img_url,
    }


def make_subtitle(item):
    if isinstance(item, recipe_helpers.Recipe):
        return _make_recipe_subtitle(item)

    elif isinstance(item, wikihow_helpers.WikiHowTask):
        return _make_task_subtitle(item)


def _make_recipe_subtitle(recipe):
    """
    Makes the screen subtitle for a recipe.

    Star (Rating|N/A) Clock (Time|N/A) Plate (Servings|N/A)
    """
    rating_str = recipe.default_rating_str
    if recipe.stars is not None:
        rating_str = recipe.stars

    time_str = recipe.default_time_str
    if recipe.minutes is not None:
        hours, minutes = time_helpers.to_hours_minutes(recipe.minutes)
        time_str = time_helpers.for_screen(hours, minutes)

    servings_str = recipe.default_servings_str
    if recipe.servings:
        servings_str = f"{recipe.servings}"

    return (
        f"{apl.Emoji.star} {rating_str} {time_str} {apl.Emoji.fork_knife}{servings_str}"
    )


def _make_task_subtitle(task):
    """
    Star (Rating|N/A) Target (Views|N/A)
    """

    rating_str = task.default_rating_str
    if task.stars is not None:
        rating_str = task.stars

    views_str = task.default_views_str
    if task.views is not None:
        views_str = f"{helpers.short_number(task.views)} {helpers.simple_plural(task.views, 'view')}"

    return f"{apl.Emoji.star} {rating_str} {apl.Emoji.target} {views_str}"
