from common import test_connection
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any
import argparse
import requests
import json
import uuid

def parse_args():
    parser = argparse.ArgumentParser(description='Find similar faces in Immich')
    parser.add_argument('--name', type=str, required=True,
                       help='Name of the person to find similar faces to')
    parser.add_argument('--min-similarity', type=float, default=0.0,
                       help='Minimum similarity score (0.0 to 1.0, default: 0.0)')
    return parser.parse_args()

def create_album(server_address: str, api_key: str, asset_ids: List[str], name: str) -> str:
    """Create an album in Immich with the given assets."""
    album_url = f"{server_address}/api/albums"
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    payload = json.dumps({
        "albumName": f"{name} - similar pictures",
        "assetIds": asset_ids,
        "description": f"Automatically created album containing pictures similar to {name}"
    })

    try:
        response = requests.post(album_url, headers=headers, data=payload)
        response.raise_for_status()
        album_data = response.json()
        print(f"Album created successfully with {len(asset_ids)} assets")
        print(f"Album ID: {album_data['id']}")
        return album_data['id']
    except requests.exceptions.RequestException as e:
        print(f"Failed to create album: {e}")
        print(f"Response: {response.text if 'response' in locals() else 'No response'}")
        return None

def find_similar_faces(cur, target_name: str, target_embedding: List[float], limit: int = 1000) -> List[Dict]:
    """Find faces similar to the target embedding"""
    cur.execute("""
        WITH target_person AS (
            SELECT id 
            FROM person 
            WHERE name = %s
            LIMIT 1
        )
        SELECT 
            p.id as person_id,
            p.name as person_name,
            p."thumbnailPath" as thumbnail_path,
            1 - (fs.embedding <=> %s::vector) as cosine_similarity
        FROM face_search fs
        JOIN person p ON fs."faceId" = p."faceAssetId"
        WHERE p.name != %s
        AND p.id NOT IN (SELECT id FROM target_person)
        AND p."isHidden" = false
        ORDER BY cosine_similarity DESC
        LIMIT %s
    """, (target_name, target_embedding, target_name, limit))
    return cur.fetchall()

def get_target_face_embedding(cur, target_name: str) -> List[float]:
    """Get the face embedding for a specific person"""
    cur.execute("""
        SELECT fs.embedding
        FROM face_search fs
        JOIN person p ON fs."faceId" = p."faceAssetId"
        WHERE p.name = %s
        LIMIT 1
    """, (target_name,))
    result = cur.fetchone()
    return result['embedding'] if result else None

def get_person_assets(cur, similar_faces: List[Dict]) -> List[Dict]:
    """Get all assets associated with each similar face"""
    results = []
    for face in similar_faces:
        cur.execute("""
            SELECT 
                %s as person_id,
                %s as person_name,
                %s as thumbnail_path,
                string_to_array(string_agg(af."assetId"::text, ','), ',') as asset_ids,
                %s as cosine_similarity
            FROM asset_faces af
            WHERE af."personId" = %s
            GROUP BY af."personId"
        """, (
            face['person_id'],
            face['person_name'],
            face['thumbnail_path'],
            face['cosine_similarity'],
            face['person_id']
        ))
        result = cur.fetchone()
        if result:
            # Convert the result to a dict and ensure asset_ids are clean UUIDs
            result_dict = dict(result)
            # Clean any remaining braces or whitespace from UUIDs
            result_dict['asset_ids'] = [uuid.strip('{}').strip() for uuid in result_dict['asset_ids']]
            results.append(result_dict)
    return results

def update_asset_description(server_address: str, api_key: str, asset_id: str, person_id: str) -> bool:
    """Update the description of an asset to include the person URL, so you can see which person is similar in the picture."""
    asset_url = f"{server_address}/api/assets/{asset_id}"
    person_url = f"{server_address}/people/{person_id}"
    
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    payload = json.dumps({
        "description": person_url
    })

    try:
        response = requests.put(asset_url, headers=headers, data=payload)
        # response = requests.get(asset_url, headers=headers)
        response.raise_for_status()
        print(response.text)
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to update asset {asset_id}: {e}")
        print(f"Response: {response.text if 'response' in locals() else 'No response'}")
        return False

