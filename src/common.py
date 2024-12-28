import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file in the parent directory
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)

# Get Immich server address and API key from environment variables
IMMICH_SERVER_ADDRESS = os.getenv('IMMICH_SERVER_ADDRESS')
IMMICH_API_KEY = os.getenv('IMMICH_API_KEY')

if not IMMICH_SERVER_ADDRESS or not IMMICH_API_KEY:
    raise ValueError("IMMICH_SERVER_ADDRESS and IMMICH_API_KEY must be set in the .env file")

def test_connection():
    url = f"{IMMICH_SERVER_ADDRESS}/api/server/about" 
    headers = {
        'x-api-key': f'{IMMICH_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print("Connection to Immich API successful!")
        # print("Response:", response.json())
        return {
            "IMMICH_SERVER_ADDRESS": IMMICH_SERVER_ADDRESS,
            "IMMICH_API_KEY": IMMICH_API_KEY
        }
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print("Please check the server address and API key in the .env file")
    except Exception as err:
        print(f"Other error occurred: {err}")