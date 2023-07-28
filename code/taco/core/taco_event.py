from injector import singleton
from typing import Optional, Dict, Any, Union

# Use `PathDict` to wrap event parameters from lambda handler function
# Provide shortcut functions to fetch some specific data from the event

class PathDict(object):
    """
    Wrap a dictionary and provide function to get nested item using a string path.
    """

    def __init__(self, init_data: dict) -> None:
        self._data = init_data

    def get(self, 
            path: str, 
            default_val: Optional[Any] = None
        ) -> Union[Optional[Any], Dict[Any, Any]]:
        """
        Given a string path, return nested value. If the string path is invalid, return default value.

        :param path: A string path separated by period. EX: 'request.intent.name'
        :return A nested item, if the path is valid. Or a default value, if the path is invalid.
        """
        key_list = path.split('.')
        cur: Union[Optional[Any], Dict[Any, Any]] = self._data
        for key in key_list:
            if isinstance(cur, dict) and key in cur:
                cur = cur.get(key)
            else:
                cur = default_val
                break
        return cur
    
    @property
    def source(self) -> dict:
        """
        Return original dictionary object
        """
        return self._data



@singleton
class Event(PathDict):
    """
    Use `PathDict` to wrap event parameters from lambda handler function.
    Provide shortcut functions to fetch some specific data from the event.
    """

    @property
    def app_id(self) -> str:
        app_id = self.get('context.System.application.applicationId')
        if app_id is None:
            app_id = self.get('session.application.applicationId')
        if app_id is None:
            app_id = ''
        if not isinstance(app_id, str):
            raise TypeError("app_id should be a str")
        return app_id

    @property
    def user_id(self) -> str:
        user_id = self.get('context.System.user.userId')
        if user_id is None:
            user_id = self.get('session.user.userId')
        if user_id is None:
            user_id = ''
        if not isinstance(user_id, str):
            raise TypeError("user_id should be a str")
        return user_id

    @property
    def conversation_id(self) -> Union[str, None]:
        conversation_id = self.get('request.payload.conversationId')
        if conversation_id is None:
            conversation_id = self.get('session.attributes.conversationId')
        if conversation_id is not None:
            if not isinstance(conversation_id, str):
                raise TypeError("conversation_id should be a str or None")
        return conversation_id

    @property
    def is_experiment(self) -> Union[bool, None]:
        is_experiment = self.get('request.payload.isExperiment')
        if is_experiment is None:
            is_experiment = self.get('session.attributes.isExperiment')
        if is_experiment is not None:
            if not isinstance(is_experiment, bool):
                raise TypeError("is_experiment should be a bool or None")
        return is_experiment

    @property
    def resume_task(self) -> Union[bool, None]:
        resume_task = self.get('request.payload.resumeTask')
        if resume_task is None:
            resume_task = self.get('session.attributes.resumeTask')
        if resume_task is not None:
            if not isinstance(resume_task, bool):
                raise TypeError("resume_task should be a bool or None")
        return resume_task

    @property
    def attributes(self) -> dict:
        attributes_ =  self.get('session.attributes', {})
        if not isinstance(attributes_, dict):
            raise TypeError("attributes should be a dict")
        return attributes_

    @property
    def speech_recognition(self) -> list:
        speech_recognition = self.get('request.payload.speechRecognition.hypotheses')
        if speech_recognition is None:
            speech_recognition = self.get('request.speechRecognition.hypotheses')
        if speech_recognition is None:
            speech_recognition = []
        if not isinstance(speech_recognition, list):
            raise TypeError("speech_recognition should be a list")
        return speech_recognition

    @property
    def ask_access_token(self) -> str:
        ask_access_token = self.get('context.System.apiAccessToken')
        if ask_access_token is None:
            ask_access_token = ''
        if not isinstance(ask_access_token, str):
            raise TypeError("ask_access_token should be a str")
        return ask_access_token

    @property
    def sentiment_score(self) -> dict:
        sentiment_score = self.get('request.sentimentScore', {})
        if not isinstance(sentiment_score, dict):
            raise TypeError("sentiment_score should be a dict")
        return sentiment_score
