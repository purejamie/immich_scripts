from common import test_connection

immich_creds = test_connection()

if immich_creds:
    IMMICH_SERVER_ADDRESS = immich_creds["IMMICH_SERVER_ADDRESS"]
    IMMICH_API_KEY = immich_creds["IMMICH_API_KEY"]

print("hello")