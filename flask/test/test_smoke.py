import pytest
from Server import appFactory
import os
from time import sleep
import json
import pprint
pp = pprint.PrettyPrinter(indent=4)


@pytest.fixture()
def app():
    current_working_directory = os.getcwd()

    os.environ["LRPI_SETTINGS_PATH"] = current_working_directory + \
        "/pytest_faux_usb/settings.json"

    app = appFactory()
    app.config.update({
        "TESTING": True,
    })

    # other setup can go here

    yield app

    # clean up / reset resources here

    app.test_client().get("/stop")


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


# Note that these hashes will changed based on
# file attributes like 'last modified' etc...
known_folder_id = "b4f1020c48a28b3cdf6be408c4f585d7"
known_track_id = "420218864c124399a0f862947b73e321"

# Thanks to https://stackoverflow.com/q/10480806/8249410


def equal_dicts(a, b, ignore_keys=[]):
    ka = set(a).difference(ignore_keys)
    kb = set(b).difference(ignore_keys)
    return ka == kb and all(a[k] == b[k] for k in ka)


@pytest.mark.smoke
class TestLrpiPlayerSmokeTests:
    def test_server_starts(self, client):
        response = client.get("/status")

        # the server returns an error when it first starts
        # bad design (so far!) but this is what we expect
        assert b"1" in response.data

    def test_server_returns_tracklist(self, client):

        response = client.get("/get-track-list")

        print("____tracklist response")
        pp.pprint(response.json)

        expected_track_list = [{'ID': 'b4f1020c48a28b3cdf6be408c4f585d7',
                                'IsDir': True,
                                      'MimeType': 'inode/directory',
                                      'ModTime': '2023-07-13T19:19:56.000000Z',
                                      'Name': 'Misophonia',
                                      'Path': 'Misophonia',
                                      'Size': -1},
                               {'ID': 'c6d8fd89154161b3ff6bb02f4f42b4ee',
                                'IsDir': True,
                                'MimeType': 'inode/directory',
                                'ModTime': '2023-07-13T19:19:36.000000Z',
                                'Name': 'NestedParent',
                                'Path': 'NestedParent',
                                'Size': -1},
                               {'ID': '3eb6e775e805ceae25d1a654de85c467',
                                'IsDir': True,
                                'MimeType': 'inode/directory',
                                'ModTime': '2023-05-24T19:53:17.000000Z',
                                'Name': 'Synthesia',
                                'Path': 'Synthesia',
                                'Size': -1},
                               {'ID': '494c2af90288e87f304b0e2a3e37d65d',
                                'IsDir': True,
                                'MimeType': 'inode/directory',
                                'ModTime': '2023-05-24T19:53:22.000000Z',
                                'Name': 'Tales_of_Bath',
                                'Path': 'Tales_of_Bath',
                                'Size': -1}]

        print(expected_track_list)

        # we don't care about asserting on ModTime
        for i in range(len(expected_track_list)):
            assert equal_dicts(
                expected_track_list[i],
                response.json[i],
                ignore_keys=['ModTime']
            )

    def test_server_returns_tablet_ui(self, client):
        response = client.get("/tracks")

        assert response.status_code == 200
        assert "LushRoom Pi</title>" in str(response.data)

    def test_server_returns_status(self, client):
        client.get("/get-track-list")
        response = client.get("/status")

        expected_status = {
            'canControl': False,
            'error': 'Player is not initialized!',
            'master_ip': None,
            'mediaBasePath': 'also not bothered',
            'paired': False,
            'playerState': '',
            'playerType': 'not bothered',
            'playlist': ['not bothered'],
            'position': '',
            'slave_url': None,
            'source': '',
            'subsPath': '',
            'trackDuration': '',
            'volume': 80
        }

        print('res')
        pp.pprint(response.json)
        print('expected')
        pp.pprint(expected_status)

        assert equal_dicts(
            response.json,
            expected_status,
            ignore_keys=['playlist', 'playerType',
                         'mediaBasePath', 'source', 'subsPath'],
        )

    def test_server_plays_one_track_no_lights(self, client):
        client.get("/get-track-list")
        client.get("/get-track-list?id=" + known_folder_id)

        client.get("/play-single-track?id=" + known_track_id)

        sleep(4)

        status_response = client.get("/status")

        status_response = status_response.json

        pp.pprint(status_response)

        assert status_response['canControl'] == True
        assert status_response['playerState'] == 'Playing'
        assert status_response['trackDuration'] == 187.11
        assert status_response['position'] > 0
        assert status_response['volume'] > 20
        assert "NestedChild/ff-16b-2c-nested.mp4" in status_response['source']

    def test_server_crossfade(self, client):
        client.get("/get-track-list")
        client.get("/get-track-list?id=" + known_folder_id)

        client.get("/play-single-track?id=" + known_track_id)

        sleep(4)

        # 'skip forward' to the same track
        client.get("/crossfade?id=" + known_track_id + "&interval=4")

        sleep(4)

        status_response = client.get("/status")

        print("*" * 30)
        print("*** stat ***")
        print(status_response.json)
        print("*" * 30)

        status_response = status_response.json

        assert status_response['canControl'] == True
        assert status_response['playerState'] == 'Playing'
        assert status_response['trackDuration'] == 187.11
        assert status_response['position'] > 0
        # 80 is set in flask/test/pytest_faux_usb/settings.json
        assert status_response['volume'] == 80
        assert "NestedChild/ff-16b-2c-nested.mp4" in status_response['source']
