from os import uname, system
from time import sleep
from platform_helpers import killOmx
from omxplayer.player import OMXPlayer  # pylint: disable=import-error
import ntplib  # pylint: disable=import-error
from time import ctime
import pause  # pylint: disable=import-error
import datetime
import os
import json
import settings


class OmxPlayer():
    def __init__(self):
        self.player = None
        self.settings_json = settings.get_settings()
        self.initialVolumeFromSettings = int(
            self.settings_json["audio_volume"])

    def setVolume(self, value_0_to_100):
        print("setVolume: Setting volume to: " + str(value_0_to_100))
        value_0_to_10_f = float(value_0_to_100)/100.0
        self.player.set_volume(value_0_to_10_f)
        return value_0_to_100

    def getVolume(self):
        return int(self.player.volume() * 100)

    def setDefaultVolumeFromSettings(self):
        print(
            "setDefaultVolumeFromSettings: Setting volume to: " + str(self.initialVolumeFromSettings))
        return self.setVolume(self.initialVolumeFromSettings)

    def waitUntilPlaying(self):
        while not self.player.is_playing():
            # TODO - THIS PAUSE MIGHT BE CRUCIAL FOR the 'position' to be returned correctly?
            sleep(0.0001)

    def waitUntilNotPlaying(self):
        while self.player.is_playing():
            sleep(0.0001)

    def triggerStart(self, pathToTrack, withPause=False, loop=False):
        # lrpi_player#105
        # Audio output can be routed through hdmi or the jack,
        # if settings.json is corrupted, default to the hdmi

        output_route = self.settings_json.get("audio_output")
        normalised_output_route = 'hdmi'
        omxArgs = []

        if output_route == 'hdmi':
            normalised_output_route = 'hdmi'
            omxArgs += ['-w', '--layout', '5.1']
        elif output_route == 'jack':
            normalised_output_route = 'local'

        omxArgs += ['-o', normalised_output_route]

        if loop:
            omxArgs += ['--loop']

        print('OUTPUT: ' + normalised_output_route)
        print('Full playing args: ' + str(omxArgs))

        if not withPause:
            self.player = OMXPlayer(
                pathToTrack, args=omxArgs, dbus_name='org.mpris.MediaPlayer2.omxplayer0')
            self.waitUntilPlaying()
        elif withPause:
            self.player = OMXPlayer(
                pathToTrack, args=omxArgs, dbus_name='org.mpris.MediaPlayer2.omxplayer0', pause=True)
            # Might need to set the volume to 0 a different way,
            # i.e. via the OS driver
            #
            # omxplayer plays a short, sharp, shock
            # before setting the volume to 0
            self.player.set_volume(0)
            self.waitUntilNotPlaying()
            self.seek(0)

    def primeForStart(self, pathToTrack, loop=False):
        self.triggerStart(pathToTrack, withPause=True, loop=loop)

    def start(self, pathToTrack, master=False, slave=False, loop=False):
        print("************* IN OMX START: master = " +
              str(master) + " slave = " + str(slave))
        print("Looping? :", loop)
        print("\n")
        print(pathToTrack)

        try:
            if master or slave:
                # we're in pairing mode, the player is already
                # primed and loaded. We just need to press play
                # todo: it's not yet primed and loaded for Mpv...
                print("*** Attempting to unpause playing after priming ***")
                self.playPause()
            else:
                print("*** RESETTING AUDIO PLAYER ***")
                if self.player:
                    self.player.quit()
                self.player = None
                self.triggerStart(pathToTrack, loop=loop)

            self.setDefaultVolumeFromSettings()

            self.waitUntilPlaying()

            return str(self.player.duration())
        except Exception as e:
            print("ERROR: Could not start player... but audio may still be playing!")
            print("Why: ", e)
            print("returning position 0...")
            return str(0)

    # action 16 is emulated keypress for playPause
    def playPause(self):
        print("OMX Playpausing")
        PLAY_PAUSE_EMULATED_KEY = 16
        self.player.action(PLAY_PAUSE_EMULATED_KEY)
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
                self.player.set_volume(
                    self.player.volume() - ((1.0/interval)/4.0))
                return True
        return False

    def seek(self, position0_to_100):
        position_as_float = float(position0_to_100)
        new_position = self.player.duration()*(position_as_float/100.0)
        if self.player.can_seek():
            self.player.set_position(new_position)
        return new_position

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
                status["volume"] = self.getVolume()
            except Exception as e:
                status["playerState"] = ""
                status["canControl"] = False
                status["error"] = "Something went wrong with player status request: " + \
                    str(e)

        else:
            status["playerState"] = ""
            status["canControl"] = False
            status["error"] = "Player is not initialized!"
            status["position"] = ''
            status["trackDuration"] = ''

        return status

    def exit(self):
        self.__del__()

    def __del__(self):
        try:
            if self.player:
                self.player.quit()
            self.player = None
        except Exception as e:
            print("Could not __del__ Omxplayer")
            print(e)
        finally:
            killOmx()
            print("OMX died")
