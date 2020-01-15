#!/usr/bin/env python3

# TODO:
#
# Clearing omxplayer temporary files sometimes solves the issue,
# sometimes it doesn't...
# sudo rm -rf /tmp/omxplayerdbus*
#
# 103 -> whitelist is injected from settings.json into the logic that uses the bools below...
# Remember to update docs/gdrive examples!


from os.path import splitext
import os, sys
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
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from tinkerforge.ip_connection import IPConnection # pylint: disable=import-error

import settings
from content_reader import content_in_dir
from Lighting import LushRoomsLighting
from Player import LushRoomsPlayer
from OmxPlayer import killOmx

# Remove initial Flask messages and warning
cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *x: None

# boolean flags
mpegOnly = True
mlpOnly = False
allFormats = False
useNTP = False

app = Flask(__name__,  static_folder='static')
api = Api(app)

scheduler = BackgroundScheduler({
    'apscheduler.executors.processpool': {
        'type': 'processpool',
        'max_workers': '1'
    }}, timezone="Europe/London")
scheduler.start(paused=False)
logging.getLogger('apscheduler').setLevel(logging.CRITICAL)

SENTRY_URL = os.environ.get("SENTRY_URL")

if SENTRY_URL is not None:
    from raven.contrib.flask import Sentry
    sentry = Sentry(app, dsn=SENTRY_URL)



NTP_SERVER = 'ns1.luns.net.uk'
BASE_PATH = "/media/usb/"
MEDIA_BASE_PATH = BASE_PATH + "tracks/"
BUILT_PATH = None
JSON_LIST_FILE = "content.json"
MENU_DMX_VAL = os.environ.get("MENU_DMX_VAL", None)
NUM_DMX_CHANNELS = os.environ.get("NUM_DMX_CHANNELS", None)
HOST = os.environ.get("BRICKD_HOST", "127.0.0.1")
PORT = 4223

NEW_TRACK_ARRAY = []
NEW_SRT_ARRAY = []

player = None
tfipcon = IPConnection() # TinkerForge IP connection
paused = True
status = "Paused"
idle_lighting_player = None

CORS(app)
# killOmx as soon as the server starts...
killOmx()


# utils

def sigint_handler(signum, frame):
    """ Kill omx processes on a ctrl+c/program closure to mirror the behaviour of vlc and, in turn, to be more graceful. """
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
    """ Load contents.json and return a graceful error if the file can't be found. """
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

def idleLoop():
    global player, paused, status, idle_lighting_player, tfipcon
    print(time.time(), tfipcon, idle_lighting_player)
    try:
        if player != None:
            status = player.getStatus()["playerState"]
        else:
            status = "Paused"
    except:
        status = "Paused"
    if status == "Paused":
        print("Playing idle loop", idle_lighting_player.startTime, idle_lighting_player.last_played, idle_lighting_player.job)
        # idlePlay()
        idle_lighting_player.startTime = time.perf_counter()
        idle_lighting_player.last_played = 0
        print(idle_lighting_player.startTime, idle_lighting_player.last_played, idle_lighting_player.job)
        # idle_lighting_player.start(None, subs)
        # idle_lighting_player.job.Job.resume()
        # idle_lighting_player.scheduler.resume()
    elif status == "Playing":
        pass
        # idle_lighting_player.playPause()
        # idle_lighting_player.job.Job.pause()
    print(status)

def idlePlay():
    global player, scheduler, tfipcon
    if player == None:
        player = LushRoomsPlayer(None, None, scheduler, tfipcon)
    sleep(0.5)
    mp3_filename = "/media/usb/uploads/idle.mp3"
    srt_filename = os.path.splitext(mp3_filename)[0]+".srt"
    player.start(mp3_filename, None, srt_filename)
    # sleep(5.5)
    # player.stop()
    # player.exit()
    # player.__del__()
    # player = None
    # killOmx()


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
    global player, scheduler, tfipcon
    def get(self):

        print(GetTrackList)

        global NEW_TRACK_ARRAY
        global NEW_SRT_ARRAY
        global BUILT_PATH
        global player

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
        # print(NEW_TRACK_ARRAY)
        # print(NEW_SRT_ARRAY)
        if player:
            player.setPlaylist(NEW_TRACK_ARRAY)
            player.lighting.resetHUE()
            player.lighting.resetDMX()
        else:
            player = LushRoomsPlayer(NEW_TRACK_ARRAY, MEDIA_BASE_PATH, scheduler, tfipcon)
            player.lighting.resetHUE()
            player.lighting.resetDMX()

        return jsonify(NEW_TRACK_ARRAY)


class PlaySingleTrack(Resource):
    def get(self):
        global player, paused
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
        paused = False

        return jsonify(duration)

class PlayPause(Resource):
    def get(self):
        global player, paused
        duration = player.playPause()
        paused = not paused
        return jsonify(duration)

