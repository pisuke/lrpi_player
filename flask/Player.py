from os import uname, system
from time import sleep

def killOmx():
    # This will only work on Unix-like systems...
    system("killall omxplayer.bin")
    print('omxplayer processes killed!')


def findArm():
    return uname().machine == 'armv7l' 

if findArm():
    from omxplayer.player import OMXPlayer # pylint: disable=import-error
else: 
    import vlc


class OmxPlayer():
    def __init__(self):
        self.player = None
        self.paired = False

    # omxplayer callbacks

    def posEvent(self, a, b):
        print('Position event!' + str(a) + " " + str(b))
        # print('Position: ' + str(player.position()) + "s")
        return

    def seekEvent(self, a, b):
        print('seek event! ' + str(b))
        return

    def start(self, pathToTrack):
        print("Playing on omx...") 
        print(pathToTrack)
        self.player = OMXPlayer(pathToTrack, args=['-w', '-o', 'both'], dbus_name='org.mpris.MediaPlayer2.omxplayer0', pause=True)
        self.player.set_volume(0)
        sleep(2.5)
        self.player.positionEvent += self.posEvent
        self.player.seekEvent += self.seekEvent
        self.player.set_position(0)
        self.player.set_volume(1.0)
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

    def mute(self):
        print(self.player.volume())
        self.player.mute()

    def volumeUp(self):
        print("upper: ", self.player.volume())
        self.player.set_volume(self.player.volume() + 0.1)

    def volumeDown(self, interval):
        # If we're right at the end of the track, don't try to 
        # lower the volume or else dbus will disconnect and
        # the server will look at though it's crashed
        
        if self.player.duration() - self.player.position() > 1:
            print("omx downer: ", self.player.volume())
            if (self.player.volume() <= 0.07 or interval == 0):
                return False
            else:
                self.player.set_volume(self.player.volume() - ((1.0/interval)/4.0))
                return True 
        return False

    def seek(self, position):
        if self.player.can_seek():
            self.player.set_position(self.player.duration()*(position/100.0))
        return self.player.position()

    def status(self, status):
        if self.player != None:
            print('status requested!')
            status["source"] = self.player.get_source()
            status["playerState"] = self.player.playback_status()
            status["canControl"] = self.player.can_control()
            status["paired"] = self.paired
            status["position"] = self.player.position()
            status["trackDuration"] = self.player.duration()
            status["error"] = ""
        else: 
            status["error"] = "error: player is not initialized!"
            
        return status


    def exit(self):
        if self.player:
            self.player.quit()
            killOmx()
        else: 
            return 1

    def __del__(self):
        if self.player:
            self.player.quit()
            killOmx()
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
        self.player.audio_set_volume(50)
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

    def volumeDown(self, interval):
        print("vlc downer: ", self.player.audio_get_volume())
        if (self.player.audio_get_volume() <= 10 or interval == 0):
            return False
        else:
            self.player.audio_set_volume(self.player.audio_get_volume() - 100/interval)
            return True  

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
        else:
            # we're likely on a desktop
            print('Spawning vlc player')
            self.playerType = "VLC"
            self.player = VlcPlayer()

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
        self.player.stop()

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


