import requests
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
from common import test_connection, create_album, get_assets_from_album
import json

def parse_args():
    parser = argparse.ArgumentParser(description='Get person ID from Immich by name')
    parser.add_argument('--name', type=str, required=True, help='Name of the person to look up')
    parser.add_argument('--number-faces', type=str, default=20, help='The number of similar faces to add to album (Default: 20)')
    parser.add_argument('--album-id', type=str, default=None, help='The ID of the album containing faces to rename')
    return parser.parse_args()

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

def get_similar_faces(server_address: str, api_key: str, person_id: str) -> list[str]:
    """Retrieve the similar faces for a person using the Immich API."""
    search_url = f"{server_address}/api/people?closestPersonId={person_id}&withHidden=false"

    headers = {
        'x-api-key': api_key,
        'Accept': 'application/json'
    }

    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        return response.json()  
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve similar faces: {e}")
        return []

def get_similar_asset_ids(server_address: str, api_key: str, person_id: str, person_name: str, similar_faces: list[str], number_faces: int) -> None:
    search_url = f"{server_address}/api/search/metadata"
    similar_asset_ids = []
    #if there are less similar faces than the number we want, set the number to the number of faces
    if len(similar_faces['people']) < number_faces:
        number_faces = len(similar_faces['people'])

    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    for i in range(number_faces + 1):
        if similar_faces['people'][i]['id'] != person_id:
            payload = json.dumps({
                "personIds": [similar_faces['people'][i]['id']]
            })

            response = requests.post(search_url, headers=headers, data=payload)
            response.raise_for_status()

            similar_asset_ids.append({
                "faceId": similar_faces['people'][i]['id'],
                "assetId": response.json()['assets']['items'][0]['id']
            })

    return similar_asset_ids

def main():
    args = parse_args()
    
    immich_creds = test_connection()
    if not immich_creds:
        print("Failed to retrieve credentials.")
        return

    person_id = get_person_id(immich_creds["IMMICH_SERVER_ADDRESS"], immich_creds["IMMICH_API_KEY"], args.name)
    if person_id:
        print(f"Person ID for {args.name}: {person_id}")
    else:
        print(f"Could not find person ID for {args.name}")
    
    #if no album ID is provided, create a new album with face similarity
    if not args.album_id:
        similar_faces = get_similar_faces(immich_creds["IMMICH_SERVER_ADDRESS"], immich_creds["IMMICH_API_KEY"], person_id)
        similar_asset_ids = get_similar_asset_ids(immich_creds["IMMICH_SERVER_ADDRESS"], immich_creds["IMMICH_API_KEY"], person_id, args.name, similar_faces, int(args.number_faces))  
        
        if similar_asset_ids:
            album_id = create_album(
                            immich_creds["IMMICH_SERVER_ADDRESS"], 
                            immich_creds["IMMICH_API_KEY"], 
                            [asset['assetId'] for asset in similar_asset_ids],
                            f"Similar faces to {args.name}", 
                            f"Automatically created album containing pictures with similar faces to {args.name}")

        print(f"Album ID: {album_id}")


    test = get_assets_from_album(immich_creds["IMMICH_SERVER_ADDRESS"], immich_creds["IMMICH_API_KEY"], args.album_id)
    print(test)

if __name__ == "__main__":
    main()