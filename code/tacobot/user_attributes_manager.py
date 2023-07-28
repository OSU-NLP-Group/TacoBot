from tacobot.user_attributes import UserAttributes


class UserAttributesManager:
    def __init__(self, user_attributes=None):
        self.user_attributes = user_attributes
        self.persistence_enabled = False

    def persistence_enabled(self):
        return self.user_attributes is not None

# To do
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
        DynamoDbManager.put_item(table_name=self.user_attributes, item_dict=item_dict)


    def retrieve_user_attributes(self, user_id: str) -> UserAttributes:
        """
        Retrieves and deserialize to a UserAttribute object for the given user id. Return None if there is no item found in DynamoDB for the given user id.
        :param user_id: user id
        :return: UserAttributes object
        """
        item = DynamoDbManager.get_item(table_name=self.user_attributes,
                                        key_name=ConfigConstants.USER_ID_FIELD_NAME,
                                        key_value=user_id)

        if item is None:
            return None
        return UserAttributes.deserialize_from_json(item)