from injector import inject, singleton
from .user_attributes_manager import UserAttributesManager
from .taco_user_attributes import UserAttributes
from .taco_event import Event


@singleton
class Analyzer(object):
    """
    This class is used to prepare data extracting from lambda event object and 
    persistent attribute from DynamoDB, if persistance is enabled.
    """

    @inject(
        event=Event,
        attributes=UserAttributes,
        user_attributes_manager=UserAttributesManager
    )
    def __init__(self, event, attributes, user_attributes_manager):
        # type: (Event, UserAttributes, UserAttributesManager) -> None
        self._event = event
        self._attributes = attributes
        self._user_attributes_manager = user_attributes_manager

    def _merge_attributes_from_db(self) -> None:
        """
        Fetch attributes from last session and merge to current turn's attributes.
        """
        event = self._event
        if self._user_attributes_manager.persistence_enabled and (
                event.get('session.sessionId') is not None or event.get('session.new')
        ):
            persistent_attributes = self._user_attributes_manager.retrieve_user_attributes(self._event.user_id)
            if persistent_attributes is not None:
                self._attributes.merge(persistent_attributes)
                # Use the conversation_id from event as authority since last session's conversation_id may be outdated
                self._attributes.conversationId = event.conversation_id

    def _extract_feature(self) -> dict:
        event = self._event
        attributes = self._attributes

        mode = attributes.mode

        if mode is None:
            mode = ''

        request_type = event.get('request.type')
        intent = event.get('request.intent.name', '')

        return {
            'new': event.get('session.new'),
            'mode': mode,
            'request_type': request_type,
            'intent': intent
        }

    def analyze(self) -> dict:
        """
        Merge session attributes from lambda event object and the one from DynamoDB, if it's a new session.
        Fetch mode, reqeust type, intent and wheter current session is a new session from lambda event parameter and session attributes.
        
        :return A dictionary contains data used by `IntentMapper`.
        """
        
        self._merge_attributes_from_db()
        return self._extract_feature()
        
