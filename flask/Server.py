#
#
# Clearing omxplayer temporary files sometimes solves the issue,
# sometimes it doesn't...
# sudo rm -rf /tmp/omxplayerdbus*
#
#

#!/usr/bin/env python3

from os.path import splitext
import os
import os.path
os.environ["FLASK_ENV"] = "development"

from flask import Flask, request, send_from_directory, render_template
from flask_cors import CORS, cross_origin 
from flask_restful import Resource, Api
from json import dumps
from flask_jsonpify import jsonify
from flask_restful import reqparse
import ntplib # pylint: disable=import-error
from time import ctime
from time import sleep
import pause # pylint: disable=import-error
import time
import signal
from pysrt import open as srtopen # pylint: disable=import-error
from pysrt import stream as srtstream
from Player import LushRoomsPlayer
from OmxPlayer import killOmx
import logging

from content_reader import content_in_dir

import settings

# 103 -> whitelist is injected from settings.json into the logic that uses the bools below...
# Remember to update docs/gdrive examples!

mpegOnly = True
mlpOnly = False
allFormats = False
useNTP = False

app = Flask(__name__,  static_folder='static')
api = Api(app)

SENTRY_URL = os.environ.get("SENTRY_URL")

if SENTRY_URL is not None:
    from raven.contrib.flask import Sentry
    sentry = Sentry(app, dsn=SENTRY_URL)


NTP_SERVER = 'ns1.luns.net.uk'
BASE_PATH = "/media/usb/"
MEDIA_BASE_PATH = BASE_PATH + "tracks/"
BUILT_PATH = None
AUDIO_PATH_TEST_MP4 = "5.1_AAC_Test.mp4"
JSON_LIST_FILE = "content.json"
MENU_DMX_VAL = os.environ.get("MENU_DMX_VAL", None)

TEST_TRACK = MEDIA_BASE_PATH + AUDIO_PATH_TEST_MP4
NEW_TRACK_ARRAY = []
NEW_SRT_ARRAY = []

player = None
paused = None

CORS(app)
# killOmx as soon as the server starts...
killOmx()

# utils

# Kill omx processes on a ctrl+c/program closure
# to mirror the behaviour of vlc and, in turn, to
# be more graceful

def sigint_handler(signum, frame):
    killOmx()
    exit()

signal.signal(signal.SIGINT, sigint_handler)

def getInput():
    parser = reqparse.RequestParser()
    parser.add_argument('id', help='error with id')
    parser.add_argument('interval', help='error with interval')
    parser.add_argument('position', help='error with position')
    parser.add_argument('pairhostname', help='error with pairHostname')
    # command and status should definitely be sent via POST...
    parser.add_argument('commandFromMaster', help='error with commandFromMaster')
    parser.add_argument('masterStatus', help='error with masterStatus')
    args = parser.parse_args()
    return args

def printOmxVars():
    print("OMXPLAYER_LIB" in os.environ)
    print("LD_LIBRARY_PATH" in os.environ)
    print("OMXPLAYER_BIN" in os.environ)

def loadSettings():
    # return a graceful error if contents.json can't be found

    settings_json = settings.get_settings()
    settings_json = settings_json.copy()
    settings_json["roomName"] = settings_json["name"]
    print("Room name: ", settings_json["name"])

    return settings_json

def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        print('{:s} function took {:.3f} ms'.format(f.__name__, (time2-time1)*1000.0))

        return ret
    return wrap

# serve the angular app

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists("static/" + path):
        return send_from_directory('static/', path)
    else:
        return send_from_directory('static/', 'index.html')

# API endpoints

class GetSettings(Resource):
    def get(self):
        return jsonify(loadSettings())


