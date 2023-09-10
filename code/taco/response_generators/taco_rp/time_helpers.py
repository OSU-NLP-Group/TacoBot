"""
Module for calculating times.
"""


def to_hours_minutes(minutes):
    """
    Converts minutes to a tuple of hours, minutes.

    Minutes is guaranteed to be between 0 and 59 (inclusive).
    """
    try:
        hours = int(minutes / 60)
        minutes = minutes % 60
    except:
        hours = 0
        minutes = 0

    return hours, minutes


def minute_s(minutes):
    """
    Returns a string of either "minute" or "minutes" depending on how many minutes are provided.
    """

    if minutes == 1:
        return "minute"

    return "minutes"


def hour_s(hours):
    """
    Returns a string of either "hour" or "hour" depending on how many hours are provided.
    """
    if hours == 1:
        return "hour"

    return "hours"


def _unicode_lookup(hours, minutes):
    """
    Returns a unicode character that's different based on time. For example, for 27 minutes (which is 0 hours) it will return a clock with 1 hour. For 95 minutes, 2 hours. Etc.
    """
    table = [
        "\U0001F550",  # 1 hour
        "\U0001F551",  # 2 hours
        "\U0001F552",  # 3 hours
        "\U0001F553",  # 4 hours
        "\U0001F554",  # 5 hours
        "\U0001F555",  # 6 hours
        "\U0001F556",  # 7 hours
        "\U0001F557",  # 8 hours
        "\U0001F558",  # 9 hours
        "\U0001F559",  # 10 hours
        "\U0001F55A",  # 11 hours
        "\U0001F55B",  # 12 hours
    ]
    if not hours and not minutes:
        return table[0]

    hours = hours - 1 if minutes == 0 else hours
    if hours < len(table):
        return table[hours]

    return ""


def for_screen(hours, minutes):
    """
    Returns a nicely formatted string for showing on the screen how long something takes.
    """

    def prepend_unicode(timestr):
        unicode_clock = _unicode_lookup(hours, minutes)
        return f"{unicode_clock} {timestr}"

    if not hours and not minutes:
        return prepend_unicode("N/A")

    if hours > 0:
        if minutes == 0:
            return prepend_unicode(f"{hours}h ")
        return prepend_unicode(f"{hours}h {minutes}m")

    return prepend_unicode(f"{minutes}m")


def for_speak(hours, minutes):
    """
    Returns a nicely formatted string for saying out loud how long something takes.
    """

    if hours > 0:
        if minutes == 0:
            return f"{hours} {hour_s(hours)}"

        return f"{hours} {hour_s(hours)} and {minutes} {minute_s(minutes)}"

    return f"{minutes} {minute_s(minutes)}"
