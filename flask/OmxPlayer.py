from os import uname, system
from time import sleep
from omxplayer.player import OMXPlayer # pylint: disable=import-error
import ntplib # pylint: disable=import-error
from time import ctime
import pause # pylint: disable=import-error
import datetime
import os
import json
import settings

def killOmx():
    # This will only work on Unix-like (just Linux?) systems...
    try:
        system("killall omxplayer.bin")
        print('omxplayer processes killed!')
    except:
        print('How are you NOT running omxplayer on Linux?')
        exit(0)

class OmxPlayer():
    def __init__(self):
        self.player = None
        self.paired = False
        self.masterIp = None
        self.audio_volume = 100.0

    # omxplayer callbacks

    def posEvent(self, a, b):
        print('Position event!' + str(a) + " " + str(b))
        # print('Position: ' + str(player.position()) + "s")
        return

    def seekEvent(self, a, b):
        print('seek event! ' + str(b))
        return

    def primeForStart(self, pathToTrack):
        self.triggerStart(pathToTrack, withPause=True)

    def triggerStart(self, pathToTrack, withPause=False):
        # lrpi_player#105
        # Audio output can be routed through hdmi or the jack,
        # if settings.json is corrupted, default to the hdmi

        settings_json = settings.get_settings()
        output_route = settings_json.get("audio_output")
        normalised_output_route = 'hdmi'
        omxArgs = []

        if output_route == 'hdmi':
            normalised_output_route = 'hdmi'
            omxArgs += ['-w', '--layout', '5.1']
        elif output_route == 'jack':
            normalised_output_route = 'local'

        omxArgs += ['-o', normalised_output_route]

        print('OUTPUT: ' + normalised_output_route)
        print('Full playing args: ' + str(omxArgs))

        if not withPause:
            self.player = OMXPlayer(pathToTrack, args=omxArgs, dbus_name='org.mpris.MediaPlayer2.omxplayer0')
            sleep(0.25)
        elif withPause:
            self.player = OMXPlayer(pathToTrack, args=omxArgs, dbus_name='org.mpris.MediaPlayer2.omxplayer0', pause=True)
            # Might need to set the volume to 0 a different way,
            # for some tracks omxplayer plays a short, sharp, shock
            # before setting the volume to 0
            self.player.set_volume(0)
            sleep(0.5)

    def start(self, pathToTrack, syncTimestamp=None, master=False):
        print("Playing on omx... :", master)
        print("\n")
        print(pathToTrack)

        settings_json = settings.get_settings()
        volume = settings_json.get("audio_volume")

        try:
            if not master:
                if self.player:
                    self.player.quit()
                self.player = None

            if syncTimestamp:
                pause.until(syncTimestamp)

            if self.player is None or syncTimestamp is None:
                self.triggerStart(pathToTrack)

            self.player.positionEvent += self.posEvent
            self.player.seekEvent += self.seekEvent

            if volume is not None:
                self.audio_volume = volume
                print("Volume set to %s" % self.audio_volume)

            self.player.set_volume(float(self.audio_volume)/100.0)

            print('synctime in omxplayer: ', ctime(syncTimestamp))
            if master:
                self.player.play()
            return str(self.player.duration())
        except Exception as e:
            print("ERROR: Could not start player... but audio may still be playing!")
            print("Why: ", e)
            print("returning position 0...")
            return str(0)

    # action 16 is emulated keypress for playPause
    def playPause(self, syncTimestamp=None):
        print("Playpausing with syncTimeStamp: ", syncTimestamp)
        if syncTimestamp:
            pause.until(syncTimestamp)
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
        return self.player.duration()*(position/100.0)

    def status(self, status):
        if self.player != None:
            print('status requested from omxplayer!')
            try:
                status["source"] = self.player.get_source()
                status["playerState"] = self.player.playback_status()
                status["canControl"] = self.player.can_control()
                status["position"] = self.player.position()
                status["trackDuration"] = self.player.duration()
                status["error"] = ""
            except Exception as e:
                status["playerState"] = ""
                status["canControl"] = False
                status["error"] = "Something went wrong with player status request: " + str(e)

        else:
            status["playerState"] = ""
            status["canControl"] = False
            status["error"] = "Player is not initialized!"

        status["paired"] = self.paired
        status["master_ip"] = self.masterIp

        return status

    def setPaired(self, val, masterIp):
        self.paired = val
        self.masterIp = masterIp
        print('paired set to: ', val)
        print('master_ip set to: ', masterIp)

    def exit(self, syncTimestamp=None):
        if syncTimestamp:
            pause.until(syncTimestamp)
        self.__del__()

    def __del__(self):
        if self.player:
            self.player.quit()
        self.player = None
        killOmx()
        print("OMX died")