class GetTrackList(Resource):
    def get(self):

        print(GetTrackList)

        global NEW_TRACK_ARRAY
        global NEW_SRT_ARRAY
        global BUILT_PATH
        global player

        try:

            if useNTP:
                c = ntplib.NTPClient()
                try:
                    response = c.request(NTP_SERVER)
                    print('\n' + 30*'-')
                    print('ntp time: ', ctime(response.tx_time))
                    print(30*'-' + '\n')
                except:
                    print('Could not get ntp time!')

            # return a graceful error if the usb stick isn't mounted
            if os.path.isdir(MEDIA_BASE_PATH) == False:
                return jsonify(1)

            if BUILT_PATH is None:
                BUILT_PATH = MEDIA_BASE_PATH 
            
            args = getInput()

            print("track list id: " +  str(args['id']))


            if args['id']:
                if NEW_TRACK_ARRAY:
                    BUILT_PATH += [x['Path'] for x in NEW_TRACK_ARRAY if x['ID'] == args['id']][0] + "/"
                    print(BUILT_PATH[0])


            print('BUILT_PATH: ' + str(BUILT_PATH))


            TRACK_ARRAY_WITH_CONTENTS = content_in_dir(BUILT_PATH)
            # print(TRACK_ARRAY_WITH_CONTENTS)
            NEW_SRT_ARRAY = TRACK_ARRAY_WITH_CONTENTS

            if mpegOnly:
                NEW_TRACK_ARRAY = [x for x in TRACK_ARRAY_WITH_CONTENTS if ((x['Name'] != JSON_LIST_FILE) and (splitext(x['Name'])[1].lower() != ".srt") and (splitext(x['Name'])[1].lower() != ".mlp"))]
            elif mlpOnly:
                NEW_TRACK_ARRAY = [x for x in TRACK_ARRAY_WITH_CONTENTS if ((x['Name'] != JSON_LIST_FILE) and (splitext(x['Name'])[1].lower() != ".srt") and (splitext(x['Name'])[1].lower() != ".mp4"))]
            elif allFormats:
                NEW_TRACK_ARRAY = [x for x in TRACK_ARRAY_WITH_CONTENTS if ((x['Name'] != JSON_LIST_FILE) and (splitext(x['Name'])[1].lower() != ".srt"))]


            NEW_SRT_ARRAY = [x for x in TRACK_ARRAY_WITH_CONTENTS if splitext(x['Name'])[1].lower() == ".srt"]

            if player and player.lighting.dmx:
                player.setPlaylist(NEW_TRACK_ARRAY)
                player.resetLighting()
            else:
                player = LushRoomsPlayer(NEW_TRACK_ARRAY, MEDIA_BASE_PATH)
                player.resetLighting()

            return jsonify(NEW_TRACK_ARRAY)
        except Exception as e:
            logging.error("Path building has probably failed. Sending error code and cleaning up...")
            logging.error(e)
            BUILT_PATH = None
            return 1, 500, {'content-type': 'application/json'}


class PlaySingleTrack(Resource):
    def get(self):
        global player
        global paused
        global BUILT_PATH

        args = getInput()

        for track in NEW_TRACK_ARRAY:
            if track["ID"] == args["id"]:
                srtFileName = splitext(track["Path"])[0]+".srt"
                pathToTrack = BUILT_PATH + track["Path"]

        if os.path.isfile(pathToTrack) == False:
            print('Bad file path, will not attempt to play...')
            return jsonify("(Playing) File not found!")

        print("Playing: " + pathToTrack)

        duration = player.start(pathToTrack, None, BUILT_PATH + srtFileName)

        return jsonify(duration)

class PlayPause(Resource):
    def get(self):
        global player
        duration = player.playPause()
        return jsonify(duration)

class FadeDown(Resource):
    def get(self):
        global player
        global BUILT_PATH 

        args = getInput()
        print('argsid : ', args["id"])
        # print('argsinterval: ', args["interval"])
        pathToTrack = None
        subs = None
        srtFileName = None

        for track in NEW_TRACK_ARRAY:
            if track["ID"] == args["id"]:
                srtFileName = splitext(track["Path"])[0]+".srt"
                if os.path.isfile(str(BUILT_PATH) + srtFileName):
                    print(srtFileName)
                    start_time = time.time()
                    print("Loading SRT file " + srtFileName + " - " + str(start_time))
                    subs = srtopen(BUILT_PATH + srtFileName)
                    #subs = srtstream(BUILT_PATH + srtFileName)
                    end_time = time.time()
                    print("Finished loading SRT file " + srtFileName + " - " + str(end_time))
                    print("Total time elapsed: " + str(end_time - start_time))
                pathToTrack = BUILT_PATH + track["Path"]

        if pathToTrack is None or not os.path.isfile(pathToTrack):
            print('Bad file path, will not attempt to play...')
            return jsonify(1)

        response = player.fadeDown(pathToTrack, int(args["interval"]),  subs, BUILT_PATH + srtFileName)

        return jsonify(response)

