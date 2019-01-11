#
#
# Clearing omxplayer temporary files sometimes solves the issue,
# sometimes it doesnt...
# sudo rm -rf /tmp/omxplayerdbus*
# 
#

from flask import Flask, request, send_from_directory, render_template
from flask_cors import CORS, cross_origin
from flask_restful import Resource, Api
from json import dumps
from flask_jsonpify import jsonify
from flask_restful import reqparse

from os.path import splitext
import os
import os.path
import sys
import time
import subprocess
import json
import random
from pathlib import Path
from time import sleep 

from LushRoomsPlayer import LushRoomsPlayer

mpegOnly = True
mlpOnly = False
allFormats = False

app = Flask(__name__,  static_folder='static')
api = Api(app)

MEDIA_BASE_PATH = "/media/usb/tracks/" 
BUILT_PATH = None
AUDIO_PATH_TEST_MP4 = "5.1_AAC_Test.mp4"
JSON_LIST_FILE = "content.json"

TEST_TRACK = MEDIA_BASE_PATH + AUDIO_PATH_TEST_MP4
NEW_TRACK_ARRAY = []
NEW_SRT_ARRAY = []


player = None
paused = None

CORS(app)

# utils

def getInput():
    parser = reqparse.RequestParser()
    parser.add_argument('id', help='error with id')
    parser.add_argument('interval', help='error with interval')
    args = parser.parse_args()
    return args

def printOmxVars():
    print("OMXPLAYER_LIB" in os.environ)
    print("LD_LIBRARY_PATH" in os.environ)
    print("OMXPLAYER_BIN" in os.environ)
    
# serve the angular app

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists("static/" + path):
        return send_from_directory('static/', path)
    else:
        return send_from_directory('static/', 'index.html')

# API endpoints

class GetTrackList(Resource): 
    def get(self): 
        global NEW_TRACK_ARRAY
        global NEW_SRT_ARRAY
        global BUILT_PATH
        global player
        
        BUILT_PATH = MEDIA_BASE_PATH
        args = getInput()
    
        print("track list id: " +  str(args['id']))
        
        if args['id']:
            if NEW_TRACK_ARRAY:
                BUILT_PATH += [x['Path'] for x in NEW_TRACK_ARRAY if x['ID'] == args['id']][0] + "/"
                print(BUILT_PATH[0]) 

        print('BUILT_PATH: ' + str(BUILT_PATH))

        if player:
            player.exit() 
            
        with open(BUILT_PATH + JSON_LIST_FILE) as data:
            TRACK_ARRAY_WITH_CONTENTS = json.load(data)
            NEW_SRT_ARRAY = TRACK_ARRAY_WITH_CONTENTS

            if mpegOnly: 
                NEW_TRACK_ARRAY = [x for x in TRACK_ARRAY_WITH_CONTENTS if ((x['Name'] != JSON_LIST_FILE) and (splitext(x['Name'])[1].lower() != ".srt") and (splitext(x['Name'])[1].lower() != ".mlp"))]
            elif mlpOnly:
                NEW_TRACK_ARRAY = [x for x in TRACK_ARRAY_WITH_CONTENTS if ((x['Name'] != JSON_LIST_FILE) and (splitext(x['Name'])[1].lower() != ".srt") and (splitext(x['Name'])[1].lower() != ".mp4"))]
            elif allFormats:
                NEW_TRACK_ARRAY = [x for x in TRACK_ARRAY_WITH_CONTENTS if ((x['Name'] != JSON_LIST_FILE) and (splitext(x['Name'])[1].lower() != ".srt"))]


            NEW_SRT_ARRAY = [x for x in TRACK_ARRAY_WITH_CONTENTS if splitext(x['Name'])[1].lower() == ".srt"]
            #print(NEW_TRACK_ARRAY)
            #print( NEW_SRT_ARRAY)
            if player:
                player.setPlaylist(NEW_TRACK_ARRAY) 
            else:
                player = LushRoomsPlayer(NEW_TRACK_ARRAY, MEDIA_BASE_PATH)

            return jsonify(NEW_TRACK_ARRAY)
            
class PlaySingleTrack(Resource):
    def get(self):
        global player
        global paused
        global BUILT_PATH

        args = getInput()

        for track in NEW_TRACK_ARRAY:
            if track["ID"] == args["id"]:
                srtFileName = splitext(track["Path"])[0]+".srt"
                if os.path.isfile(BUILT_PATH + srtFileName):
                    print(srtFileName)
                pathToTrack = BUILT_PATH + track["Path"]

        if os.path.isfile(pathToTrack) == False:
            print('Bad file path, will not attempt to play...')
            return jsonify("(Playing) File not found!")

        print("Playing: " + pathToTrack)
            
        duration = player.start(pathToTrack)
            
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
        print('argsid: ', args["id"])
        # print('argsinterval: ', args["interval"])

        for track in NEW_TRACK_ARRAY:
            if track["ID"] == args["id"]:
                srtFileName = splitext(track["Path"])[0]+".srt"
                if os.path.isfile(BUILT_PATH + srtFileName):
                    print(srtFileName)
                pathToTrack = BUILT_PATH + track["Path"]

        if os.path.isfile(pathToTrack) == False:
            print('Bad file path, will not attempt to play...')
            return jsonify(1)

        response = player.fadeDown(pathToTrack, int(args["interval"]))

        return jsonify(response)

# URLs are defined here

api.add_resource(GetTrackList, '/get-track-list')
api.add_resource(PlaySingleTrack, '/play-single-track')
api.add_resource(PlayPause, '/play-pause')
api.add_resource(FadeDown, '/crossfade')

if __name__ == '__main__':
   app.run(debug=True, port=80, host='0.0.0.0')
