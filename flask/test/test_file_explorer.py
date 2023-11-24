from .test_helpers import _find_track_by_dir_and_name, TEST_MEDIA_BASE_PATH
import pytest
from FileExplorer import BasePathInvalid, FileExplorer
import pprint
pp = pprint.PrettyPrinter(indent=4)

# misophonia_folder_id = "b4f1020c48a28b3cdf6be408c4f585d7"
# synthesia_folder_id = "3eb6e775e805ceae25d1a654de85c467"
# tales_of_bath_folder_id = "494c2af90288e87f304b0e2a3e37d65d"
# nested_child_folder_id = "67d9a9462e356166ea6337505a1af6e7"


def equal_dicts(a, b, ignore_keys=['ModTime']):
    ka = set(a).difference(ignore_keys)
    kb = set(b).difference(ignore_keys)
    return ka == kb and all(a[k] == b[k] for k in ka)

def path_from_base(after_base_path):
    return TEST_MEDIA_BASE_PATH + after_base_path


@pytest.mark.file_explorer
class TestFileExplorer:

    def test_returns_directories_in_base_path(self):
        file_explorer = FileExplorer(TEST_MEDIA_BASE_PATH)
        (track_array, _,) = file_explorer.contents_by_directory_id(None)

        expected_track_list = [   
            {   'AbsolutePath': './pytest_faux_usb/tracks/Directory1',
                'ID': '1fbd46d2a566fa9390d277b938cdbb35',
                'IsDir': True,
                'MimeType': 'inode/directory',
                'ModTime': '2023-11-24T17:02:46.639549Z',
                'Name': 'Directory1',
                'Path': 'Directory1',
                'Size': -1},
            {   'AbsolutePath': './pytest_faux_usb/tracks/Directory2',
                'ID': '09f8710c74c84574e79791fa77d27962',
                'IsDir': True,
                'MimeType': 'inode/directory',
                'ModTime': '2023-11-24T17:02:51.387548Z',
                'Name': 'Directory2',
                'Path': 'Directory2',
                'Size': -1},
            {   'AbsolutePath': './pytest_faux_usb/tracks/Directory3',
                'ID': '44b05267942fe255a5411df90900eaea',
                'IsDir': True,
                'MimeType': 'inode/directory',
                'ModTime': '2023-11-24T17:02:54.471548Z',
                'Name': 'Directory3',
                'Path': 'Directory3',
                'Size': -1},
            {   'AbsolutePath': './pytest_faux_usb/tracks/Misophonia',
                'ID': 'c3c4eaa9777371a9dcae8b9369a1b276',
                'IsDir': True,
                'MimeType': 'inode/directory',
                'ModTime': '2023-11-24T17:02:44.195550Z',
                'Name': 'Misophonia',
                'Path': 'Misophonia',
                'Size': -1},
            {   'AbsolutePath': './pytest_faux_usb/tracks/NestedParent',
                'ID': 'a588647644e09988a154d4b69ccdbae7',
                'IsDir': True,
                'MimeType': 'inode/directory',
                'ModTime': '2023-10-22T22:21:44.062630Z',
                'Name': 'NestedParent',
                'Path': 'NestedParent',
                'Size': -1},
            {   'AbsolutePath': './pytest_faux_usb/tracks/NoSrt',
                'ID': '18f6b12093f0683cb448bde7a92dd533',
                'IsDir': True,
                'MimeType': 'inode/directory',
                'ModTime': '2023-10-22T22:23:04.054606Z',
                'Name': 'NoSrt',
                'Path': 'NoSrt',
                'Size': -1},
            {   'AbsolutePath': './pytest_faux_usb/tracks/Synthesia',
                'ID': '81fe4c18906510d9cc8ae863b71fc1ab',
                'IsDir': True,
                'MimeType': 'inode/directory',
                'ModTime': '2023-07-13T21:14:15.859154Z',
                'Name': 'Synthesia',
                'Path': 'Synthesia',
                'Size': -1},
            {   'AbsolutePath': './pytest_faux_usb/tracks/Tales_of_Bath',
                'ID': 'c73339b069b62410f6ab8c7bf9a8c21a',
                'IsDir': True,
                'MimeType': 'inode/directory',
                'ModTime': '2023-10-22T23:06:45.981802Z',
                'Name': 'Tales_of_Bath',
                'Path': 'Tales_of_Bath',
                'Size': -1}
        ]

        for i in range(len(track_array)):
            assert equal_dicts(track_array[i], expected_track_list[i])

    def test_returns_track_by_id_nested(self):
        # NOTE - 23_Renaissance has nested tracks...
        file_explorer = FileExplorer(TEST_MEDIA_BASE_PATH)

        nested_track_id = "ed5db02bfac60ee5c50d577e22ebbb4d"

        (track, path_to_track, path_to_srt) = file_explorer.track_by_track_id(
            nested_track_id)

        expected_track = {'ID': 'ed5db02bfac60ee5c50d577e22ebbb4d',
                          'IsDir': False,
                          'MimeType': 'video/mp4',
                          'ModTime': '2023-07-13T19:20:02.000000Z',
                          'Name': 'ff-16b-2c-nested.mp4',
                          'Path': 'ff-16b-2c-nested.mp4',
                          'AbsolutePath': './pytest_faux_usb/tracks/NestedParent/NestedChild/ff-16b-2c-nested.mp4',
                          'Size': 3079106}

        expected_track_path = path_from_base("NestedParent/NestedChild/ff-16b-2c-nested.mp4")
        expected_srt_path = path_from_base("NestedParent/NestedChild/ff-16b-2c-nested.srt")

        print("****** test results")
        pp.pprint(track)
        print("audio = ", path_to_track)
        print("srt = ", path_to_srt)

        assert equal_dicts(track, expected_track)
        assert path_to_track == expected_track_path
        assert path_to_srt == expected_srt_path

    def test_returns_tracklist_by_dir_id_misophonia(self):
        _, misophonia_folder_id, _ = _find_track_by_dir_and_name("Misophonia", "misophonia.mp4")

        file_explorer = FileExplorer(TEST_MEDIA_BASE_PATH)

        (NEW_TRACK_ARRAY, NEW_SRT_ARRAY) = file_explorer.contents_by_directory_id(
            misophonia_folder_id)

        misophonia_audio = [{'ID': 'ce7efe69cdda0feea71e8cafbffad0ed',
                             'IsDir': False,
                                'MimeType': 'video/mp4',
                                'ModTime': '2023-05-24T19:53:06.000000Z',
                                'Name': 'misophonia.mp4',
                                'Path': 'misophonia.mp4',
                                'AbsolutePath': './pytest_faux_usb/tracks/Misophonia/misophonia.mp4',
                                'Size': 3079106}]

        misophonia_srt = [{'ID': '3f664bdfd41cc1c12ecba85970ef5b46',
                           'IsDir': False,
                                 'MimeType': 'application/octet-stream',
                                 'ModTime': '2023-05-24T19:49:22.000000Z',
                                 'Name': 'misophonia.srt',
                                 'Path': 'misophonia.srt',
                                 'AbsolutePath': './pytest_faux_usb/tracks/Misophonia/misophonia.srt',
                                 'Size': 3658}]

        assert equal_dicts(NEW_TRACK_ARRAY[0], misophonia_audio[0])
        assert equal_dicts(NEW_SRT_ARRAY[0], misophonia_srt[0])

    def test_returns_tracklist_by_dir_id_synthesia(self):
        _, synthesia_folder_id, _ = _find_track_by_dir_and_name("Synthesia", "synthesia.mp4")

        file_explorer = FileExplorer(TEST_MEDIA_BASE_PATH)

        (NEW_TRACK_ARRAY, NEW_SRT_ARRAY) = file_explorer.contents_by_directory_id(
            synthesia_folder_id)

        synthesia_audio = [{'ID': '080d8570f31c80b8c788343d1d7f45d0',
                            'IsDir': False,
                            'MimeType': 'video/mp4',
                            'ModTime': '2023-05-24T19:53:17.000000Z',
                            'Name': 'synthesia.mp4',
                            'Path': 'synthesia.mp4',
                            'AbsolutePath': './pytest_faux_usb/tracks/Synthesia/synthesia.mp4',
                            'Size': 3079106}]

        synthesia_srt = [{'ID': '2815170a245e3253801efbc03d11888e',
                          'IsDir': False,
                            'MimeType': 'application/octet-stream',
                            'ModTime': '2023-05-24T19:49:22.000000Z',
                            'Name': 'synthesia.srt',
                            'Path': 'synthesia.srt',
                            'AbsolutePath': './pytest_faux_usb/tracks/Synthesia/synthesia.srt',
                            'Size': 3658}]

        assert equal_dicts(NEW_TRACK_ARRAY[0], synthesia_audio[0])
        assert equal_dicts(NEW_SRT_ARRAY[0], synthesia_srt[0])

    def test_returns_tracklist_by_dir_id_tales_of_bath(self):
        _, tales_of_bath_folder_id, _ = _find_track_by_dir_and_name("Tales_of_Bath", "tales_of_bath.mp4")

        file_explorer = FileExplorer(TEST_MEDIA_BASE_PATH)

        (NEW_TRACK_ARRAY, NEW_SRT_ARRAY) = file_explorer.contents_by_directory_id(
            tales_of_bath_folder_id)

        tales_of_bath_audio = [{'ID': 'c2c6feab501e97fe85c8c000efe12aca',
                                'IsDir': False,
                                      'MimeType': 'video/mp4',
                                      'ModTime': '2023-05-24T19:53:22.000000Z',
                                      'Name': 'tales_of_bath.mp4',
                                      'Path': 'tales_of_bath.mp4',
                                      'AbsolutePath': './pytest_faux_usb/tracks/Tales_of_Bath/tales_of_bath.mp4',
                                      'Size': 3079106}]

        tales_of_bath_srt = [{'ID': '48f827ad5b63241f2403c047c30c8600',
                              'IsDir': False,
                                    'MimeType': 'application/octet-stream',
                                    'ModTime': '2023-05-24T19:49:22.000000Z',
                                    'Name': 'tales_of_bath.srt',
                                    'Path': 'tales_of_bath.srt',
                                    'AbsolutePath': './pytest_faux_usb/tracks/Tales_of_Bath/tales_of_bath.srt',
                                    'Size': 3658}]

        assert equal_dicts(NEW_TRACK_ARRAY[0], tales_of_bath_audio[0])
        assert equal_dicts(NEW_SRT_ARRAY[0], tales_of_bath_srt[0])

    def test_returns_correct_srt(self):
        tales_of_bath_second_id, _, _ = _find_track_by_dir_and_name("Tales_of_Bath", "tales_of_bath_second.mp4")

        file_explorer = FileExplorer(TEST_MEDIA_BASE_PATH)

        (track, path_to_track, path_to_srt) = file_explorer.track_by_track_id(
            tales_of_bath_second_id)

        expected_track = {
            'ID': 'd95863a0921ef12a3252888a64eeb0c7', 
            'IsDir': False,
            'MimeType': 'video/mp4',
            'ModTime': '2023-10-22T22:20:27.278652Z', 
            'Name': 'tales_of_bath_second.mp4', 
            'Path': 'tales_of_bath_second.mp4',
            'AbsolutePath': './pytest_faux_usb/tracks/Tales_of_Bath/tales_of_bath_second.mp4', 
            'Size': 3079106}

        expected_path_to_track = path_from_base("Tales_of_Bath/tales_of_bath_second.mp4")
        expected_path_to_srt = path_from_base("Tales_of_Bath/tales_of_bath_second.srt")

        assert equal_dicts(track, expected_track)
        assert path_to_track == expected_path_to_track
        assert path_to_srt == expected_path_to_srt
        
    def test_returns_directory_list_by_dir_id_nested(self):
        file_explorer = FileExplorer(TEST_MEDIA_BASE_PATH)

        _, nested_parent_folder_id, _ = _find_track_by_dir_and_name("NestedParent", None)

        (NEW_TRACK_ARRAY, NEW_SRT_ARRAY) = file_explorer.contents_by_directory_id(
            nested_parent_folder_id)

        expected_dir_array = [   
        {   'AbsolutePath': './pytest_faux_usb/tracks/NestedParent/NestedChild',
        'ID': 'e80a5659937d260ff3154047e26fdc3c',
        'IsDir': True,
        'MimeType': 'inode/directory',
        'ModTime': '2023-07-13T20:20:25.889602Z',
        'Name': 'NestedChild',
        'Path': 'NestedChild',
        'Size': -1},
        {   'AbsolutePath': './pytest_faux_usb/tracks/NestedParent/SecondNestedChild',
            'ID': '373799e337df1cde57a62f8f19ea16a0',
            'IsDir': True,
            'MimeType': 'inode/directory',
            'ModTime': '2023-10-22T22:22:01.138625Z',
            'Name': 'SecondNestedChild',
            'Path': 'SecondNestedChild',
            'Size': -1}
        ]

        parent_srt_array = []

        for i in range(len(expected_dir_array)):
            assert equal_dicts(NEW_TRACK_ARRAY[i], expected_dir_array[i])

        assert parent_srt_array == NEW_SRT_ARRAY

    def test_returns_correct_path_duplicate_filename(self):
        dir1_track_id, _, dir1_track_absolute_path = _find_track_by_dir_and_name("Directory1", "misophonia.mp4")
        dir2_track_id, _, dir2_track_absolute_path = _find_track_by_dir_and_name("Directory2", "misophonia.mp4")
        dir3_track_id, _, dir3_track_absolute_path = _find_track_by_dir_and_name("Directory3", "misophonia.mp4")

        id_list = [dir1_track_id, dir2_track_id, dir3_track_id]
        path_list = [dir1_track_absolute_path, dir2_track_absolute_path, dir3_track_absolute_path]

        expected_path_list = [
            './pytest_faux_usb/tracks/Directory1/misophonia.mp4',
            './pytest_faux_usb/tracks/Directory2/misophonia.mp4',
            './pytest_faux_usb/tracks/Directory3/misophonia.mp4'
        ]

        print("path_list = ", path_list)

        assert path_list == expected_path_list
        assert len(set(id_list)) == 3
