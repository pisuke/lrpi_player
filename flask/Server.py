#!/usr/bin/env python3

# Tip for trying newer versions of omxplayer:
#
# Clearing omxplayer temporary files sometimes solves issues,
# sometimes it doesn't...
# sudo rm -rf /tmp/omxplayerdbus*


from Connections import Connections
from Player import LushRoomsPlayer
from FileExplorer import BasePathInvalid, FileExplorer
import settings
import logging
from pysrt import open as srtopen  # pylint: disable=import-error
import signal
import time
from time import sleep
import ntplib  # pylint: disable=import-error
from flask_restful import reqparse
from flask_jsonpify import jsonify
from flask_restful import Resource, Api
from flask_cors import CORS
from flask import Flask, request, send_from_directory
from os.path import splitext
import os
import sys
import os.path
import datetime
from platform_helpers import killOmx
os.environ["FLASK_ENV"] = "development"

# Remove initial Flask messages and warning
cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *x: None

# boolean flags
mpegOnly = True
mlpOnly = False
allFormats = False
useNTP = False

if useNTP:
    import Ntp
    # Could we do this on every 'pair' or 'free'?
    # Would that be silly and/or dumb?
    Ntp.set_os_time_with_ntp()

app = Flask(__name__,  static_folder='static')
api = Api(app)

logging.getLogger('apscheduler').setLevel(logging.CRITICAL)

SENTRY_URL = os.environ.get("SENTRY_URL")

if SENTRY_URL is not None:
    from raven.contrib.flask import Sentry
    sentry = Sentry(app, dsn=SENTRY_URL)

MENU_DMX_VAL = os.environ.get("MENU_DMX_VAL", None)
NUM_DMX_CHANNELS = os.environ.get("NUM_DMX_CHANNELS", None)
HOST = os.environ.get("BRICKD_HOST", "127.0.0.1")
PORT = 4223

NEW_TRACK_ARRAY = []
NEW_SRT_ARRAY = []

CORS(app)


def get_connections():
    global connections
    return connections

# utils


def sigint_handler(signum, frame):
    """ Kill omx processes on a ctrl+c/program closure to mirror the behaviour of vlc and, in turn, to be more graceful. """
    killOmx()
    get_connections().__del__()
    exit()


signal.signal(signal.SIGINT, sigint_handler)


def printOmxVars():
    print("OMXPLAYER_LIB" in os.environ)
    print("LD_LIBRARY_PATH" in os.environ)
    print("OMXPLAYER_BIN" in os.environ)


def loadSettings():
    """ 
        Load contents.json and return a graceful error if the file can't be found. 
    """
    settings_json = settings.get_settings()
    settings_json = settings_json.copy()
    settings_json["roomName"] = settings_json["name"]
    print("Room name: ", settings_json["name"])
    return settings_json


class LushRoomsPlayerWrapped():
    """
        LushRoomsPlayer singleton 
        (to avoid messing up state with the 'global' keyword everywhere...)

        This also allows us to handle race conditions on startup, e.g. if some
        route is called before LushRoomsPlayer has finished starting up, we can
        do something graceful(ish).

        Every time instance() is accessed, _instance_count is printed 
    """
    _instance = None
    _instance_count = 0
    _RACE_CONDITION_GUARD = "PLAYER_IS_SETTING_UP"
    _RACE_CONDITION_WAIT = 0.5

    def __init__(self):
        raise RuntimeError(
            'For safety reasons, only call instance() or destroy(), e.g. LushRoomsPlayerWrapper.destroy() - only one set of parentheses!')

    @classmethod
    def instance(cls, *args, **kwargs):
        print("LushRoomsPlayerWrapped count :: ", str(cls._instance_count))

        if cls._instance_count > 1:
            # ideally, this should never happen
            # if this DOES happen, it is likely two or more
            # of the same track will be playing simultaneously
            logging.error(
                "DANGER : LushRoomsPlayerWrapped count is " + str(cls._instance_count))

        while cls._instance == cls._RACE_CONDITION_GUARD:
            # bit of a hack here
            # ideally we need to test if the lighting init
            # (which is the thing taking the time in the LushRoomsPlayer
            # init sequence) can be folded into the 'connections' object...
            sleep(cls._RACE_CONDITION_WAIT)

        if cls._instance is None:
            print('Creating new LushRoomsPlayer')
            connections = get_connections()
            # to avoid race conditions, we set cls._instance to a
            # string so that any HTTP calls that arrive before
            # the LushRoomsPlayer constructor exits fail
            #
            # This ensures that there will only ever be ONE instance of
            # LushRoomsPlayer. This, in turn, means that only one omx process
            # will be spawned and allows us to keep the 'paired' state within
            # LushRoomsPlayer
            cls._instance = cls._RACE_CONDITION_GUARD
            cls._instance = LushRoomsPlayer(connections, *args, **kwargs)
            cls._instance_count += 1
        return cls._instance

    @classmethod
    def destroy(cls):
        if cls._instance is not None:
            cls._instance.exit()
            del cls._instance
            cls._instance = None
            cls._instance_count -= 1

