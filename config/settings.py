import os
from dotenv import load_dotenv

load_dotenv(override=True)

print(os.environ.get('AWS_DATABASE_URL'))

class Config:
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('AWS_DATABASE_URL')
