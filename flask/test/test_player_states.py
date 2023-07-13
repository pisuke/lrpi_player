# pytest
# test plan (more of lrpi_player 'contract' test)
#
# start Server with a local settings / usb file
# test get track list
# test load a track, play it
# assert based on response from /status
#
# test crossfade, etc
#
# generate a random interaction sequence
# last sequence is always 'stop' (i.e. pressing the 'back' button)
# make sure that the player doesn't error by the end of it
#
#
# extra unit test plan
# DMX interpolator
# get track list content JSON generation (with error modes)
# lighting
# events could be spit out through a dummy lighting driver / events go into a text file (parsed before assertion)
# events should be cross referenced with audio player timelines
##

import pytest
from Server import appFactory
import os
from time import sleep


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


# Thanks to https://stackoverflow.com/q/10480806/8249410
def equal_dicts(a, b, ignore_keys=[]):
    ka = set(a).difference(ignore_keys)
    kb = set(b).difference(ignore_keys)
    return ka == kb and all(a[k] == b[k] for k in ka)


# Note that these hashes will changed based on
# file attributes like 'last modified' etc...
known_folder_id = "b4f1020c48a28b3cdf6be408c4f585d7"
known_track_id = "420218864c124399a0f862947b73e321"


@pytest.mark.player_states
class TestLrpiPlayerStates:
    def test_play_pause(self, client):
        client.get("/get-track-list")
        client.get("/get-track-list?id=" + known_folder_id)

        client.get("/play-single-track?id=" + known_track_id)

        # around two seconds of track played
        sleep(2)

        client.get("/play-pause")

        # has been paused for 1 second
        sleep(1)

        status_response = client.get("/status").json

        assert status_response['playerState'] == 'Paused'
        assert status_response['position'] > 1

    def test_stop(self, client):
        client.get("/get-track-list")
        client.get("/get-track-list?id=" + known_folder_id)

        client.get("/play-single-track?id=" + known_track_id)

        # around two seconds of track played
        sleep(2)

        client.get("/stop")

        # has been stopped for 2 seconds
        sleep(2)

        status_response = client.get("/status").json

        print(status_response)

        assert status_response['playerState'] == ''
        assert status_response['position'] == ''
