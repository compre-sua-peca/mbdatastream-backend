import os
from dotenv import load_dotenv

load_dotenv(override=True)

print(os.environ.get('AWS_DATABASE_URL'))
print(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES'))
class Config:
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('AWS_DATABASE_URL')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES'))