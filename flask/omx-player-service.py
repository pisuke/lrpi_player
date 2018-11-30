from flask import Flask, request, send_from_directory, render_template
from flask_cors import CORS, cross_origin
from flask_restful import Resource, Api
from json import dumps
from flask_jsonpify import jsonify
from flask_restful import reqparse

import os
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

class GetTrackList(Resource): 
    def get(self): 
        global NEW_TRACK_ARRAY
        global paused
        paused = None
        os.system("killall omxplayer.bin")
        print('omxplayer processes killed!')
        with open('../tracks.json') as data:
            NEW_TRACK_ARRAY = json.load(data)
            for track in NEW_TRACK_ARRAY:
                track['Length'] = '5:00'
            print(NEW_TRACK_ARRAY)
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
                    pathToTrack = TRACK_BASE_PATH + track["Name"]
            print("Playing: " + pathToTrack)
            
            print('Spawning player')
            if (paused == True and paused is not None):
                player.action(16)
                paused = False
            else:
                player = OMXPlayer(pathToTrack, args=['-w']) 
                player.pause()
                sleep(2.5)
                player.positionEvent += posEvent 
                player.set_position(0)
                player.play()

            return jsonify("Playing track: " + track["Name"] + " length: " + str(player.metadata()['mpris:length']))
           
            while (player.playback_status() == 'Playing'):
                sleep(1)
                print(player.position())
            
                
            print("metadata: " + str(player.metadata()))
            print("Duration: " + str(player.metadata()['mpris:length']/1000/1000))

            sleep(5)
            
            print("Dur after 5: " + str(player.duration()))
        
        return jsonify("(Playing) You don't seem to be on a media_warrior...")

class ScrubFoward(Resource):
    def get(self):
        global player
        if findArm():
            # scrub the track
            player.seek(float(5.0))
            return jsonify("Scrub successful!") 
        return jsonify("(Scrub) You don't seem to be on a media_warrior...")

class PauseTrack(Resource):
    def get(self):
        global player
        global paused
        if findArm():
            # Pause the track
            player.action(16)
            paused = True            
            return jsonify("Pause successful!") 
        return jsonify("(Pausing) You don't seem to be on a media_warrior...")
        
class StopAll(Resource):
    def get(self):
        if findArm():
            # For the moment, kill every omxplayer process
            os.system("killall omxplayer.bin")
            print('omxplayer processes killed!')
            
            return jsonify("omxplayer processes killed")
        return jsonify("(Killing omxplayer proc) You don't seem to be on a media_warrior...")

api.add_resource(GetTrackList, '/get-track-list')
api.add_resource(GetSingleTrack, '/get-single-track')
api.add_resource(PlaySingleTrack, '/play-single-track')
api.add_resource(ScrubFoward, '/scrub-forward')
api.add_resource(PauseTrack, '/pause-track')
api.add_resource(StopAll, '/stop')

if __name__ == '__main__':
   app.run(debug=True, port=80, host='0.0.0.0')
