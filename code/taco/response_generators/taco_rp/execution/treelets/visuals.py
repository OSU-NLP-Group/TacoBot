import abc
import random
import re

from taco.response_generators.taco_rp.execution.treelets import utils

def base(main_template_item, last_step):
    """
    Creates the dictionary representing the APL visual.

    Arguments:
        main_template_item (dict) key-value pairs that are recipe- or wikihow- specific.
        last_step (bool) Whether we are on the last step.
    """
    assert isinstance(main_template_item, dict)
    assert "headerTitle" in main_template_item
    assert "headerSubtitle" in main_template_item

    assert "imageSource" in main_template_item
    assert "defaultImageSource" in main_template_item
    assert "backgroundImageSource" in main_template_item

    assert "primaryText" in main_template_item
    assert "secondaryText" in main_template_item

    assert "bodyText" in main_template_item

    next_button = "Next"
    next_button_action = ["NextButtonPressed"]
    if last_step:
        next_button = "Complete"
        next_button_action = ["CompleteButtonPressed"]

    return {
        "document": {
            "type": "APL",
            "version": "1.8",
            "import": [{"name": "alexa-layouts", "version": "1.3.0"}],
            "settings": {"idleTimeout": 60000},
            "mainTemplate": {
                "parameters": [],
                "items": [
                    {
                        "type": "AlexaDetail",
                        "detailImageAlignment": "right",
                        "backgroundColorOverlay": False,
                        "backgroundBlur": False,
                        "imageBlurredBackground": False,
                        "imageScale": "best-fill",
                        "imageAspectRatio": "square",
                        "imageAlignment": "right",
                        "theme": "dark",
                        "button1Text": "Previous",
                        "button1Style": "egress",
                        "button1PrimaryAction": [
                            {
                                "type": "SendEvent",
                                "arguments": ["PreviousButtonPressed"],
                            }
                        ],
                        "button2Text": next_button,
                        "button2Style": "ingress",
                        "button2PrimaryAction": [
                            {
                                "type": "SendEvent",
                                "arguments": next_button_action,
                            }
                        ],
                        **main_template_item,
                    },
                ],
            },
        },
        "type": "Alexa.Presentation.APL.RenderDocument",
        "token": "taco_show_steps_document",
        "datasources": {},
    }


# Hint Text
# To generate hint text, sometimes we need the current step. Not all of the hint texts need these arguments ("next step" doesn't) but they must accept them all. The return type of a hint generator must be str or None (None if the hint is not valid at this time).


def get_hint_text(current_task_docparse, method, step, has_parts):
    """
    Arguments:
        current_task_docparse (List[List[Dict]])
        method (int): current method
        step (int): current step
        has_parts (bool): whether we have parts (always False for recipes)
    """

    if not current_task_docparse:
        return ""
    if method >= len(current_task_docparse):
        return ""
    steplist = current_task_docparse[method]
    if step >= len(steplist):
        return ""

    parsed_step = steplist[step]
    last_step = utils.is_last_step(current_task_docparse, method, step, has_parts)

    # In reverse order of priority because we use .pop() which pops from the end.
    # So Complete should take first priority, then MoreDetails, etc.
    hint_generators = [
        NextStep(),
        SetTimer(parsed_step),
        MoreDetails(parsed_step),
        GoTo(),
        Complete(last_step),
    ]

    text = None
    while not text:
        generator = hint_generators.pop()
        text = generator.generate()

    return f'<span fontSize="30dp"><i>Try “{text}”</i></span>'


class HintGenerator(abc.ABC):
    """
    An abstract class for an object that can generate hint text.
    """

    @abc.abstractmethod
    def generate(self):
        """
        Returns either string or None.
        """

    def coinflip(self):
        return random.random() > 0.5


class Complete(HintGenerator):
    """
    Returns complete if we are at the last step. Otherwise None.
    """

    def __init__(self, last_step):
        """
        Arguments:
            last_step (bool): whether we are at the last step.
        """
        self.last_step = last_step

    def generate(self):
        """
        Returns: "complete" | None
        """
        if self.last_step:
            return "complete"

        return None


class NextStep(HintGenerator):
    """
    Returns "next step", "go on", etc. randomly.
    """

    utterances = [
        "continue",
        "go on",
        "next step",
    ]

    def generate(self):
        """
        Returns: string
        """

        return random.choice(self.utterances)


class MoreDetails(HintGenerator):
    """
    Returns "tell me some details" if the step has details.
    Otherwise returns None.
    """

    def __init__(self, step):
        """
        Arguments:
            step (dict): step dictionary
        """
        self.step = step

    def generate(self):
        """
        Returns: str | None
        """
        if "detail" not in self.step:
            return None

        if not self.step["detail"]:
            return None

        # Only show a more details tip 1/2 of the time if the step has details.
        if self.coinflip():
            return None

        utterances = [
            "tell me more",
            "more details",
        ]
        return random.choice(utterances)


class SetTimer(HintGenerator):
    """
    Returns a question about the setting a timer if it can
    detect a time in the step text. Otherwise returns None.

    The rest of this docstring is an explanation of the heuristic.

    Examples
    ... the last 30 minutes of baking ...
    ... and saute 2 minutes
    ... begin to soften, 3 to 4 minutes
    ... and steam for 8 minutes
    ... and simmer for 8 minutes
    After 15 minutes, stir the rice, re-cover and set the pot off the heat for 5 minutes
    Let sit uncovered at room temperature for 30 minutes ...
    Cook and stir pork, carrot, broccoli, peas, and green onion in melted butter until pork is cooked through, 7 to 10 minutes
    Add lobster tails back to the wok, lightly tossing all ingredients in the wok for another 4 minutes.
    Add garlic, fresh parsley, lemon, juice of lemon, and crushed red pepper flakes to butter and simmer for 5 minutes.
    """

    search_pattern = re.compile(r"for (\d+) minutes\.?$")
    """
    Explanation:
    If the phrase starts with "for", it's normally a simple command (broil for 10 minutes, steam for 5 minutes) and not something hard like (until cooked, 7 to 10 minutes, last 30 minutes of baking)
    We only want to handle one proposed time, not a X to Y minutes time.
    Then we should be at the end of the step, with no extra explanation afterwards.
    """

    def __init__(self, step):
        """
        Arguments:
            step (dict): step dictionary
        """
        self.step = step

    def generate(self):
        """
        Returns: str | None
        """

        if "instruction" not in self.step:
            # Not a recipe step
            return None

        if "minutes" not in self.step["instruction"]:
            # We are using a super simple heuristic
            return None

        instruction = self.step["instruction"].strip()

        # Parse heuristic:
        match = self.search_pattern.search(instruction)

        if not match:
            return None

        minutes = match.group(1)
        return f"Set a timer for {minutes} minutes"


class GoTo(HintGenerator):
    """
    Returns "go to part X", "go to step X", or "go to the last step", "skip two steps" with 50% probability.
    """

    fixed_hints = [
        "go three steps forward",
        "go back three steps",
        "go to the last step",
    ]

    def generate(self):
        """
        Returns: str | None
        """
        if self.coinflip():
            return None

        if self.coinflip():
            return random.choice(self.fixed_hints)

        return None
