from os import uname

def findArm():
    return uname().machine == 'armv7l'

if findArm():
    from omxplayer.player import OMXPlayer
else: 
    import vlc

class VlcPlayer():
    def __init__(self, player):
        self.player = player

    def play(self):
        print("Playing on vlc...")

    def getPosition(self):
        print("0:00")

    def pause(self):
        print("Pausing...")

    def stop(self):
        print("Stopping...")

    def next(self):
        print("Skipping forward...")

    def previous(self):
        print("Skipping back...")

    def __del__(self):
        print("OMX died")


class OmxPlayer():
    def __init__(self, player):
        self.player = player

    def play(self):
        print("Playing on vlc...")

    def getPosition(self):
        print("0:00")

    def pause(self):
        print("Pausing...")

    def stop(self):
        print("Stopping...")

    def next(self):
        print("Skipping forward...")

    def previous(self):
        print("Skipping back...")

    def __del__(self):
        print("OMX died")

class LushRoomPlayer:
    def __init__(self, playlist):
        if uname().machine:
            self.playerType = "OMX"
            self.player = None
        else:
            self.playerType = "VLC"
            self.player = None

        self.playlist = playlist
        self.paused = None 
        

    def setPlaylist(self, playlist):
        self.playlist = playlist

    def getPlaylist(self):
        if len(self.playlist):
            return self.playlist
        else:
            return False
    
    def getPlayerType(self):
        return self.playerType

    def __del__(self):
        self.player.__del__()
        print("Player died")