class FadeDown(Resource):
    def get(self):
        global player, paused
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
        global player, paused
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
        global player, scheduler, tfipcon

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
            player = LushRoomsPlayer(None, None, scheduler, tfipcon)

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
        global player, scheduler, tfipcon
        body = request.get_json(force=True)

        print("SR Trigger received:")
        print(body)

        if body:
            if body['trigger'] == "start" and body["upload_path"]:
                print("SR Trigger received: start")
                mp3_filename = body["upload_path"]
                srt_filename = os.path.splitext(mp3_filename)[0]+".srt"
                print(mp3_filename, srt_filename)
                if player == None:
                    print("SR Trigger play - restarting LushRoomsPlayer")
                    player = LushRoomsPlayer(None, None, scheduler, tfipcon)
                    player.start(mp3_filename, None, srt_filename)
                    return jsonify({'response': 200, 'description': 'ok!'})
                else:
                    player.start(mp3_filename, None, srt_filename)
                    return jsonify({'response': 200, 'description': 'ok!'})

            elif body['trigger'] == "stop":
                print("SR Trigger received: stop")
                # TODO: make this better
                # Python, your flexibility is charming but also _scary_
                if player != None:
                    print("SR Trigger received: player existing")
                    try:
                        # for the ScentRoom, RGB value for warm white for both RGBW downlight and side RGB lights
                        # The eighth channel of 255 is needed for whatever reason, I don't have time
                        # to find out why right now
                        # matched white light RGB: 255, 241, 198, 255
                        if player.lighting.dmx:
                            player.lighting.dmx.write_frame([0, 0, 0, 255, 30, 30, 30, 0])
                        # player.playPause()
                        # player.stop()
                        # player.exit()
                        # player.__del__()
                        # player = None
                        # killOmx()
                        # scheduler.print_jobs()
                        # status = "Paused"
                        # return jsonify({'response': 200, 'description': 'ok!'})
                    except Exception as e:
                        logging.error("Could not kill lighting, things have gotten out of sync...")
                        logging.info("Killing everything anyway!")
                        print("Why: ", e)
                        player.stop()
                        player.exit()
                        player.__del__()
                        player = None
                        # killOmx()
                        # scheduler.print_jobs()
                        # status = "Paused"
                        # return jsonify({'response': 200, 'description': 'lighting out of sync'})
                    # else:
                    player.stop()
                    player.exit()
                    player.__del__()
                    player = None

                    # print("SR Trigger stop - restarting LushRoomsPlayer")
                    # player = LushRoomsPlayer(None, None, scheduler, tfipcon)
                    # if player.lighting.dmx:
                    #     player.lighting.dmx.write_frame([0, 0, 0, 255, 30, 30, 30, 0])
                    scheduler.print_jobs()
                    status = "Paused"

                return jsonify({'response': 200, 'description': 'ok!'})

            else:
                return jsonify({'response': 500, 'description': 'not ok!', "error": "Unsupported trigger"})

        else:
            return jsonify({'response': 500, 'description': 'not ok!', "error": "Incorrect body format"})

class ScentRoomReboot(Resource):
    def get(self):
        global player, scheduler, tfipcon
        try:
            player = LushRoomsPlayer(None, None, scheduler, tfipcon)
            sleep(1)
            if player.lighting:
                player.lighting.dmx.write_frame([0, 150, 0, 255, 0, 150, 0, 0])
                sleep(0.2)
                player.lighting.dmx.write_frame([0, 0, 0, 0, 0, 0, 0, 0])
                sleep(0.2)
                player.lighting.dmx.write_frame([0, 150, 0, 255, 0, 150, 0, 0])
                sleep(0.2)
                player.lighting.dmx.write_frame([0, 0, 0, 0, 0, 0, 0, 0])
            player.stop()
            player.exit()
            player.__del__()
            player = None
            killOmx()
            return jsonify({'response': 200, 'description': 'ok!'})
        except Exception as e:
            print("Reboot sequence failed: ", e)
            return jsonify({'response': 500, 'description': 'not ok!'})

class ScentRoomIdle(Resource):
    def get(self):
        global player, scheduler, tfipcon
        try:
            print("SR Trigger idle - restarting LushRoomsPlayer")
            if player == None:
                player = LushRoomsPlayer(None, None, scheduler, tfipcon)
            sleep(0.5)
            mp3_filename = "/media/usb/uploads/idle.mp3"
            srt_filename = os.path.splitext(mp3_filename)[0]+".srt"
            player.start(mp3_filename, None, srt_filename)
            sleep(5.5)
            player.stop()
            player.exit()
            player.__del__()
            player = None
            killOmx()
            return jsonify({'response': 200, 'description': 'ok!'})
        except Exception as e:
            print("Idle sequence failed: ", e)
            return jsonify({'response': 500, 'description': 'not ok!'})

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
api.add_resource(ScentRoomReboot, '/scentroom-reboot') # GET
api.add_resource(ScentRoomIdle, '/scentroom-idle') # GET

if __name__ == '__main__':
    tfipcon.connect(HOST, PORT)
    settings_json = settings.get_settings()
    if settings_json['activate_idle_loop'] == "true":
        scheduler.add_job(idleLoop, 'interval', seconds=8, misfire_grace_time=None, max_instances=1, coalesce=False)

    idle_lighting_player = LushRoomsLighting(scheduler, tfipcon)
    srtFilename = "/media/usb/uploads/idle.srt"
    subs = srtopen(srtFilename)
    idle_lighting_player.start(None, subs)

    sleep(8)

    # app.run(use_reloader=False, debug=settings_json["debug"], port=os.environ.get("PORT", "80"), host='0.0.0.0')
    app.run(use_reloader=False, debug="true", port=os.environ.get("PORT", "80"), host='0.0.0.0')
