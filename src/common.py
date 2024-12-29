import os
import requests
from dotenv import load_dotenv
import psycopg2

# Load environment variables from .env file in the parent directory
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)

# Get Immich server address and API key from environment variables
IMMICH_SERVER_ADDRESS = os.getenv('IMMICH_SERVER_ADDRESS')
IMMICH_API_KEY = os.getenv('IMMICH_API_KEY')
DB_PATH = os.getenv('DB_PATH')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
IMMICH_USER_ID = os.getenv('IMMICH_USER_ID')

if not all([DB_PATH, DB_USERNAME, DB_PASSWORD, IMMICH_SERVER_ADDRESS, IMMICH_API_KEY, DB_NAME]):
    raise ValueError("DB_PATH, DB_USERNAME, DB_PASSWORD, IMMICH_SERVER_ADDRESS, IMMICH_API_KEY, DB_NAME must be set in the .env file")

def test_connection():
    # Test Immich connection
    immich_url = f"{IMMICH_SERVER_ADDRESS}/api/server/about" 
    immich_headers = {
        'x-api-key': f'{IMMICH_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    credentials = {}
    connection_success = True

    # Test Immich API
    try:
        response = requests.get(immich_url, headers=immich_headers)
        response.raise_for_status()
        print("Connection to Immich API successful!")
        credentials.update({
            "IMMICH_SERVER_ADDRESS": IMMICH_SERVER_ADDRESS,
            "IMMICH_API_KEY": IMMICH_API_KEY,
        })
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print("Please check the server address and API key in the .env file")
        connection_success = False
    except Exception as err:
        print(f"Other error occurred: {err}")
        connection_success = False

    # Test PostgreSQL connection
    try:
        conn = psycopg2.connect(
            host=DB_PATH,
            database=DB_NAME,
            user=DB_USERNAME,
            password=DB_PASSWORD
        )
        conn.close()
        print("Connection to PostgreSQL database successful!")
        credentials.update({
            "DB_PATH": DB_PATH,
            "DB_USERNAME": DB_USERNAME,
            "DB_PASSWORD": DB_PASSWORD,
            "DB_NAME": DB_NAME
        })
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        print("Please check the database credentials in the .env file")
        connection_success = False

    return credentials if connection_success else None
