from taco.response_generators.taco_rp import time_helpers


class Choice:
    default_rating_str = "N/A"
    default_steps_str = "N/A"
    default_time_str = time_helpers.for_screen(hours=None, minutes=None)

    def rating_text(self):
        rating_count = getattr(self, "rating_count", None)
        if rating_count:
            return f"({rating_count} {simple_plural(rating_count, 'rating')})"

        return ""

    def rating_keys(self):
        rating = getattr(self, "rating", None)
        if rating:
            return {
                "ratingNumber": rating,
                "ratingSlotMode": "multiple",
                "ratingText": self.rating_text(),
            }

        return {}


def simple_plural(count, word):
    if count == 1:
        return word

    return word + "s"


def short_number(count):
    """
    Returns a short string representing a number.

    Examples:
        1,234,567 => 1M
        1,234 => 1K
    """

    table = {
        1_000: "K",
        1_000_000: "M",
        1_000_000_000: "B",
        1_000_000_000_000: "T",
        1_000_000_000_000_000: "Q",
    }

    for lower_bound, letter in reversed(sorted(table.items())):
        if count > lower_bound:
            return f"{count // lower_bound}{letter}"

    return count


def logic_exception(err):
    print(f"LogicException: {err}")
