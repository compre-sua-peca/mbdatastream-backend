import boto3
import os
from botocore.exceptions import NoCredentialsError

class S3ClientSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            instance = super(S3ClientSingleton, cls).__new__(cls)
            # Store the boto3 client in an attribute on the instance
            instance.client = boto3.client(
                's3',
                aws_access_key_id=os.environ.get('CSP_AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('CSP_AWS_SECRET_ACCESS_KEY'),
                region_name=os.environ.get('REGION_NAME')
            )
            cls._instance = instance
        return cls._instance

    def upload_image(self, file, bucket, object_name):
        try:
            # Here, file is expected to be a file-like object (or already the binary content)
            self.client.put_object(
                Bucket=bucket,
                Key=object_name,
                Body=file
            )
            print(f"Image uploaded to {bucket}/{object_name}")
            return True
        except NoCredentialsError:
            print("Credentials not available")
            return False
        except Exception as e:
            print(f"Error uploading image: {e}")
            return False

    def upload_image_from_folder(self, file_path, bucket, object_name):
        """
        Uploads an image file from disk to S3.
        :param file_path: The path to the image file on disk.
        :param bucket: The S3 bucket name.
        :param object_name: The desired S3 object key.
        :return: True if the upload succeeded, False otherwise.
        """
        try:
            with open(file_path, 'rb') as file:
                self.client.put_object(
                    Bucket=bucket,
                    Key=object_name,
                    Body=file
                )
            print(f"Image uploaded to {bucket}/{object_name}")
            return True
        except NoCredentialsError:
            print("Credentials not available")
            return False
        except Exception as e:
            print(f"Error uploading image: {e}")
            return False
