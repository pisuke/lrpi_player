from FileExplorer import BasePathInvalid, FileExplorer

# TEST_MEDIA_BASE_PATH = "/opt/code/flask/test/pytest_faux_usb/tracks/"
TEST_MEDIA_BASE_PATH = "./pytest_faux_usb/tracks/"

def _find_track_by_dir_and_name(dir_name, track_name):
    """
        V simple helper for testing only, all track finding should
        be done by directory / folder id only. This helps keep
        the tablet ui code as simple as possible

        Note: helper doesn't work for nested folders
    """
    file_explorer = FileExplorer(TEST_MEDIA_BASE_PATH)
    (root_track_array, _,) = file_explorer.contents_by_directory_id(None)

    print("**** searching for dir_name: ", dir_name)

    dir_id = None

    for dir in root_track_array:
        if dir["Path"] == dir_name:
            dir_id = dir["ID"]
            break

    print("*** found dir_id : ", dir_id)

    (track_array, _,) = file_explorer.contents_by_directory_id(dir_id)

    track_id = None
    track_absolute_path = None

    for track in track_array:
        if track["Name"] == track_name:
            track_id = track["ID"]
            track_absolute_path = track["AbsolutePath"]
            break

    # print("root : ", root_track_array)
    # print("track_array : ", track_array)
    print("*** found track_id : ", track_id)

    return track_id, dir_id, track_absolute_path