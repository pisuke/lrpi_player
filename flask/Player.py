import os
from os import uname, system
from time import sleep
import urllib.request
from Lighting import LushRoomsLighting


# utils

def findArm(): 
    return uname().machine == 'armv7l' 

if findArm():
    from OmxPlayer import OmxPlayer
else: 
    from VlcPlayer import VlcPlayer

class LushRoomsPlayer():
    def __init__(self, playlist, basePath):
        if uname().machine == 'armv7l':
            # we're likely on a 'Pi
            self.playerType = "OMX"
            print('Spawning omxplayer')
            self.player = OmxPlayer()
        else:
            # we're likely on a desktop
            print('Spawning vlc player')
            self.playerType = "VLC"
            self.player = VlcPlayer()

        self.lighting = LushRoomsLighting()
        self.basePath = basePath
        self.started = False
        self.playlist = playlist
        self.paired = False
        self.status = {
            "source" : "",
            "srtSource" : "",
            "playerState" : "",
            "canControl" : "",
            "paired" : self.paired,
            "position" : "",
            "trackDuration" : "",
            "playerType": self.playerType,
            "playlist": self.playlist,
            "error" : ""
        }
        self.subs = None
 
    def getPlayerType(self):
        return self.playerType

    # Returns the current position in secoends
    def start(self, path, subs, subsPath):
        self.started = True
        response = self.player.start(path)
        self.status["subsPath"] = subsPath
        try:
            print('In Player: ', id(self.player))
            self.lighting.start(self.player, subs) 
        except Exception as e:
            print('Lighting failed: ', e)  

        return response

    def playPause(self):
        response = self.player.playPause()
        try:
            print('In Player: ', id(self.player))
            self.lighting.playPause(self.getStatus()["playerState"]) 
        except Exception as e:
            print('Lighting failed: ', e)
        return response

    def stop(self):
        try:
            print('Stopping...')
            self.lighting.exit()
            self.player.exit()
            return 0
        except Exception as e:
            print("stop e: ", e)
            return 1

    def setPlaylist(self, playlist):
        self.playlist = playlist
        self.status["playlist"] = playlist
 
    def getPlaylist(self):
        if len(self.playlist):
            return self.playlist
        else:
            return False

    def next(self):
        print("Skipping forward...")

    def previous(self):
        print("Skipping back...")

    def fadeDown(self, path, interval, subs, subsPath):
        if interval > 0: 
            while self.player.volumeDown(interval):
                sleep(1.0/interval)
        self.player.exit() 
        self.lighting.exit() 
        response = self.player.start(path)
        self.status["subsPath"] = subsPath
        try:
            print('In Player: ', id(self.player))
            self.lighting.start(self.player, subs) 
        except Exception as e:
            print('Lighting failed: ', e) 

        return response

    def seek(self, position):
        if self.started:
            self.lighting.seek()
            return self.player.seek(position)

    def getStatus(self):
        return self.player.status(self.status)

    # Method called by the master

    def pair(self, hostname): 
        response = os.system("ping -c 1 " + hostname)
        if response == 0:
            print(hostname, 'is up!')
            slaveUrl = "http://" + hostname
            print("slaveUrl: ", slaveUrl)
            statusRes = urllib.request.urlopen(slaveUrl + "/status").read()
            print("status: ", statusRes)
            if statusRes:
                print('Attempting to enslave: ' + hostname)
                enslaveRes = urllib.request.urlopen(slaveUrl + "/enslave").read()
                print('res from enslave: ', enslaveRes)

        else:
            print(hostname, 'is down!')

        self.player.setPaired(True)

        return 0

    # Method called by the slave

    def setPaired(self, val): 
        self.player.setPaired(val)

    # When this player is enslaved, map the status of the 
    # master to a method

    def commandFromMaster(self, masterStatus, command, startTime):
        if self.paired:
            print('command from master: ', command)
            print('Master status: ', masterStatus)
        else:
            print('Not paired, cannot accept master commands')


    def exit(self):
        self.player.exit()

    # mysterious Python destructor...

    def __del__(self):
        self.player.__del__()
        print("LRPlayer died")