import functools
import threading
from urllib import parse
from typing import List
import logging

import jsonpickle

from tacobot.config import SIZE_THRESHOLD

logger = logging.getLogger('tacologger')



def parse_blocklist_class_from_profanity_response(response):
    """
    helper method to extract the blocklist's offensive class from one service output from AlexaPrizeToolkitService
    :param response from toolkit service, List of Dict

    :return: blocklist classes, List of Number, 0: not offensive, 1: offensive
    """
    profanity_result = []
    for profanity in response.get('offensivenessClasses', []):
        for elem in profanity.get('values', None):
            source = elem.get('source', None)
            offensive_class = elem.get('offensivenessClass', None)
            if source == 'keyword':
                profanity_result.append(offensive_class)
    return profanity_result


def parse_overall_class_from_profanity_response(response: List[dict]) -> List[int]:
    """
    helper method to extract the overall offensive class from one service output from AlexaPrizeToolkitService
    :param response from toolkit service, List of Dict
    :return: overall class, List of Number, 0: not offensive, 1: offensive
    """
    profanity_result = []
    for profanity in response.get('offensivenessClasses', []):
        overall_class = profanity.get('overallClass', None)
        profanity_result.append(overall_class)
    return profanity_result


def map_two_lists(input_data_list, profanity_result_list):
    """
    Return the clean data list.
    i.e. input_data_list = ['a','b','c']
         profanity_result_list = [0, 0, 1]
         result: clean_data = ['a','b']
    """
    assert len(input_data_list) == len(profanity_result_list), "Two lists must have the same length. "
    clean_data = []
    for data, profanity in zip(input_data_list, profanity_result_list):
        if profanity == 0:
            clean_data.append(data)
    return clean_data


def is_url_valid(url, qualifying=None):
    min_attributes = ('scheme', 'netloc')
    qualifying = min_attributes if qualifying is None else qualifying
    try:
        token = parse.urlparse(url)
        return all([getattr(token, qualifying_attr)
                    for qualifying_attr in qualifying])
    except:
        return False


def killable(func):
    """Decorator to denote a method as killable"""
    @functools.wraps(func)
    def wrapper_killable(*args, **kwargs):
        current_thread = threading.currentThread()
        killable = getattr(current_thread, "killable", False)
        # Check if we are running in a killable thread
        if killable:
            logger.info(f"{func.__qualname__} running in a killable thread.")
            out = {}

            if getattr(current_thread, "isKilled", False) and current_thread.isKilled():
                logger.primary_info(f"{func.__qualname__} preemptively killed externally.")
                return None

            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                out['out'] = result

            # logging.warning(f"args {args}")
            client_thread = threading.Thread(target=wrapper, args=args, kwargs=kwargs)
            client_thread.start()
            while client_thread.is_alive():
                client_thread.join(timeout=0.1)
                if getattr(current_thread, "isKilled", False) and current_thread.isKilled():
                    logger.primary_info(f"{func.__qualname__} killed externally.")
                    return None
            return out['out']
        else:
            return func(*args, **kwargs)
    return wrapper_killable
