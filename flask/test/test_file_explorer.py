import pytest
from FileExplorer import BasePathInvalid, FileExplorer
import pprint
pp = pprint.PrettyPrinter(indent=4)

misophonia_folder_id = "b4f1020c48a28b3cdf6be408c4f585d7"
synthesia_folder_id = "3eb6e775e805ceae25d1a654de85c467"
tales_of_bath_folder_id = "494c2af90288e87f304b0e2a3e37d65d"
nested_child_folder_id = "67d9a9462e356166ea6337505a1af6e7"


misophonia_track_id = ""
synthesia_track_id = ""
tales_of_bath_track_id = ""
nested_track_id = "420218864c124399a0f862947b73e321"

TEST_MEDIA_BASE_PATH = "/opt/code/flask/test/pytest_faux_usb/tracks/"


def equal_dicts(a, b, ignore_keys=[]):
    ka = set(a).difference(ignore_keys)
    kb = set(b).difference(ignore_keys)
    return ka == kb and all(a[k] == b[k] for k in ka)


@pytest.mark.file_explorer
class TestFileExplorer:

    @pytest.mark.only
    def test_returns_track_by_id_nested(self):
        file_explorer = FileExplorer(TEST_MEDIA_BASE_PATH)

        (track, path_to_track, path_to_srt) = file_explorer.track_by_track_id(
            nested_track_id)

        expected_track = {'ID': '420218864c124399a0f862947b73e321',
                          'IsDir': False,
                          'MimeType': 'video/mp4',
                          'ModTime': '2023-07-13T19:20:02.000000Z',
                          'Name': 'ff-16b-2c-nested.mp4',
                          'Path': 'ff-16b-2c-nested.mp4',
                          'Size': 3079106}

        expected_track_path = "/opt/code/flask/test/pytest_faux_usb/tracks/NestedParent/NestedChild/ff-16b-2c-nested.mp4"
        expected_srt_path = "/opt/code/flask/test/pytest_faux_usb/tracks/NestedParent/NestedChild/ff-16b-2c-nested.srt"

        print("****** test results")
        pp.pprint(track)
        print("audio = ", path_to_track)
        print("srt = ", path_to_srt)

        assert equal_dicts(track, expected_track)
        assert path_to_track == expected_track_path
        assert path_to_srt == expected_srt_path

    def test_returns_tracklist_by_dir_id_first(self):
        file_explorer = FileExplorer(TEST_MEDIA_BASE_PATH)

        (NEW_TRACK_ARRAY, NEW_SRT_ARRAY) = file_explorer.contents_by_directory_id(
            misophonia_folder_id)

        misophonia_audio = [{'ID': '48043ea26d6ab5808d271d523ca935a0',
                             'IsDir': False,
                                   'MimeType': 'video/mp4',
                                   'ModTime': '2023-05-24T19:53:06.000000Z',
                                   'Name': 'misophonia.mp4',
                                   'Path': 'misophonia.mp4',
                                   'Size': 3079106}]

        misophonia_srt = [{'ID': '811f3b7614004f4a3d6ca1c6d1ec6821',
                           'IsDir': False,
                                 'MimeType': 'application/octet-stream',
                                 'ModTime': '2023-05-24T19:49:22.000000Z',
                                 'Name': 'misophonia.srt',
                                 'Path': 'misophonia.srt',
                                 'Size': 3658}]

        assert equal_dicts(NEW_TRACK_ARRAY[0], misophonia_audio[0])
        assert equal_dicts(NEW_SRT_ARRAY[0], misophonia_srt[0])

    def test_returns_tracklist_by_dir_id_second(self):
        file_explorer = FileExplorer(TEST_MEDIA_BASE_PATH)

        (NEW_TRACK_ARRAY, NEW_SRT_ARRAY) = file_explorer.contents_by_directory_id(
            synthesia_folder_id)

        synthesia_audio = [{'ID': 'c0f0dc51fdbb1ceb74e3ee714f74b2f7',
                            'IsDir': False,
                                  'MimeType': 'video/mp4',
                                  'ModTime': '2023-05-24T19:53:17.000000Z',
                                  'Name': 'synthesia.mp4',
                                  'Path': 'synthesia.mp4',
                                  'Size': 3079106}]

        synthesia_srt = [{'ID': 'd2e273fd47a526603db4f128ab9f31bf',
                          'IsDir': False,
                                'MimeType': 'application/octet-stream',
                                'ModTime': '2023-05-24T19:49:22.000000Z',
                                'Name': 'synthesia.srt',
                                'Path': 'synthesia.srt',
                                'Size': 3658}]

        assert equal_dicts(NEW_TRACK_ARRAY[0], synthesia_audio[0])
        assert equal_dicts(NEW_SRT_ARRAY[0], synthesia_srt[0])

    def test_returns_tracklist_by_dir_id_third(self):
        file_explorer = FileExplorer(TEST_MEDIA_BASE_PATH)

        (NEW_TRACK_ARRAY, NEW_SRT_ARRAY) = file_explorer.contents_by_directory_id(
            tales_of_bath_folder_id)

        tales_of_bath_audio = [{'ID': '5409ca9a87ef6b53a4b9db27ba997a25',
                                'IsDir': False,
                                      'MimeType': 'video/mp4',
                                      'ModTime': '2023-05-24T19:53:22.000000Z',
                                      'Name': 'tales_of_bath.mp4',
                                      'Path': 'tales_of_bath.mp4',
                                      'Size': 3079106}]

        tales_of_bath_srt = [{'ID': 'ea0e1e25c7fcff4f78a8bc42cc7d4e99',
                              'IsDir': False,
                                    'MimeType': 'application/octet-stream',
                                    'ModTime': '2023-05-24T19:49:22.000000Z',
                                    'Name': 'tales_of_bath.srt',
                                    'Path': 'tales_of_bath.srt',
                                    'Size': 3658}]

        assert equal_dicts(NEW_TRACK_ARRAY[0], tales_of_bath_audio[0])
        assert equal_dicts(NEW_SRT_ARRAY[0], tales_of_bath_srt[0])

    def test_returns_tracklist_by_dir_id_nested(self):
        file_explorer = FileExplorer(TEST_MEDIA_BASE_PATH)

        (NEW_TRACK_ARRAY, NEW_SRT_ARRAY) = file_explorer.contents_by_directory_id(
            nested_child_folder_id)

        nested_audio = [{'ID': '420218864c124399a0f862947b73e321',
                         'IsDir': False,
                               'MimeType': 'video/mp4',
                               'ModTime': '2023-07-13T19:20:02.000000Z',
                               'Name': 'ff-16b-2c-nested.mp4',
                               'Path': 'ff-16b-2c-nested.mp4',
                               'Size': 3079106}]

        nested_srt = [{'ID': '3572e372b48d6e73de72fd2e0214fb58',
                       'IsDir': False,
                             'MimeType': 'application/octet-stream',
                             'ModTime': '2023-07-13T19:20:03.000000Z',
                             'Name': 'ff-16b-2c-nested.srt',
                             'Path': 'ff-16b-2c-nested.srt',
                             'Size': 3658}]

        assert equal_dicts(NEW_TRACK_ARRAY[0], nested_audio[0])
        assert equal_dicts(NEW_SRT_ARRAY[0], nested_srt[0])
