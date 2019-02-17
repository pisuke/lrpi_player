from os import uname, system
from time import sleep
from omxplayer.player import OMXPlayer # pylint: disable=import-error
import ntplib # pylint: disable=import-error
from time import ctime
import pause # pylint: disable=import-error

def killOmx():
    # This will only work on Unix-like (just Linux?) systems...
    try:
        system("killall omxplayer.bin")
        print('omxplayer processes killed!')
    except:
        print('How are you running omxplayer NOT on Linux?')
        exit(0)

class OmxPlayer():
    def __init__(self):
        self.player = None
        self.paired = False
        self.masterIp = None

    # omxplayer callbacks

    def posEvent(self, a, b):
        print('Position event!' + str(a) + " " + str(b))
        # print('Position: ' + str(player.position()) + "s")
        return

    def seekEvent(self, a, b):
        print('seek event! ' + str(b))
        return

    def start(self, pathToTrack, syncTimestamp=None):
        print("Playing on omx...") 
        print(pathToTrack)
        self.player = OMXPlayer(pathToTrack, args=['-w', '-o', 'both'], dbus_name='org.mpris.MediaPlayer2.omxplayer0', pause=True)
        # Might need to set the volume to 0 a different way,
        # for some tracks omxplayer plays a short, sharp, shock
        # before setting the volume to 0
        self.player.set_volume(0)
        sleep(2.5)
        self.player.positionEvent += self.posEvent
        self.player.seekEvent += self.seekEvent
        self.player.set_position(0)
        self.player.set_volume(1.0)

        if syncTimestamp:
            pause.until(syncTimestamp)

        self.player.play() 
        return str(self.player.duration())

    # action 16 is emulated keypress for playPause
    def playPause(self, syncTimestamp=None):
        print("Playpausing...")
        self.player.action(16)
        return str(self.player.duration())

    def getPosition(self):
        return self.player.position() 

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

    def seek(self, position, syncTimestamp=None):
        if self.player.can_seek():
            self.player.set_position(self.player.duration()*(position/100.0))
        return self.player.position()

    def status(self, status):
        if self.player != None:
            print('status requested!')
            status["source"] = self.player.get_source()
            status["playerState"] = self.player.playback_status()
            status["canControl"] = self.player.can_control()
            status["position"] = self.player.position()
            status["trackDuration"] = self.player.duration()
            status["error"] = ""
        else: 
            status["error"] = "Player is not initialized!"
        
        status["paired"] = self.paired
        status["master_ip"] = self.masterIp
            
        return status

    def setPaired(self, val, masterIp):
        self.paired = val
        self.masterIp = masterIp
        print('paired set to: ', val)
        print('master_ip set to: ', masterIp)
 
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