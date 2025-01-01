# Immich Scripts
A set of helper scripts written to help with the import and management of large photo collections.

> [!WARNING]
> Use these scripts at your own risk - I've written them for my own use, and while they've worked for me, I can't guarantee they'll work for you.
> If you find these useful, and find a bug/improvement, open an issue. 

## hide_faces_in_picture.py
This script does two things:
- creates albums containing pictures with a large number of unhidden faces (configurable)
- hides faces in the created albums that don't have names 

The workflow for this script:

1. Use the env file to set up immich credentials (example in root folder) and ensure the dependancies are installed.

2. Run the script with the `--face-count` flag **only** to create albums containing pictures with a large number of unhidden faces which aren't named. The number of faces is configurable (default is 10).

    ```
    python3 hide_faces_in_picture.py --face-count 20
    ```

    This will create an album named **_Pictures with x or more unhidden faces_** where x is the number of faces.

    The script will output a summary and the UUID of the newly created album (this can also be found in the album URL in Immich).


3. Work through the pictures in the new album, and name any faces which should be named. For example, I have pictures of my kids playing football, so I name the kids, leaving the crowd unnamed. You can also just remove photos from the album if you don't want them to be processed.

4. Once you have the faces named, run the script again with the `--album-id` flasg (using the UUID from previous step) to hide the faces which aren't named.

    ```
    python3 hide_faces_in_picture.py --album-id <album-id>
    ```

#### Commandline flags

| Flag | Description | Example |
|------|-------------|---------|
| `--face-count` | Creates an album containing pictures with at least this many unhidden faces | `--face-count 20` |
| `--album-id` | The UUID of the album to process for hiding unnamed faces | `--album-id 123e4567-e89b-12d3-a456-426614174000` |
| `--ignore-assets` | Comma-separated list of asset IDs to skip during processing | `--ignore-assets abc123,def456` |


