from injector import singleton, inject
from .taco_user_attributes import UserAttributes
from .taco_dynamodb_manager import DynamoDbManager
from .taco_config_constants import ConfigConstants
from typing import *
# from .base_dependency_type import TableName

from injector import Injector_Key

Context = Injector_Key('context')
AppId = Injector_Key('app_id')
TableName = Injector_Key('table_name')
SaveBeforeResponse = Injector_Key('save_before_response')

@singleton
class UserAttributesManager(object):
    """
        This class is used to handle persistence and retrieval of user information.
        """

    @inject(table_name=TableName)
    def __init__(self, table_name):
        self.table_name=table_name
    
    @property
    def persistence_enabled(self):
        return self.table_name is not None

    def persist_user_attributes(self, user_attributes: UserAttributes) -> None:
        """
        This will take the provided user_preferences object and persist it to DynamoDB. It does this by creating
                a dictionary representing the DynamoDB item to push consisting of user_id and a dictionary representing all of
                the user preferences.
        :param user_attributes: input UserAttributes object
        :return: None
        """
        item_dict = {
            ConfigConstants.USER_ID_FIELD_NAME: user_attributes.user_id,
            ConfigConstants.USER_ATTRIBUTE_DICT_FIELD_NAME: user_attributes.map_attributes
        }
        DynamoDbManager.put_item(table_name=self.table_name, item_dict=item_dict)


    def retrieve_user_attributes(self, user_id: str) -> UserAttributes:
        """
        Retrieves and deserialize to a UserAttribute object for the given user id. Return None if there is no item found in DynamoDB for the given user id.
        :param user_id: user id
        :return: UserAttributes object
        """
        item = DynamoDbManager.get_item(table_name=self.table_name,
                                        key_name=ConfigConstants.USER_ID_FIELD_NAME,
                                        key_value=user_id)

        if item is None:
            return None
        return UserAttributes.deserialize_from_json(item)
