"""DynamoDb Manager - central handler for all DDB communication."""
from time import sleep

import boto3
import decimal
from typing import List, Dict, Set, Optional, Any
from boto3.dynamodb.conditions import Key


from taco_config_constants import ConfigConstants

class DynamoDbManager(object):
    """
    This class is a utility for interacting with DynamoDB.
    Get or put operations will ensure tables exist and create them if necessary.
    Copied from https://code.amazon.com/packages/AlexaMoviebot/blobs/mainline/--/lib/alexa_moviebot/dynamodb_manager.py
    """

    #warning region is left to aws credential defaults
    _resource = boto3.resource('dynamodb')
    _client = boto3.client('dynamodb')


    # A set of table names that have been validated
    _checked_tables: Set[str] = set()

    @classmethod
    def get_item(cls, table_name: str, key_name: str, key_value: str) -> Optional[Any]:
        """
        Retrieve the specified key_name=key_value from the table.
        Returns None if item is not found, or the Item object (dictionary) if it is.
        """
        table = cls._get_table(table_name)
        item_response = table.get_item(
            Key={
                key_name: key_value
            }
        )

        if 'Item' in item_response:
            return item_response['Item']
        else:
            return None

    @classmethod
    def has_gsi(cls, table_name: str, index_name: str) -> bool:
        """
        Check GSI existence. Return True if it exists, otherwise return False.
        """
        response = cls._client.describe_table(
            TableName=table_name
        )

        for gsi in response['Table'].get('GlobalSecondaryIndexes', []):
            if gsi['IndexName'] == index_name:
                return True
        return False

    @classmethod
    def put_item(cls, table_name: str, item_dict: dict) -> None:
        """
        Pushes the item to DynamoDB
        """
        # DynamoDB does not support float types
        # Convert them to decimal if they exist
        item_dict = cls._fix_empty_string(item_dict)
        item_dict = cls._fix_types(item_dict)
        table = cls._get_table(table_name)
        table.put_item(Item=item_dict)

    @classmethod
    def _fix_empty_string(cls, item_dict):
        """
        This is a placeholder function to loop through an item dictionary intended for use with DynamoDB and remove
        empty strings that are necessary for DynamoDB,
        otherwise it throws "An error occurred (ValidationException) when calling the PutItem operation: One or more parameter values were invalid: An AttributeValue may not contain an empty string." as of April, 2018.
        """
        item_dict_return = {}
        for key, value in item_dict.items():
            if isinstance(value, dict):
                new_value = cls._fix_empty_string(value)
                item_dict_return[key] = new_value
            elif isinstance(value, list):
                new_value = []
                for elem in value:
                    if isinstance(elem, dict):
                        new_elem = cls._fix_empty_string(elem)
                        new_value.append(new_elem)
                    elif elem is not None and elem != "":  # not None and not empty string
                        new_value.append(elem)
                item_dict_return[key] = new_value
            elif value is not None and value != "":   # not None and not empty string
                item_dict_return[key] = value

        return item_dict_return

    #TODO: only handles float, dict, or list in dict
    @classmethod
    def _fix_types(cls, item_dict: dict) -> dict:
        """
        This is a placeholder function to loop through an item dictionary intended for use with DynamoDB and convert
        some python types to types that are necessary for DynamoDB. Currently the only example of this is that python
        float values must be converted to Decimal as there is a mismatch in precision between the two systems.
        """
        item_dict_return = item_dict.copy()
        for key, value in item_dict.items():
            if isinstance(value, float):
                item_dict_return[key] = cls._fix_types_for_float(value)
            elif isinstance(value, dict):
                item_dict_return[key] = cls._fix_types(value)
            elif isinstance(value, list):
                for idx, elem in enumerate(value):
                    if isinstance(elem, dict):
                        new_elem = cls._fix_types(elem)
                        value[idx] = new_elem
                    elif isinstance(elem, float):
                        value[idx] = DynamoDbManager._fix_types_for_float(elem)
        return item_dict_return

    @classmethod
    def _fix_types_for_float(cls, item_float: float) -> decimal.Decimal:
        """
        This is a placeholder function to loop through an item dictionary intended for use with DynamoDB and convert
        some python types to types that are necessary for DynamoDB. Currently the only example of this is that python
        float values must be converted to Decimal as there is a mismatch in precision between the two systems.
        """
        if isinstance(item_float, float):
            item_result = decimal.Decimal(str(item_float))
        else:
            item_result = item_float

        return item_result

    @classmethod
    def query(cls, 
            table_name: str,
            key_condition: dict,
            index_name: Optional[str] = None,
            expression_attribute_values_dict: Optional[dict] = None,
            scan_index_forward: bool=None,
            limit: int=None
        ) -> list:
        """
        Query the given table_name with the supplied key condition and optional index name.
        """

        # Passing None or empty string for index_name results in an error. So we need to manually construct the argument
        # dictionary and unpack it when calling hte query function.
        arg_dict: Dict[str, Any] = {
            'KeyConditionExpression': key_condition
        }

        if index_name is not None:
            arg_dict['IndexName'] = index_name

        if expression_attribute_values_dict:
            arg_dict['ExpressionAttributeValues'] = expression_attribute_values_dict

        if scan_index_forward is not None:
            arg_dict['ScanIndexForward'] = scan_index_forward

        if limit is not None:
            arg_dict['Limit'] = limit

        table = cls._get_table(table_name)

        finished_querying = False
        query_data: list = []
        total_items_returned = 0
        # Perform the requests in a loop as we may hit the response limit (1MB)
        while not finished_querying:
            query_response = table.query(**arg_dict)
            query_data.extend(query_response['Items'])
            total_items_returned += query_response.get('Count', 0)
            last_evaluated_key = query_response.get('LastEvaluatedKey')
            if last_evaluated_key and (limit is None or limit > total_items_returned):
                # If the response contained a LastEvaluatedKey and we have not reached the specified limit,
                # need to perform the next query with the ExclusiveStartKey set to that key.
                arg_dict['ExclusiveStartKey'] = last_evaluated_key
            else:
                finished_querying = True

        return query_data

    @classmethod
    def update_item(cls, 
            table_name: str,
            key_dict: dict,
            update_expression: dict,
            expression_attribute_values_dict: Optional[dict] = None,
            return_values: str = 'ALL_NEW'
        ) -> Any:
        """
        Updates the item specified by the matching key=value items in the key_dict.
        Requires an update_expression, as well as an optional dictionary of expression attribute values and/or a
        return_values expression to send to the update call.
        """
        table = cls._get_table(table_name)
        update_response = table.update_item(
            Key=key_dict,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values_dict,
            ReturnValues=return_values
        )

        return update_response['Attributes']

    @classmethod
    def _get_table(cls, table_name: str) -> Any:
        """
        This function will return a handle to a Table to perform operations on.
        """
        return cls._resource.Table(table_name)

    @classmethod
    def ensure_table_exists(cls, table_name: str, type: str) -> None:
        """
        This method will check once for each runtime/session that the given table exists. If it does not, it will create
        a table with a single string key using the given key_name.
        """
        if table_name not in cls._checked_tables:
            cls._checked_tables.add(table_name)

            table_names = cls._client.list_tables()['TableNames']
            if table_name not in table_names:
                # Table does not exist, need to create it
                print('*' * 50)
                print('Creating DynamoDB table: {}. This should happen rarely but may result in a response timeout. '
                      'Please repeat the request to try again after it times out.'.format(table_name))
                print('*' * 50)

                table_definition_dict = ConfigConstants.TABLE_DEFINITIONS[type]
                table = cls._resource.create_table(
                    TableName=table_name,
                    **table_definition_dict
                )

                # Wait until the table exists.
                table.meta.client.get_waiter('table_exists').wait(TableName=table_name)

    """ Called by the ABTest class to save the test config in a batch. """
    @classmethod
    def put_items(cls, table_name: str, item_dict_list: list) -> None:
        table = cls._get_table(table_name)

        with table.batch_writer() as batch:
            for item_dict in item_dict_list:
                item_dict = cls._fix_empty_string(item_dict)
                item_dict = cls._fix_types(item_dict)
                batch.put_item(Item=item_dict)


