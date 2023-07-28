import warnings
from typing import List, Dict, Union


class OutputResponsesConverter(object):

    def convert(self, output_responses_dict: Dict[str, Union[dict, str, list]]) -> List[str]:
        """
        Extract list of "responses" in text from response generator modules
        """
        if len(output_responses_dict) == 0:
            return [], output_responses_dict
        result = []
        converted_output_responses_dict = {}
        for response_generator_name, response in output_responses_dict.items():
            # Special handlings to responses:
            # if response is a dict, try to extract the text out of dict; if response is "Internal Server Error", add warning
            if isinstance(response, dict):
                if "response" in response:
                    response = response['response']
                    if response:  # exclude empty string, None, False
                        result.append(response)
                    converted_output_responses_dict[response_generator_name] = response
                elif "message" in response and response["message"] == "Internal Server Error":
                    warnings.warn(response_generator_name + " returned Internal Server Error")
            elif isinstance(response, list):
                for elem in response:
                    if elem:
                        result.append(elem)
                converted_output_responses_dict[response_generator_name] = response
            else:
                if response:
                    result.append(response)
                converted_output_responses_dict[response_generator_name] = response

        return result, converted_output_responses_dict
