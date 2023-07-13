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


from Player import LushRoomsPlayer
from Connections import Connections
# import requests_mock
import requests
import datetime
import pprint
import json
from time import sleep
import os
from Server import appFactory
import pytest
import sys
# Add the ptdraft folder path to the sys.path list
sys.path.append('/opt/code/flask')

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
    app.test_client().get("/unpair")


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


# Note that these hashes will changed based on
# file attributes like 'last modified' etc...
known_mp4_path = "/opt/code/flask/test/pytest_faux_usb/tracks/Misophonia/misophonia.mp4"
known_srt_path = "/opt/code/flask/test/pytest_faux_usb/tracks/Misophonia/misophonia.srt"


@pytest.mark.pair_master
class TestPartyPairingModeMaster:
    # todo: learn more about pythonic, nock-like interfaces
    # @requests_mock.Mocker(kw='http_mocker', real_http=True)
    @pytest.mark.pair_master
    def test_can_pair_with_slave(self, client, **kwargs):
        # these tests ABSOLUTELY need to exist
        # in a format where the /pair /unpair /free routes are tested
        #
        # but I can't quite get my head around how to intercept / mock http requests to the slave here...
        # it will be possible, potentially using the requests_mock module?

        # For now, tests might be based around building a LushRoomsPlayer object
        # in 'master mode', i.e. like so

        connections = Connections()
        player = LushRoomsPlayer(connections)
        player.setSlaveUrl("http://urawizard.com") \
            .setPaired() \
            .isMaster = True

        player.start(known_mp4_path, None, known_srt_path)

        sleep(2)

        status = player.getStatus()

        assert status["paired"] == True
        assert status["slave_url"] == "http://urawizard.com"
        assert status["playerState"] == "Playing"
        assert status["position"] > 0

    @pytest.mark.skip(reason="Need to (somehow...) intercept the request to urawizard.com - try the @patch thing")
    def test_can_pair_then_unpair(self, client):
        connections = Connections()
        player = LushRoomsPlayer(connections)
        player.setSlaveUrl("http://urawizard.com") \
            .setPaired() \
            .isMaster = True

        player.start(known_mp4_path, None, known_srt_path)

        sleep(2)

        player.playPause()

        sleep(1)

        player.unpairAsMaster()

        status = player.getStatus()

        assert status["paired"] == False
        assert status["slave_url"] == None
        # if 'unpair' is pressed on the master,
        # the current behaviour dictates that the master keeps
        # playing and the slave resets
        assert status["playerState"] == "Playing"
        assert status["position"] > 0

    @pytest.mark.pair_master
    def test_stays_paired_after_complex_interaction(self, client):
        # This is best tested using the HTTP routes,
        # especially what happens after:
        # /get-track-list + /pair + /play-single-track + /seek + /stop
        # + /get-track-list
        #
        # We want to make the the 'pairing' state is constant across
        # many audio / lighting object lifecycles
        pass
