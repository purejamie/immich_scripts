# Immich Scripts
A set of helper scripts written to help with the import and management of large photo collections.

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


3. Work through the pictures in the new album, and name any faces which should be named. For example, I have pictures of my kids playing football, so I name the kids, leaving the crowd unnamed. 

4. Once you have the faces named, run the script again with the `--album-id` flasg (using the UUID from previous step) to hide the faces which aren't named.

    ```
    python3 hide_faces_in_picture.py --album-id <album-id>
    ```


> [!TIP]
> If you want to ignore certain pictures, you can use the `--ignore-assets` flag to specify a comma-separated list of asset IDs to ignore. This was for an edge case where I had a few photos with elderly relatives I didn't know the names of, but also didn't want to hide. 