# serve the angular app (https://github.com/LUSHDigital/lrpi_tablet_ui)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists("static/" + path):
        return send_from_directory('static/', path)
    else:
        return send_from_directory('static/', 'index.html')


def http_error_response(message="LushRooms, we have a problem"):
    return 1, 500, {'content-type': 'application/json'}

# API endpoints

# Generic endpoints


class GetSettings(Resource):
    def get(self):
        return jsonify(loadSettings())


def getInput():
    parser = reqparse.RequestParser()
    parser.add_argument('id', help='error with id')
    parser.add_argument('interval', help='error with interval')
    parser.add_argument('position', help='error with position')
    parser.add_argument('pairhostname', help='error with pairHostname')
    # command and status should definitely be sent via POST...
    parser.add_argument('commandFromMaster',
                        help='error with commandFromMaster')
    parser.add_argument('masterStatus', help='error with masterStatus')
    args = parser.parse_args()
    return args


class GetTrackList(Resource):
    def get(self):
        try:

            MEDIA_BASE_PATH = loadSettings()["media_base_path"]
            file_explorer = FileExplorer(MEDIA_BASE_PATH)
            args = getInput()
            track_or_folder_id = args['id']

            try:
                (NEW_TRACK_ARRAY, _) = file_explorer.contents_by_directory_id(
                    track_or_folder_id)
            except BasePathInvalid:
                logging.error(
                    MEDIA_BASE_PATH + " is not a valid os file path - cannot load media from this directory!")
                return jsonify(1)

            LushRoomsPlayerWrapped.instance() \
                .setPlaylist(NEW_TRACK_ARRAY) \
                .setMediaBasePath(MEDIA_BASE_PATH) \
                .resetLighting()

            print("LushRoomsPlayerWrapped created!")

            return jsonify(NEW_TRACK_ARRAY)
        except Exception as e:
            logging.error(
                "Path building has probably failed. Sending error code and cleaning up...")
            logging.error(e)
            return http_error_response()


class PlaySingleTrack(Resource):
    def get(self):
        MEDIA_BASE_PATH = loadSettings()["media_base_path"]
        file_explorer = FileExplorer(MEDIA_BASE_PATH)
        args = getInput()
        track_id = args['id']

        (_, path_to_track, path_to_srt) = file_explorer.track_by_track_id(track_id)

        if os.path.isfile(path_to_track) == False:
            print('Bad file path, will not attempt to play...')
            return jsonify("(Playing) File not found! " + str(path_to_track))

        print("Playing: " + path_to_track)

        duration = LushRoomsPlayerWrapped.instance().start(
            path_to_track, None, path_to_srt)

        return jsonify(duration)


class PlayPause(Resource):
    def get(self):
        duration = LushRoomsPlayerWrapped.instance().playPause()
        return jsonify(duration)


