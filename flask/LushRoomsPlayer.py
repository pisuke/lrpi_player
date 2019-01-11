from os import uname
from time import sleep

def findArm():
    return uname().machine == 'armv7l'

if findArm():
    from omxplayer.player import OMXPlayer
else: 
    import vlc


class OmxPlayer():
    def __init__(self):
        self.player = None

    # omxplayer callbacks

    def posEvent(self, a, b):
        print('Position event!' + str(a) + " " + str(b))
        # print('Position: ' + str(player.position()) + "s")
        return

    def seekEvent(self, a, b):
        print('seek event! ' + str(b))
        return

    def start(self, pathToTrack, dbusId):
        print("Playing on omx...")
        print(pathToTrack)
        self.player = OMXPlayer(pathToTrack, args=['-w', '-o', 'both'], dbus_name='org.mpris.MediaPlayer2.omxplayer' + str(dbusId), pause=True)
        sleep(2.5)
        self.player.positionEvent += self.posEvent
        self.player.seekEvent += self.seekEvent
        self.player.set_position(0)
        self.player.play() 
        return str(self.player.duration())

    # action 16 is emulated keypress for playPause
    def playPause(self):
        print("Playpausing...")
        self.player.action(16)
        return str(self.player.duration())

    def getPosition(self):
        print("0:00")

    def getDuration(self):
        return str(self.player.duration())

    def pause(self):
        print("Pausing...")

    def stop(self):
        print("Stopping...")

    def crossfade(self, nextTrack):
        print("Crossfading...")

    def next(self):
        print("Skipping forward...")

    def previous(self):
        print("Skipping back...")

    def mute(self):
        print(self.player.volume())
        self.player.mute()

    def volumeUp(self):
        print("upper: ", self.player.volume())
        self.player.set_volume(self.player.volume() + 0.1)

    def volumeDown(self):
        print("downer: ", self.player.volume())
        self.player.set_volume(self.player.volume() - 0.25)

    def exit(self):
        if self.player:
            self.player.quit()
        else:
            return 1

    def __del__(self):
        if self.player:
            self.player.quit()
        print("OMX died")

class VlcPlayer():
    def __init__(self):
        self.ready = False
        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()

    def start(self, pathToTrack):
        self.media = self.vlc_instance.media_new('file://' + pathToTrack)
        self.player.set_media(self.media)
        self.player.play()
        self.player.pause()
        sleep(1.5)
        self.player.play()
        print("Playing on vlc...", self.player.get_length() / 1000)
        return self.player.get_length() / 1000     

    def playPause(self):
        print("Playpausing...", self.player.get_length() / 1000)
        self.player.pause()
        return self.player.get_length() / 1000

    def getPosition(self):
        print("0:00")

    def pause(self):
        self.player.pause()

    def stop(self):
        print("Stopping...")

    def crossfade(self, nextTrack):
        print("Crossfading...") 

    def next(self):
        print("Skipping forward...")

    def previous(self):
        print("Skipping back...")

    def mute(self):
        print(self.player.audio_get_volume())
        self.player.audio_set_volume(0)

    def volumeUp(self):
        self.player.audio_set_volume(self.player.audio_get_volume() + 10)

    def exit(self):
        if self.player:
            self.player.stop()
        else:
            return 1

    def __del__(self):
        print("VLC died")

class LushRoomsPlayer():
    def __init__(self, playlist, basePath):
        if uname().machine == 'armv7l':
            # we're likely on a 'Pi
            self.playerType = "OMX"
            print('Spawning omxplayer')
            self.player = OmxPlayer()
            self.crossfadePlayer = OmxPlayer()
        else:
            # we're likely on a desktop
            print('Spawning vlc player')
            self.playerType = "VLC"
            self.player = VlcPlayer()
            self.crossfadePlayer = VlcPlayer()

        self.basePath = basePath
        self.started = False
        self.playlist = playlist

    def getPlayerType(self):
        return self.playerType

    # Returns the current position in seconds
    def start(self, path):
        self.started = True
        return self.player.start(path, 0)

    def playPause(self):
        return self.player.playPause()

    def stop(self):
        self.player.stop()

    def setPlaylist(self, playlist):
        self.playlist = playlist

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
        for i in range(interval):
            print ("Fading: ", i)
            sleep(1)
            self.player.volumeDown()
        self.player.exit()
        return self.player.start(path, 0) 

    def exit(self):
        self.player.exit()

    # mysterious Python destructor...

    def __del__(self):
        self.player.__del__()
        print("LRPlayer died")


