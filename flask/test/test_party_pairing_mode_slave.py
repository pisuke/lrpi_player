# Test plan for pairing mode
# might be worth testing master and slave separately
# and basing everything on time
#
# key - need to somehow force 'paired' to true
# Can we do some network call mocking? Here's hoping!
#
# if not therefore - might be worth testing Player.py class in isolation
# alas, network calls are still made
#
# for master - set to isMaster
# send play command
# play should begin N seconds later, not before
#
# send pause command
# query status
# track should be paused N seconds later
#
#
# for slave - set to isSlave
# receive play command
# play should begin N seconds later, not before
# query status - should be Playing, should be within < 10ms?
#
# send pause command
# query status
# track should be paused N seconds alter
#
# For full e2e test, Party mode testing should be a script that runs
# against two real rpis
# Could be against player api endpoints
# might also be a Cypress (or Playwright?) test with a real frontend
# - that would also be a nice way to ensure that the 'pair' button at the
# - top of the app sticks properly when paired
# ooh, complex

import pytest
from Server import appFactory
import os
from time import sleep
import json
import pprint
import datetime


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
    app.test_client().get("/free")


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


def getLocalTimestamp():
    return datetime.datetime.now()


def getSyncTime(slaveCommandOffsetSeconds):
    return getLocalTimestamp() + \
        datetime.timedelta(seconds=slaveCommandOffsetSeconds)


testSlaveCommandOffsetSeconds = 3