class FadeDown(Resource):
    def get(self):
        MEDIA_BASE_PATH = loadSettings()["media_base_path"]
        file_explorer = FileExplorer(MEDIA_BASE_PATH)
        args = getInput()
        track_id = args['id']

        (_, path_to_track, path_to_srt) = file_explorer.track_by_track_id(track_id)

        if os.path.isfile(path_to_track) == False:
            print('Bad file path, will not attempt to play...')
            return jsonify(1)

        print(path_to_srt)
        start_time = time.time()
        print("Loading SRT file " + path_to_srt +
              " - " + str(start_time))
        subs = srtopen(path_to_srt)
        end_time = time.time()
        print("Finished loading SRT file " +
              path_to_srt + " - " + str(end_time))
        print("Total time elapsed: " + str(end_time - start_time))

        response = LushRoomsPlayerWrapped.instance().fadeDown(
            path_to_track,
            int(args["interval"]),
            subs,
            path_to_srt
        )

        return jsonify(response)


class Seek(Resource):
    def get(self):
        args = getInput()
        print('position to seek (%%): ', args["position"])

        response = LushRoomsPlayerWrapped.instance().seek(
            int(args["position"]))

        print('pos: ', response)

        return jsonify(response)


class PlayerStatus(Resource):
    def get(self):
        try:
            response = LushRoomsPlayerWrapped.instance().getStatus()
        except Exception as e:
            print('Could not get PlayerStatus: ', e)
            response = 1

        return jsonify(response)


class Pair(Resource):
    def get(self):
        args = getInput()
        print('Pair with: ', args["pairhostname"])

        try:
            pairRes = LushRoomsPlayerWrapped.instance(
            ).pairAsMaster(args["pairhostname"])
        except Exception as e:
            print('Pair as Master Exception: ', e)
            pairRes = 1
            LushRoomsPlayerWrapped.instance(
            ).setUnpaired()

        return jsonify(pairRes)


class Unpair(Resource):
    def get(self):
        try:
            unpairRes = LushRoomsPlayerWrapped.instance().unpairAsMaster()
        except Exception as e:
            print('Unpair as master Exception: ', e)
            unpairRes = 1

        return jsonify(unpairRes)


class Enslave(Resource):
    """
        If there is a player running, kill it

        If there isnt, make one without a playlist
        since we'll be getting the path of the audio/srt
        from the status object from the master

        If the Angular app is accessed while a LRPi is
        in slave mode, we know from the status object that
        it is paired: we can easily lock the UI and stop it
        sending any control commands
    """

    def get(self):
        LushRoomsPlayerWrapped.destroy()

        print('Enslaving, player stopped and exited')
        print('Enslaved by: ', request.environ.get(
            'HTTP_X_REAL_IP', request.remote_addr))

        # set paired to true
        masterIp = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)

        LushRoomsPlayerWrapped \
            .instance() \
            .setSlaveUrl(None) \
            .setMasterIp(masterIp) \
            .setPaired()

        LushRoomsPlayerWrapped.instance().isSlave = True

        return jsonify(0)


class Free(Resource):
    """
        Free is nominally for unpairing 'slaved'
        LushRoomsPis - a controller Pi releases a
        'slaved' Pi

        It can also be used as a hard reset at any point.
    """

    def get(self):
        try:
            print('Freeing slave! :: ')
            freeRes = LushRoomsPlayerWrapped.instance().free()
            LushRoomsPlayerWrapped.destroy()
        except Exception as e:
            print('Could not Free: ', e)
            freeRes = 1

        return jsonify(freeRes)


class Command(Resource):
    """
        POST body Should have the command, status of the master, 
        desired position of the player (for 'seek' commands)
        and the desired trigger time (sync_timestamp)
    """

    def post(self):
        command = request.get_json(force=True)

        res = LushRoomsPlayerWrapped.instance().commandFromMaster(
            command["master_status"],
            command["command"],
            command["position"],
            datetime.datetime.strptime(
                command["sync_timestamp"], '%Y-%m-%d %H:%M:%S.%f')
        )

        return jsonify(res)


class Stop(Resource):
    def get(self):
        try:
            response = LushRoomsPlayerWrapped.instance().stop()
        except Exception as e:
            print('Could not Stop: ', e)
            response = 1

        return jsonify(response)

# Scentroom specific functions / endpoints


