from urllib import parse
from typing import List

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