class Seek(Resource):
    def get(self):
        global player
        global BUILT_PATH

        args = getInput()
        print('position to seek (%%): ', args["position"])
        # print('argsinterval: ', args["interval"])

        response = player.seek(int(args["position"]))
        print('pos: ', response)

        return jsonify(response)

class PlayerStatus(Resource):
    def get(self):
        global player

        try:
            response = player.getStatus()
        except:
            response = 1

        return jsonify(response)

class Pair(Resource):
    def get(self):
        global player

        args = getInput()
        print('Pair with: ', args["pairhostname"])

        try:
            pairRes = player.pairAsMaster(args["pairhostname"])
        except Exception as e:
            print('Exception: ', e)
            pairRes = 1

        return jsonify(pairRes)

class Unpair(Resource):
    def get(self):
        global player

        try:
            unpairRes = player.unpairAsMaster()
        except Exception as e: 
            print('Exception: ', e)
            unpairRes = 1

        return jsonify(unpairRes)

class Enslave(Resource):
    def get(self):
        global player

        # If there is a player running, kill it
        # If there isnt, make one without a playlist
        # since we'll be getting the path of the audio/srt
        # from the status object from the master

        # If the Angular app is accessed while a LRPi is
        # in slave mode, we know from the status object that
        # it is paired: we can easily lock the UI and stop it
        # sending any control commands

        if player:
            player.stop()
            player.exit()
        else:
            player = LushRoomsPlayer(None, None)

        print('Enslaving, player stopped and exited')
        print('Enslaved by: ', request.environ.get('HTTP_X_REAL_IP', request.remote_addr) )

        # set paired to true
        masterIp = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)

        player.setPairedAsSlave(True, masterIp)

        return jsonify(0)

class Free(Resource):
    def get(self):
        global player
 
        try:
            freeRes = player.free()
        except Exception as e: 
            print('Exception: ', e)
            freeRes = 1

        return jsonify(freeRes)

# POST body Should have the command, status of the master
# and the desired trigger time

class Command(Resource):
    def post(self):
        global player
        command = request.get_json(force=True)

        res = player.commandFromMaster(
            command["master_status"],
            command["command"],
            command["sync_timestamp"]
        )

        return jsonify(res)

class Stop(Resource):
    def get(self):
        global player
        global BUILT_PATH

        BUILT_PATH = None

        try:
            response = player.stop()
        except:
            response = 1

        return jsonify(response)


class ScentRoomTrigger(Resource):
    def post(self):
        global player
        body = request.get_json(force=True)

        print("SR Trigger received:")
        print(body)

        if body:
            if body['trigger'] == "start" and body["upload_path"]:
                if player == None:
                    player = LushRoomsPlayer(None, None)
                    player.start(body["upload_path"], None, "/media/usb/uploads/01_scentroom.srt")
                    return jsonify({'response': 200, 'description': 'ok!'})

            elif body['trigger'] == "stop":
                # TODO: make this better
                # Python, your flexibility is charming but also _scary_
                if player:
                    try:
                        # RGB value for warm white for both RGBW downlight and side RGB lights
                        # The eighth channel of 255 is needed for whatever reason, I don't have time
                        # to find out why right now
                        # matched white light RGB: 255, 241, 198, 255
                        if player.lighting.dmx:
                            player.lighting.dmx.write_frame([0, 0, 0, 255, 0, 0, 0, 0])
                    except Exception as e:
                        logging.error("Could not kill lighting, things have gotten out of sync...")
                        logging.info("Killing everything anyway!")
                        print("Why: ", e)
                        player.stop()
                        player.exit()
                        player.__del__()
                        player = None
                    player.stop()
                    player.exit()
                    player.__del__()
                    player = None
                
                return jsonify({'response': 200, 'description': 'ok!'})

            else:
                return jsonify({'response': 500, 'description': 'not ok!', "error": "Unsupported trigger"})

        else:
            return jsonify({'response': 500, 'description': 'not ok!', "error": "Incorrect body format"})
        
# URLs are defined here

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
api.add_resource(Command, '/command') # POST

# Scentroom specific endpoints
api.add_resource(ScentRoomTrigger, '/scentroom-trigger') # POST

if __name__ == '__main__':
    settings_json = settings.get_settings()
    app.run(debug=settings_json["debug"], port=os.environ.get("PORT", "80"), host='0.0.0.0')