if __name__ == '__main__':
    item_dict = {
        'asr': [{'tokens': [{'value': "you're", 'confidence': 0.327}]},
                {'tokens': [{'value': 'your', 'confidence': 0.87}]}],
        'encoding': [0.1, 0.2]
    }
    result = DynamoDbManager._fix_types(item_dict)
    print(result)
    item_dict = {
        "session_id" : "test_session_id",
        "creation_date_time": "2018-03-28T00:48:20.704344",
        "candidate_responses": {"RULES": "", "RETRIEVAL": {"response": "usa is on strike we want moar monies\\n",
                                                           "performance": [0.06956839561462402], "error": False}},
        "RULES": "",
        "asr": [],
        "ner": ["", "person"],
        "input_offensive": 0,
        "output_offensive": False,
        "ranking": None
    }
    result = DynamoDbManager._fix_empty_string(item_dict)
    print(result)
    DynamoDbManager.put_item('StateTableBeta', item_dict)

    attribute_definitions=[
            {
                'AttributeName': 'conversation_id',
                'AttributeType': 'S'
            }
        ]

    key_schema = [{
                        "AttributeName": "conversation_id",
                        "KeyType": "HASH"
                    }]
    projection = {
                        'ProjectionType': "KEYS_ONLY"
                }

    query_result = DynamoDbManager.query(table_name='StateTableBeta',
                                         key_condition=
                                         Key('session_id').eq("SessionId.f37c8cce-ac01-43bf-bdb9-9c45748482cf"),
                                         scan_index_forward=False)
    print(query_result)


