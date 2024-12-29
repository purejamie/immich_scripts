from common import test_connection
from sqlalchemy import create_engine, Column, String, Boolean, ForeignKey, case
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy import func
from urllib.parse import quote_plus
import argparse
import requests
import json
from datetime import datetime

Base = declarative_base()

def parse_args():
    parser = argparse.ArgumentParser(description='Process faces in Immich')
    parser.add_argument('--face-count', type=int, default=20,
                       help='Minimum number of faces to look for (default: 20)')
    parser.add_argument('--album-id', type=str,
                       help='Album ID to process for hiding unnamed faces')
    return parser.parse_args()

class Person(Base):
    __tablename__ = 'person'
    
    id = Column('id', String, primary_key=True)
    isHidden = Column('isHidden', Boolean)
    name = Column('name', String)

class AssetFace(Base):
    __tablename__ = 'asset_faces'
    
    assetId = Column('assetId', String, primary_key=True)
    personId = Column('personId', String, ForeignKey('person.id'))

class AlbumAsset(Base):
    __tablename__ = 'albums_assets_assets'
    
    albumsId = Column('albumsId', String, primary_key=True)
    assetsId = Column('assetsId', String, primary_key=True)
    createdAt = Column('createdAt', String)

immich_creds = test_connection()

def find_assets_with_faces(session, min_face_count):
    """Find assets that have at least min_face_count unhidden faces."""
    query = (
        session.query(
            AssetFace.assetId,
            func.count().label('face_count'),
            func.sum(case((Person.isHidden == True, 1), else_=0)).label('hidden_count')
        )
        .join(Person, AssetFace.personId == Person.id)
        .filter(Person.name == '')  # Ignore faces that are already named
        .group_by(AssetFace.assetId)
        .having(
            func.count() - func.sum(case((Person.isHidden == True, 1), else_=0)) >= min_face_count
        )
    )
    
    results = query.all()
    print(f"Found {len(results)} assets with {min_face_count} or more unhidden faces")
    for row in results:
        unhidden_faces = row[1] - (row[2] or 0)
        print(f"Asset {row[0]}: {row[1]} total faces, {row[2]} hidden faces, {unhidden_faces} unhidden faces")
    
    return [row[0] for row in results]

def create_album(server_address, api_key, asset_ids, face_count):
    """Create an album in Immich with the given assets."""
    album_url = f"{server_address}/api/albums"
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    payload = json.dumps({
        "albumName": f"Pictures with {face_count} or more unhidden faces",
        "assetIds": [str(id) for id in asset_ids],
        "description": f"Automatically created album containing pictures with {face_count} or more unhidden faces"
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

def hide_unnamed_faces(session, album_id):
    """Hide all faces in the album that are not named."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    failures_file = f"failed_faces_{timestamp}.txt"
    failures = []
    faces_hidden = 0
    faces_skipped = 0

    query = (
        session.query(AlbumAsset.assetsId)
        .filter(AlbumAsset.albumsId == album_id)
    )
    
    album_assets = query.all()
    print(f"Found {len(album_assets)} assets in album {album_id}")
    
    for asset in album_assets:
        face_query = (
            session.query(AssetFace.personId, Person.name)
            .join(Person, AssetFace.personId == Person.id)
            .filter(AssetFace.assetId == asset[0])
        )
        
        for face, name in face_query.all():
            if name and name.strip():
                print(f"Skipping face {face} in asset {asset[0]} as it has name: {name}")
                faces_skipped += 1
                continue
                
            print(f"Hiding unnamed face {face} in asset {asset[0]}")
            
            people_url = f"{IMMICH_SERVER_ADDRESS}/api/people"
            headers = {
                'x-api-key': IMMICH_API_KEY,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            payload = json.dumps({
                "people": [
                    {
                        "id": str(face),
                        "isHidden": True
                    }
                ]
            })

            try:
                response = requests.put(people_url, headers=headers, data=payload)
                response.raise_for_status()
                print(f"Successfully hid face {face}")
                faces_hidden += 1
            except requests.exceptions.RequestException as e:
                error_msg = f"Failed to hide face {face} in asset {asset[0]}: {e}"
                print(error_msg)
                print(f"Response: {response.text if 'response' in locals() else 'No response'}")
                failures.append(error_msg)

    # Print summary
    print("\nSummary:")
    print(f"Total faces processed: {faces_hidden + faces_skipped + len(failures)}")
    print(f"Faces hidden: {faces_hidden}")
    print(f"Faces skipped (already named): {faces_skipped}")
    print(f"Faces failed to hide: {len(failures)}")

    if failures:
        with open(failures_file, 'w') as f:
            f.write(f"Failures from hide_unnamed_faces run on {timestamp}\n")
            f.write(f"Album ID: {album_id}\n")
            f.write(f"\nSummary:\n")
            f.write(f"Total faces processed: {faces_hidden + faces_skipped + len(failures)}\n")
            f.write(f"Faces hidden: {faces_hidden}\n")
            f.write(f"Faces skipped (already named): {faces_skipped}\n")
            f.write(f"Faces failed to hide: {len(failures)}\n\n")
            f.write("Detailed failures:\n")
            for failure in failures:
                f.write(f"{failure}\n")
        print(f"\nFailed to hide {len(failures)} faces. Details written to {failures_file}")
    else:
        print("\nAll faces were hidden successfully!")

if immich_creds:
    IMMICH_SERVER_ADDRESS = immich_creds["IMMICH_SERVER_ADDRESS"]
    IMMICH_API_KEY = immich_creds["IMMICH_API_KEY"]
    DB_PATH = immich_creds["DB_PATH"]
    DB_USERNAME = immich_creds["DB_USERNAME"]
    DB_PASSWORD = quote_plus(immich_creds["DB_PASSWORD"])
    DB_NAME = immich_creds["DB_NAME"]

    args = parse_args()
    db_url = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_PATH}/{DB_NAME}"
    engine = create_engine(db_url)
    
    with Session(engine) as session:
        if args.album_id:
            # If album_id is provided, hide unnamed faces
            print(f"Processing album {args.album_id} for unnamed faces")
            hide_unnamed_faces(session, args.album_id)
        else:
            # Create new album with face detection
            asset_ids = find_assets_with_faces(session, args.face_count)
            if asset_ids:
                album_id = create_album(
                    IMMICH_SERVER_ADDRESS,
                    IMMICH_API_KEY,
                    asset_ids,
                    args.face_count
                )
        