class ScentRoomTrigger(Resource):
    def post(self):
        body = request.get_json(force=True)

        print("SR Trigger received:")
        print(body)

        if body:
            if body['trigger'] == "start" and body["upload_path"]:
                print("SR Trigger received: start")
                mp3_filename = body["upload_path"]
                srt_filename = os.path.splitext(mp3_filename)[0]+".srt"
                print(mp3_filename, srt_filename)
                LushRoomsPlayerWrapped.instance() \
                    .start(mp3_filename, None, srt_filename)
                return jsonify({'response': 200, 'description': 'ok!'})

            elif body['trigger'] == "stop":
                print("SR Trigger received: stop")
                # TODO: make this better
                # Python, your flexibility is charming but also _scary_
                if LushRoomsPlayerWrapped.instance() != None:
                    print("SR Trigger received: player existing")
                    try:
                        # for the ScentRoom, RGB value for warm white for both RGBW downlight and side RGB lights
                        # The eighth channel of 255 is needed for whatever reason, I don't have time
                        # to find out why right now
                        # matched white light RGB: 255, 241, 198, 255
                        if LushRoomsPlayerWrapped.instance().lighting.dmx:
                            LushRoomsPlayerWrapped.instance().lighting.dmx.write_frame(
                                [0, 0, 0, 255, 30, 30, 30, 0])
                    except Exception as e:
                        logging.error(
                            "Could not kill lighting, things have gotten out of sync...")
                        logging.info("Killing everything anyway!")
                        print("Why: ", e)

                    LushRoomsPlayerWrapped.instance().stop()
                    LushRoomsPlayerWrapped.destroy()

                    get_connections().scheduler.print_jobs()

                return jsonify({'response': 200, 'description': 'ok!'})

            else:
                return jsonify({'response': 500, 'description': 'not ok!', "error": "Unsupported trigger"})

        else:
            return jsonify({'response': 500, 'description': 'not ok!', "error": "Incorrect body format"})


class ScentRoomIdle(Resource):
    def get(self):
        try:
            print("SR Trigger idle - restarting LushRoomsPlayer")
            LushRoomsPlayerWrapped.destroy()

            mp3_filename = "/media/usb/uploads/idle.mp3"
            srt_filename = os.path.splitext(mp3_filename)[0]+".srt"

            LushRoomsPlayerWrapped \
                .instance() \
                .start(mp3_filename, None, srt_filename,
                       syncTime=None, loop=True)
            return jsonify({'response': 200, 'description': 'ok!'})
        except Exception as e:
            print("Idle sequence failed: ", e)
            return jsonify({'response': 500, 'description': 'not ok!'})


# URLs / routes defined here

api.add_resource(GetTrackList, '/get-track-list')
api.add_resource(PlaySingleTrack, '/play-single-track')
api.add_resource(PlayPause, '/play-pause')
api.add_resource(FadeDown, '/crossfade')
api.add_resource(Seek, '/seek')
api.add_resource(Stop, '/stop')
api.add_resource(GetSettings, '/settings')
api.add_resource(PlayerStatus, '/status')
# Master endpoints
api.add_resource(Pair, '/pair')
api.add_resource(Unpair, '/unpair')
# Slave endpoints
api.add_resource(Enslave, '/enslave')
api.add_resource(Free, '/free')
api.add_resource(Command, '/command')  # POST

# Scentroom specific endpoints
api.add_resource(ScentRoomTrigger, '/scentroom-trigger')  # POST
api.add_resource(ScentRoomIdle, '/scentroom-idle')  # GET


def appFactory():
    """
        appFactory should only be
        used by pytest!
    """
    print("In app factory")
    global connections

    # killOmx as soon as the server starts...
    killOmx()

    # Initialise the connections singletons
    connections = Connections()
    return app


if __name__ == '__main__':
    global connections

    # killOmx as soon as the server starts...
    killOmx()

    # Initialise the connections singletons
    connections = Connections()

    settings_json = settings.get_settings()
    app.run(use_reloader=False, debug=settings_json["debug"], port=os.environ.get(
        "PORT", "80"), host='0.0.0.0')
