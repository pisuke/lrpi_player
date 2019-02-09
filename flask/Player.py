from os import uname, system
from time import sleep
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

        self.Lighting = LushRoomsLighting()
        self.basePath = basePath
        self.started = False
        self.playlist = playlist
        self.status = {
            "source" : "",
            "playerState" : "",
            "canControl" : "",
            "paired" : "",
            "position" : "",
            "trackDuration" : "",
            "playerType": self.playerType,
            "playlist": self.playlist,
            "error" : ""
        }

    def getPlayerType(self):
        return self.playerType

    # Returns the current position in secoends
    def start(self, path):
        self.started = True
        return self.player.start(path)

    def playPause(self):
        return self.player.playPause()

    def stop(self):
        try:
            print('Stopping...')
            self.player.exit()
            return 0
        except:
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

    def fadeDown(self, path, interval):
        if interval > 0: 
            while self.player.volumeDown(interval):
                sleep(1.0/interval)
        self.player.exit() 
        return self.player.start(path) 

    def seek(self, position):
        if self.started:
            return self.player.seek(position)

    def getStatus(self):
        return self.player.status(self.status)

    def exit(self):
        self.player.exit()

    # mysterious Python destructor...

    def __del__(self):
        self.player.__del__()
        print("LRPlayer died")