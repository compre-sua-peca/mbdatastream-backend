import boto3
import os
from botocore.exceptions import NoCredentialsError
from boto3.dynamodb.types import TypeDeserializer

class DynamoSingleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            instance = super(DynamoSingleton, cls).__new__(cls)
            
            instance.client = boto3.client(
                'dynamodb',
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                region_name=os.environ.get('AWS_REGION_NAME')
            )
            cls._instance = instance
        
        return cls._instance
    
    def get_item_by_hash_key(self, table_name, hash_key_name, hash_key_value):
        """
        Retrieves an item from the specified DynamoDB table using the provided hash key.
        Assumes the key attribute type is a string. Modify the type accordingly if needed.
        
        :param table_name: Name of the DynamoDB table.
        :param hash_key_name: Name of the hash key attribute.
        :param hash_key_value: Value for the hash key (assumed to be a string).
        :return: The item if found, otherwise None.
        """
        
        try:
            response = self.client.get_item(
                TableName=table_name,
                Key={
                    hash_key_name: {"S": hash_key_value}
                }
            )
            
            raw_item = response.get("Item")
            
            if raw_item:
                deserializer = TypeDeserializer()
                
                item = {k: deserializer.deserialize(v) for k, v in raw_item.items()}
                return item
            
            return None
        
        except NoCredentialsError:
            print("Credentials not available")
            
            return None
        
        except Exception as e:
            print(f"Error retrieving item: {e}")
            
            return None