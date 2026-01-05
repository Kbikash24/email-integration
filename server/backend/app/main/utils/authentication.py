import firebase_admin
from firebase_admin import credentials, firestore
from google.oauth2 import service_account
from google.cloud import bigquery, storage
from sqlalchemy import create_engine
import json

environment = "development"  # Change to "production" as needed

if environment == "production":
    file_path = 'app/main/files/bigquery-prod.json'
    file_path_firebase = file_path
    storage_client = storage.Client.from_service_account_json(file_path)
    storage_bucket = "instagram-345102.appspot.com"
    bucket = storage_client.get_bucket('vedasis-images')

if environment == "development":
    file_path = 'app/main/files/service_account_dev.json'
    file_path_firebase = 'app/main/files/firebase_dev.json'
    storage_client = storage.Client.from_service_account_json('app/main/files/service_account_dev.json')
    storage_bucket = "firebase-345106.appspot.com"
    bucket = storage_client.get_bucket('vedasis-images-dev')

with open(file_path, "r") as file:
        data = json.load(file)
credentials_gcp = service_account.Credentials.from_service_account_file(file_path)
client = bigquery.Client.from_service_account_json(file_path)
cred = credentials.Certificate(file_path_firebase)
gemini_api_key = data.get("gemini_api_key")

if environment == "production":
    DATABASE_URL = "postgresql+psycopg2://postgres:{}@{}/vhub".format(data['pg_password'], data['pg_host'])
    
if environment == "development":
    DATABASE_URL = "postgresql+psycopg2://postgres:{}@{}/postgres".format(data['pg_password'], data['pg_host'])

engine = create_engine(DATABASE_URL)

firebase_admin.initialize_app(cred, {'storageBucket': storage_bucket})
db = firestore.client()