def create_output_json(input_name: str, face_id: str, album_name: str, album_id: str, assets: List[Dict[str, Any]]) -> None:
    """Create a JSON file with the specified structure."""
    output_data = {
        "input_person": {
            "name": input_name,
            "face_id": face_id
        },
        "album": {
            "name": album_name,
            "uuid": album_id
        },
        "assets": [
            {
                "asset_id": asset['asset_id'],
                "similar_face_id": asset['similar_face_id']
            }
            for asset in assets
        ]
    }

    # Write the output data to a JSON file
    with open(f"{input_name}_similar_faces.json", "w") as json_file:
        json.dump(output_data, json_file, indent=4)
    print(f"Output JSON file created: {input_name}_similar_faces.json")

def main():
    args = parse_args()
    
    if args.min_similarity < 0.0 or args.min_similarity > 1.0:
        print("Error: Minimum similarity must be between 0.0 and 1.0")
        return

    immich_creds = test_connection()
    if not immich_creds:
        return

    # Set up database connection using the same format as hide_faces_in_picture
    DB_USERNAME = immich_creds["DB_USERNAME"]
    DB_PASSWORD = immich_creds["DB_PASSWORD"]
    DB_PATH = immich_creds["DB_PATH"]
    DB_NAME = immich_creds["DB_NAME"]
    IMMICH_SERVER_ADDRESS = immich_creds["IMMICH_SERVER_ADDRESS"]
    IMMICH_API_KEY = immich_creds["IMMICH_API_KEY"]

    conn = None
    
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            host=DB_PATH,
            cursor_factory=RealDictCursor
        )
        
        with conn.cursor() as cur:
            target_embedding = get_target_face_embedding(cur, args.name)
            if not target_embedding:
                raise ValueError(f"No face embedding found for {args.name}")

            similar_faces = find_similar_faces(cur, args.name, target_embedding)
            results = get_person_assets(cur, similar_faces)
            
            # Sort by similarity and filter by minimum similarity
            results = [r for r in results if r['cosine_similarity'] >= args.min_similarity]
            results.sort(key=lambda x: x['cosine_similarity'], reverse=True)
            
            # Print results in the requested format
            for person in results:
                person_id = person['person_id']
                similarity = person['cosine_similarity']
                url = f"https://photos.bakernet.casa/people/{person_id}"
                print(f"{person_id}\t{url}\t{similarity:.4f}")
            
            # Collect all asset IDs and update their descriptions
            all_asset_ids = []
            for person in results:
                person_id = person['person_id']
                for asset_id in person['asset_ids']:
                    all_asset_ids.append({
                        "asset_id": asset_id,
                        "similar_face_id": person_id
                    })
                    # Update the asset description with the person URL
                    update_asset_description(
                        IMMICH_SERVER_ADDRESS,
                        IMMICH_API_KEY,
                        asset_id,
                        person_id
                    )
            
            # Create album if we have assets
            album_id = None
            if all_asset_ids:
                album_id = create_album(
                    IMMICH_SERVER_ADDRESS,
                    IMMICH_API_KEY,
                    [asset['asset_id'] for asset in all_asset_ids],
                    args.name
                )
                if album_id:
                    print(f"\nCreated album with ID: {album_id}")
            else:
                print("\nNo assets found to create album")
            
            # Create the output JSON file
            create_output_json(
                input_name=args.name,
                face_id=target_embedding,  # Assuming face_id is part of the embedding or retrieved separately
                album_name=f"{args.name} - similar pictures",
                album_id=album_id,
                assets=all_asset_ids
            )
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()