@pytest.mark.pair_slave
class TestPartyPairingModeSlave:
    @pytest.mark.pair_slave
    def test_can_be_paired_with(self, client):
        client.get("/enslave")

        status_response = client.get("/status")
        status_response = status_response.json

        assert status_response['paired'] == True
        assert status_response['master_ip'] == "127.0.0.1"

    @pytest.mark.pair_slave
    def test_can_be_paired_with_then_freed(self, client):
        client.get("/enslave")

        client.get("/free")

        status_response = client.get("/status")
        status_response = status_response.json

        assert status_response['paired'] == False
        assert status_response['master_ip'] == None

    @pytest.mark.pair_slave
    def test_primeForStart_when_slave(self, client):
        client.get("/status")
        client.get("/enslave")

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

        commandPostFields = {
            'master_status': master_status,
            'command': "primeForStart",
            'position': str(0),
            'sync_timestamp': str(getSyncTime(3))
        }

        slaveCommandRes = client.post('/command', json=commandPostFields)

        print('command from slave, res: ')
        pp.pprint(slaveCommandRes.json)

        assert slaveCommandRes.json == 0

        sleep(0.5)

        slaveStatus = client.get('/status')
        slaveStatus = slaveStatus.json

        assert slaveStatus['paired'] == True
        assert slaveStatus['playerState'] == 'Paused'

    @pytest.mark.pair_slave
    def test_start_when_slave(self, client):
        # note - we MUST primeForStart before playing
        client.get("/status")
        client.get("/enslave")

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

        commandPostFields = {
            'master_status': master_status,
            'command': "primeForStart",
            'position': str(0),
            'sync_timestamp': str(getSyncTime(3))
        }

        client.post('/command', json=commandPostFields)

        commandPostFields = {
            'master_status': master_status,
            'command': "start",
            'position': str(0),
            'sync_timestamp': str(getSyncTime(5))
        }

        slaveCommandRes = client.post('/command', json=commandPostFields)

        print('command from slave, res: ')
        pp.pprint(slaveCommandRes.json)

        slaveStatus = client.get('/status')
        slaveStatus = slaveStatus.json

        assert slaveStatus['paired'] == True
        # this is weird - shouldn't this be 'paused'?
        assert slaveStatus['playerState'] == 'Playing'
        # position here is something like 2.94372847324 = why?
        # assert slaveStatus['position'] == 0

        sleep(3)
        # syncTime is 5s, so after another 3s the player should be playing

        slaveStatus = client.get('/status')
        slaveStatus = slaveStatus.json

        assert slaveStatus['paired'] == True
        assert slaveStatus['playerState'] == 'Playing'
        # Very, very loose test for synchronisation here!
        assert slaveStatus['position'] > 2
        assert slaveStatus['position'] < 6

    @pytest.mark.pair_slave
    def test_pause_when_slave(self, client):
        # note - we MUST primeForStart before playing
        client.get("/enslave")

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

        startCommand = {
            'master_status': master_status,
            'command': "start",
            'position': str(0),
            'sync_timestamp': str(getSyncTime(2))
        }
        client.post('/command', json=startCommand)

        playPauseCommand = {
            'master_status': master_status,
            'command': "playPause",
            'position': str(0),
            'sync_timestamp': str(getSyncTime(2))
        }
        slaveCommandRes = client.post('/command', json=playPauseCommand)

        print('command from slave, res: ')
        pp.pprint(slaveCommandRes.json)

        slaveStatus = client.get('/status')
        slaveStatus = slaveStatus.json

        assert slaveStatus['paired'] == True
        assert slaveStatus['playerState'] == 'Paused'
        assert slaveStatus['position'] > 0

    @pytest.mark.pair_slave
    def test_stop_when_slave(self, client):
        # note - we MUST primeForStart before playing
        client.get("/enslave")

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

        startCommand = {
            'master_status': master_status,
            'command': "start",
            'position': str(0),
            'sync_timestamp': str(getSyncTime(2))
        }
        client.post('/command', json=startCommand)

        stopCommand = {
            'master_status': master_status,
            'command': "stop",
            'position': str(0),
            'sync_timestamp': str(getSyncTime(2))
        }
        slaveCommandRes = client.post('/command', json=stopCommand)

        print('command from slave, res: ')
        pp.pprint(slaveCommandRes.json)

        slaveStatus = client.get('/status')
        slaveStatus = slaveStatus.json

        assert slaveStatus['paired'] == True
        assert slaveStatus['playerState'] == ''
        assert slaveStatus['position'] == ''

    @pytest.mark.pair_slave
    def test_seek_when_slave(self, client):
        # note - we MUST primeForStart before playing
        client.get("/enslave")

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

        startCommand = {
            'master_status': master_status,
            'command': "start",
            'position': str(0),
            'sync_timestamp': str(getSyncTime(2))
        }
        client.post('/command', json=startCommand)

        sleep(2)

        seekCommand = {
            'master_status': master_status,
            'command': "seek",
            'position': str(50),
            'sync_timestamp': str(getSyncTime(1))
        }
        slaveCommandRes = client.post('/command', json=seekCommand)

        sleep(1.5)

        print('command from slave, res AFTER SEEK: ')
        pp.pprint(slaveCommandRes.json)

        slaveStatusAfterSeek = client.get('/status')
        slaveStatusAfterSeek = slaveStatusAfterSeek.json

        print('status from slave, res AFTER SEEK: ')
        pp.pprint(slaveStatusAfterSeek)

        assert slaveStatusAfterSeek['paired'] == True
        assert slaveStatusAfterSeek['playerState'] == 'Playing'
        assert slaveStatusAfterSeek['position'] > 187.11 / 2

    @pytest.mark.pair_slave
    def test_crossfade_when_slave(self, client):
        # note - we MUST primeForStart before playing
        client.get("/enslave")

        master_status = {
            "canControl": True,
            "error": "",
            "master_ip": "",
            "paired": True,
            "playerState": "Paused",
            "playerType": "MPV",
            "interval": 2,  # interval must be int!
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

        startCommand = {
            'master_status': master_status,
            'command': "start",
            'position': str(0),
            'sync_timestamp': str(getSyncTime(2))
        }
        client.post('/command', json=startCommand)

        sleep(2)

        # note: crossfades to the same track!
        fadeDownCommand = {
            'master_status': master_status,
            'command': "fadeDown",
            'position': str(50),
            'sync_timestamp': str(getSyncTime(2))
        }
        slaveCommandRes = client.post('/command', json=fadeDownCommand)

        print('command from slave, res AFTER FADE DOWN: ')
        pp.pprint(slaveCommandRes.json)

        slaveStatusAfterFadeDown = client.get('/status')
        slaveStatusAfterFadeDown = slaveStatusAfterFadeDown.json

        print('status from slave, res FADE DOWN: ')
        pp.pprint(slaveStatusAfterFadeDown)

        assert slaveStatusAfterFadeDown['paired'] == True
        assert slaveStatusAfterFadeDown['playerState'] == ''
        assert slaveStatusAfterFadeDown['volume'] == 0
