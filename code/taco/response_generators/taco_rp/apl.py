class Urls:
    """
    URLs for APL documents.
    """

    # Launch screen background image
    launch_background_image = (
        "https://images.unsplash.com/photo-1560258018-c7db7645254e?q=80"
    )

    # Launch screen image for recommended tasks option
    favorites_task_image = (
        "https://tacobot-static-content.s3.amazonaws.com/undraw-box.png"
    )

    # Used when a task doesn't provide an image.
    default_task_image = (
        "https://images.unsplash.com/photo-1533090161767-e6ffed986c88?q=40"
    )

    default_recipe_image = (
        "https://tacobot-static-content.s3.amazonaws.com/unsplash-cutting-board.jpg"
    )

    # Background when image when choosing a wikkihow task
    wikihow_background_image = "https://tacobot-static-content.s3.amazonaws.com/unsplash-crafts-blurred-50-dimmed.jpg"

    # Background image when choosing a recipe
    recipe_background_image = "https://tacobot-static-content.s3.amazonaws.com/unsplash-cutting-board-blurred-50-dimmed.jpg"


class Emoji:
    # https://unicode-table.com/en/2B50/
    star = "\u2B50"

    # https://unicode-table.com/en/1F374/
    fork_knife = "\U0001F374"

    # https://unicode-table.com/en/1F3AF/
    target = "\U0001F3AF"

    # https://unicode-table.com/en/1F4CB/
    clipboard = "\U0001F4CB"


def shared_keys():
    """
    A dictionary of key-value pairs used by all APL documents.
    """
    return {
        "backgroundBlur": False,  # Display the provided background image with a blur effect.
        "backgroundColorOverlay": False,  # Apply a scrim to the background to make it easier to read the text displayed over the image or video.
        "imageBlurredBackground": False,
        "imageScale": "best-fill",
        "theme": "dark",
    }
