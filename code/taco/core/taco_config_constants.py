"""Configuration Constants - centrally located configuration."""


class ConfigConstants:

    # Configuration for storing user attributes in DynamoDB
    USER_ATTRIBUTES_TABLE_NAME = "UserAttributes"
    USER_ID_FIELD_NAME = "user_id"
    USER_ATTRIBUTE_DICT_FIELD_NAME = "map_attributes"

    # Configuration for storing state in DynamoDB
    STATE_TABLE_NAME = "State"

    # Configuration for storing AB test configurations in DynamoDB
    AB_CONFIG_TABLE_NAME = "ABConfigTable"

    USER_ATTRIBUTES_TABLE_DEFINITION = {
            "AttributeDefinitions": [
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S',
                }
            ],
            "KeySchema": [
                {
                    'AttributeName': 'user_id',
                    'KeyType': 'HASH',
                }
            ],
            "BillingMode": "PAY_PER_REQUEST"
    }

    STATE_TABLE_DEFINITION = {
        "AttributeDefinitions": [
            {
                'AttributeName': 'session_id',
                'AttributeType': 'S',
            },
            {
                'AttributeName': 'creation_date_time',
                'AttributeType': 'S',
            }
        ],
        "KeySchema": [
            {
                'AttributeName': 'session_id',
                'KeyType': 'HASH',
            },
            {
                'AttributeName': 'creation_date_time',
                'KeyType': 'RANGE',
            }
        ],
        "BillingMode": "PAY_PER_REQUEST"
    }

    AB_CONFIG_TABLE_DEFINITION = {
        "AttributeDefinitions": [
            {
                'AttributeName': 'name',
                'AttributeType': 'S',
            }
        ],
        "KeySchema": [
            {
                'AttributeName': 'name',
                'KeyType': 'HASH',
            }
        ],
        "BillingMode": "PAY_PER_REQUEST"
    }

    TABLE_DEFINITIONS = {
        'user': USER_ATTRIBUTES_TABLE_DEFINITION,
        'state': STATE_TABLE_DEFINITION,
        'ab_config': AB_CONFIG_TABLE_DEFINITION
    }


