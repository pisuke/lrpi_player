# Clearing omxplayer temporary files sometimes solves the issue,
# sometimes it doesnt...
# sudo rm -rf /tmp/omxplayerdbus*
# 

from flask import Flask, request, send_from_directory, render_template
from flask_cors import CORS, cross_origin
from flask_restful import Resource, Api
from json import dumps
from flask_jsonpify import jsonify
from flask_restful import reqparse

import os
import os.path
import sys
import time
import subprocess
import json
import random

app = Flask(__name__,  static_folder='static')
api = Api(app)
player = None

TRACK_BASE_PATH = "/media/usb/demo/"
AUDIO_PATH_TEST_MP4 = "5.1_AAC_Test.mp4"

TEST_TRACK = TRACK_BASE_PATH + AUDIO_PATH_TEST_MP4
NEW_TRACK_ARRAY = []
paused = None

CORS(app)

def findArm():
    if os.uname().machine == 'armv7l':
        return True
    return False

if findArm():
    from omxplayer.player import OMXPlayer
    from pathlib import Path
    from time import sleep

# player = OMXPlayer(AUDIO_PATH_MLP, args=['--layout', '5.1', '-w', '-o', 'hdmi'])

# serve the angular app

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists("static/" + path):
        return send_from_directory('static/', path)
    else:
        return send_from_directory('static/', 'index.html')

def getIdInput():
    parser = reqparse.RequestParser()
    parser.add_argument('id', help='error with id')
    args = parser.parse_args()
    return args

def printOmxVars():
    print("OMXPLAYER_LIB" in os.environ)
    print("LD_LIBRARY_PATH" in os.environ)
    print("OMXPLAYER_BIN" in os.environ)

class GetFolderList(Resource): 
    def get(self): 
        global NEW_TRACK_ARRAY
        global paused
        global player
        paused = None
        # printOmxVars()
        if player:
            player.quit()
            print('Player exists and was quit!')
        with open(TRACK_BASE_PATH + 'tracks.json') as data:
            NEW_TRACK_ARRAY = json.load(data)
            for track in NEW_TRACK_ARRAY:
                track['Length'] = '5:00'
            # print(NEW_TRACK_ARRAY)
            return jsonify(NEW_TRACK_ARRAY)
 
class GetSingleTrack(Resource):
    def get(self):
        global NEW_TRACK_ARRAY
        args = getIdInput()
        print(args['id'])
        for track in NEW_TRACK_ARRAY:
            if track['ID'] == args['id']:
                return jsonify(track["Name"])

def posEvent(a, b):
    global player
    print('Position event!' + str(a) + " " + str(b))
    # print('Position: ' + str(player.position()) + "s")
    return
            
class PlaySingleTrack(Resource):
    def get(self):
        global player
        global paused
        if findArm():
            args = getIdInput()
            thisTrack = None
            print('argsid: ', args["id"])
            for track in NEW_TRACK_ARRAY:
                if track["ID"] == args["id"]:
                    thisTrack = track
                    pathToTrack = TRACK_BASE_PATH + track["Path"]
            if os.path.isfile(pathToTrack) == False:
                print('Bad file path, will not attempt to play...')
                return jsonify("(Playing) File not found!")
            print("Playing: " + pathToTrack)
            
            print('Spawning player')
            if (paused == True and paused is not None):
                player.pause() # emulated pause key
                sleep(2.5)
                paused = False
            else:
                # fixed to headphone port for testing
                print('path: ' + str(pathToTrack))
                player = OMXPlayer(pathToTrack, args=['-w', '-o', 'both']) 
                player.pause()
                sleep(2.5)
                player.positionEvent += posEvent 
                player.set_position(0)
                player.play()

            return jsonify("Playing track: " + track["Name"] + " length: " + str(player.metadata()['mpris:length']))
            #return jsonify("Playing track...")
            
            # while (player.playback_status() == 'Playing'):
            #     sleep(1)
            #     print(player.position())
                    
        return jsonify("(Playing) You don't seem to be on a media_warrior...")

# Currently seeks foward 10 seconds, works a few times but then comes back
# with something similar to:
#
# /usr/bin/omxplayer: line 67:  2225 Aborted                 LD_LIBRARY_PATH="$OMXPLAYER_LIBS${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" $OMXPLAYER_BIN "$@"
#
# or something even more worrying like:
# 
# *** Error in `/usr/bin/omxplayer.bin': corrupted double-linked list: 0x00d5ed78 ***
# /usr/bin/omxplayer: line 67:  2582 Segmentation fault      LD_LIBRARY_PATH="$OMXPLAYER_LIBS${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" $OMXPLAYER_BIN "$@"
#
# I've tried with as little at 1 second too, the problem remains. Could be
# because the files are so large?
# update, mp4s work a LOT better!
# There seems to be an intermittent issue where dbus loses connection to omxplayer though...
class ScrubFoward(Resource):
    def get(self):
        global player
        # printOmxVars()
        if findArm():
            # scrub the track
            # can_control() always seems to return false...
            #if player.can_control():
            if player.can_seek():
                player.seek(20.0)
                sleep(2.5)
                return jsonify("Scrub successful!")
            return jsonify("Must wait for scrub...")
        return jsonify("(Scrub) You don't seem to be on a media_warrior...")

class PauseTrack(Resource):
    def get(self):
        global player
        global paused
        if findArm():
            # Pause the track
            player.action(16)
            sleep(2.5)
            paused = True            
            return jsonify("Pause successful!") 
        return jsonify("(Pausing) You don't seem to be on a media_warrior...")
        
class StopAll(Resource):
    global player
    def get(self):
        if findArm():
            # For the moment, kill every omxplayer process
            os.system("killall omxplayer.bin")
            print('omxplayer processes killed!')
            sleep(2.5)
            #if player.can_control():
            #    player.exit()
            return jsonify("omxplayer processes killed")
        return jsonify("(Killing omxplayer proc) You don't seem to be on a media_warrior...")

api.add_resource(GetFolderList, '/get-track-list')
api.add_resource(GetSingleTrack, '/get-single-track')
api.add_resource(PlaySingleTrack, '/play-single-track')
api.add_resource(ScrubFoward, '/scrub-forward')
api.add_resource(PauseTrack, '/pause-track')
api.add_resource(StopAll, '/stop')

if __name__ == '__main__':
   app.run(debug=True, port=80, host='0.0.0.0')
