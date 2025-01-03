import os
import requests
from dotenv import load_dotenv
import psycopg2
import json


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

def create_album(server_address, api_key, asset_ids, album_name, album_description):
    """Create an album in Immich with the given assets."""
    album_url = f"{server_address}/api/albums"
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    payload = json.dumps({
        "albumName": album_name,
        "assetIds": [str(id) for id in asset_ids],
        "description": album_description
    })

    try:
        response = requests.post(album_url, headers=headers, data=payload)
        response.raise_for_status()
        album_data = response.json()
        print(f"Album created successfully with {len(asset_ids)} assets")
        print(f"Album ID: {album_data['id']}")
        return album_data['id']  # Return just the ID string, not a set
    except requests.exceptions.RequestException as e:
        print(f"Failed to create album: {e}")
        print(f"Response: {response.text if 'response' in locals() else 'No response'}")
        return None

def get_assets_from_album(server_address, api_key, album_id):
    album_url = f"{server_address}/api/albums/{album_id}"
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    try:
        response = requests.get(album_url, headers=headers)
        response.raise_for_status()
        return [asset['id'] for asset in response.json()['assets']]
    except requests.exceptions.RequestException as e:
        print(f"Failed to get assets from album: {e}")
        return None

def get_person_id(server_address: str, api_key: str, person_name: str) -> str:
    """Retrieve the person ID by name using the Immich API."""
    search_url = f"{server_address}/api/search/person?name={person_name}"
    
    headers = {
        'x-api-key': api_key,
        'Accept': 'application/json'
    }

    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        person = response.json()
        
        if len(person) > 1:
            print(f"Found multiple people with the name: {person_name}")
            return ""
        else: return person[0]['id']
        
        print(f"No person found with the name: {person_name}")
        return ""
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve person data: {e}")
        print(f"Response: {response.text if 'response' in locals() else 'No response'}")
        return ""

def merge_person(server_address: str, api_key: str, main_person_id: str, similar_person_id: str) -> bool:
    """Merge a similar person into the main person using the Immich API."""
    merge_url = f"{server_address}/api/people/{main_person_id}/merge"
    
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    payload = json.dumps({
        "ids": [similar_person_id]
    })
    try:
        response = requests.post(merge_url, headers=headers, data=payload)
        response.raise_for_status()
        print(f"Successfully merged person ID {similar_person_id} into {main_person_id}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to merge person ID {similar_person_id} into {main_person_id}: {e}")
        print(f"Response: {response.text if 'response' in locals() else 'No response'}")
        return False