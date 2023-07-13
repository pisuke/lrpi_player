import pytest
from Server import appFactory
import os
from time import sleep
import pprint
import datetime
from threading import Thread
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


def getLocalTimestamp():
    return datetime.datetime.now()


def getSyncTime(slaveCommandOffsetSeconds):
    return getLocalTimestamp() + \
        datetime.timedelta(seconds=slaveCommandOffsetSeconds)


testSlaveCommandOffsetSeconds = 3


@pytest.mark.use_cases
class TestSpecificUseCases:

    @pytest.mark.pair_slave
    def test_does_not_need_refreshes_after_follower_free(self, client):
        # enslave
        client.get("/enslave")

        # prime for start
        master_status = {
            "canControl": True,
            "error": "",
            "master_ip": "",
            "paired": True,
            "playerState": "Paused",
            "playerType": "MPV",
            "playlist": [
                {
                    "ID": "bc1e0c153609b9abdad741fbb13d9623",
                    "IsDir": False,
                    "MimeType": "video/mp4",
                    "ModTime": "2023-05-04T20:35:03.216627Z",
                    "Name": "misophonia.mp4",
                    "Path": "/opt/code/flask/test/pytest_faux_usb/tracks/Misophonia/misophonia.mp4",
                    "Size": 3079106
                },
            ],
            "position": 2.32589569160998,
            "slave_url": None,
            "source": "/opt/code/flask/test/pytest_faux_usb/tracks/Misophonia/misophonia.mp4",
            "subsPath": "/opt/code/flask/test/pytest_faux_usb/tracks/Misophonia/misophonia.srt",
            "trackDuration": 187.11,
            "volume": 55
        }

        primeCommand = {
            'master_status': master_status,
            'command': "primeForStart",
            'position': str(0),
            'sync_timestamp': str(getSyncTime(2))
        }
        client.post('/command', json=primeCommand)

        # play for a bit

        startCommand = {
            'master_status': master_status,
            'command': "start",
            'position': str(0),
            'sync_timestamp': str(getSyncTime(2))
        }
        client.post('/command', json=startCommand)

        sleep(5)

        # free randomly (during playback, should stop the player)

        client.get("/free")

        # ask for tracks after some rapid fire status / settings / status
        # this mimics the rxjs behaviour from the tablet ui

        def _statusReq():
            client.get('/status')
            print('status finished')

        def _settingsReq():
            client.get('/settings')
            print('settings finished')

        Thread(target=_statusReq).start()
        Thread(target=_settingsReq).start()
        Thread(target=_statusReq).start()

        slavePlaylistAfterFree = client.get('/get-track-list')
        slavePlaylistAfterFree = slavePlaylistAfterFree.json

        statusAfterFree = client.get('/status')
        statusAfterFree = statusAfterFree.json

        # should NOT get an error result

        assert slavePlaylistAfterFree != 1
        assert len(slavePlaylistAfterFree) == 4
        assert statusAfterFree['canControl'] == False
        assert statusAfterFree['position'] == ''
        assert len(statusAfterFree['error']) > 0
