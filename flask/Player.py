import os
from os import uname, system
from time import sleep
import time
from time import perf_counter
import urllib.request
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib import parse
import requests
import ntplib  # pylint: disable=import-error
from time import ctime
import pause  # pylint: disable=import-error
from pysrt import open as srtopen  # pylint: disable=import-error
from pysrt import stream as srtstream
import datetime
import calendar
import json
import Profiling
from threading import Thread
import logging
logging.basicConfig(level=logging.INFO)

from Lighting import LushRoomsLighting
from platform_helpers import findArm

# utils

NTP_SERVER = 'ns1.luns.net.uk'


if findArm():
    from OmxPlayer import OmxPlayer
else:
    from VlcPlayer import VlcPlayer


class LushRoomsPlayer():
    def __init__(self, connections):
        if uname().machine == 'armv7l' or uname().machine == 'aarch64':
            # we're likely on a 'Pi 3
            self.playerType = "OMX"
            print('Spawning omxplayer')
            self.audioPlayer = OmxPlayer()
        else:
            # we're likely on a desktop
            print('Spawning vlc player')
            self.playerType = "VLC"
            self.audioPlayer = VlcPlayer()

        self.lighting = LushRoomsLighting(connections)
        self.basePath = "NONE SET"
        self.started = False
        self.playlist = []
        self.slaveCommandOffset = 2.5  # seconds
        self.slaveUrl = None
        self.paired = False
        self.isMaster = False
        self.isSlave = False
        self.masterIp = None
        self.status = {
            "source": "",
            "subsPath": "",
            "mediaBasePath": "",
            "playerState": "",
            "canControl": "",
            "position": "",
            "trackDuration": "",
            "playerType": self.playerType,
            "playlist": self.playlist,
            "error": "",
            "paired": self.paired,
            "slave_url": None,
            "master_ip": None
        }
        self.subs = None

    def getPlayerType(self):
        return self.playerType

    def loadSubtitles(self, subsPath):
        logging.info("Loading SRT file from path :: " + subsPath)
        if os.path.isfile(subsPath):
            profiledSrtOpen = Profiling.timing(srtopen, "Loading SRT file :: ")
            subs = profiledSrtOpen(subsPath)
            return subs
        else:
            logging.warning(
                "Subtitle track file " + subsPath + " is not valid. Subtitles will NOT be loaded")
            return None

    # Returns the current position in seconds
    def start(self, path, subs, subsPath, loop=False):
        self.audioPlayer.status(self.status)
        self.status["source"] = path
        self.status["subsPath"] = subsPath

        print("***************  player wrapper :: start  ********************")
        logging.debug('loopval: ', loop)

        # in party mode - these subs need to be loaded _before_ playback start
        # on the slave. Otherwise audio will _always_ play 'Total time elapsed'
        # seconds BEHIND on the slave
        if not self.isMaster and not self.isSlave:
            self.subs = self.loadSubtitles(subsPath)

        if self.isMaster:
            print('Master, sending start!')
            self.subs = self.loadSubtitles(subsPath)
            self.audioPlayer.primeForStart(path, loop=loop)
            print('Master :: PLAYER IS PRIMED')
            self.sendSlaveCommand('primeForStart')
            syncTime = self.sendSlaveCommand('start')
            self.pauseIfSync(syncTime)

        profiledAudioStarter = Profiling.timing(
            self.audioPlayer.start, "LushRoomsPlayer::Start")
        track_length_seconds = profiledAudioStarter(
            path,
            master=self.isMaster,
            slave=self.isSlave,
            loop=loop
        )
        self.started = True

        try:
            self.lighting.start(self.audioPlayer, self.subs)
        except Exception as e:
            print('Lighting start failed: ', e)

        return track_length_seconds

    def playPause(self, syncTime=None):

        if self.isMaster:
            print('Master, sending playPause!')
            syncTime = self.sendSlaveCommand('playPause')
            self.pauseIfSync(syncTime)

        response = self.audioPlayer.playPause()

        try:
            print('In Player: ', id(self.audioPlayer))
            self.lighting.playPause(self.getStatus()["playerState"])
        except Exception as e:
            print('Lighting playPause failed: ', e)

        return response

    def stop(self, syncTime=None):
        try:
            print('Stopping...')

            if self.isMaster:
                print('Master, sending stop!')
                syncTime = self.sendSlaveCommand('stop')
                self.pauseIfSync(syncTime)

            self.audioPlayer.exit()
            self.lighting.exit()

            self.playlist = []
            self.status["playlist"] = []

            return 0
        except Exception as e:
            print("stop failed: ", e)
            return 1

    def setMediaBasePath(self, basePath):
        self.basePath = basePath
        self.status["mediaBasePath"] = self.basePath
        return self

    def setPlaylist(self, playlist):
        self.playlist = playlist
        self.status["playlist"] = playlist
        return self

    def getPlaylist(self):
        if len(self.status["playlist"]):
            return self.status["playlist"]
        else:
            return False

    def resetLighting(self):
        if self.lighting:
            self.lighting.resetDMX()
            self.lighting.resetHUE()

    def fadeDown(self, path, interval, subs, subsPath, syncTimestamp=None):

        self.status["interval"] = interval
        if self.isMaster:
            print('Master, sending fadeDown!')
            syncTime = self.sendSlaveCommand('fadeDown')
            self.pauseIfSync(syncTime)

        if syncTimestamp:
            self.pauseIfSync(syncTimestamp)

        if interval > 0:
            while self.audioPlayer.volumeDown(interval):
                sleep(1.0/interval)
        self.audioPlayer.exit()

        if not self.isSlave:
            return self.start(path, subs, subsPath)
        else:
            return 0

    def seek(self, position_0_to_100):
        if self.started:
            if self.isMaster:
                print('Master, sending seek!')
                syncTime = self.sendSlaveCommand('seek', position_0_to_100)
                self.pauseIfSync(syncTime)

            newPos = self.audioPlayer.seek(position_0_to_100)
            self.lighting.seek(newPos)
            return newPos
        else:
            print("LushRoomsPlayer is NOT started - cannot seek!")

    def getStatus(self):
        self.status["slave_url"] = self.slaveUrl
        self.status["paired"] = self.paired
        self.status["master_ip"] = self.masterIp
        # todo - could add lighting status here too
        # current frame, tick info, etc?
        return self.audioPlayer.status(self.status)

    # Pair methods called by the master

    def pairAsMaster(self, hostname):
        response = os.system("ping -c 1 " + hostname)
        if response == 0:
            print(hostname, 'is up!')
            self.slaveUrl = "http://" + hostname
            print("slaveUrl: ", self.slaveUrl)
            statusRes = urllib.request.urlopen(
                self.slaveUrl + "/status").read()
            print("status: ", statusRes)
            if statusRes:
                print('Attempting to enslave: ' + hostname)
                enslaveRes = urllib.request.urlopen(
                    self.slaveUrl + "/enslave").read()
                print('res from enslave: ', enslaveRes)
                self.setSlaveUrl(self.slaveUrl).setPaired()
                self.isMaster = True

        else:
            print(hostname, 'is down! Cannot pair!')
            self.setSlaveUrl(None).setUnpaired()

        return 0

    def unpairAsMaster(self):
        print("slaveUrl: ", self.slaveUrl)
        statusRes = urllib.request.urlopen(self.slaveUrl + "/status").read()
        print("status: ", statusRes)
        if statusRes:
            print('Attempting to free the slave: ' + self.slaveUrl)
            freeRes = urllib.request.urlopen(self.slaveUrl + "/free").read()
            print('res from free: ', freeRes)
            if freeRes:
                self.setSlaveUrl(None).setUnpaired()
                self.isMaster = False
            else:
                print('Error freeing the slave, pairing may be stuck!')
                return 1

        return 0

    def setMasterIp(self, masterIp):
        self.masterIp = masterIp
        self.slaveUrl = None
        return self

    def setSlaveUrl(self, slaveUrl):
        self.slaveUrl = slaveUrl
        self.masterIp = None
        return self

    def setPaired(self):
        self.paired = True
        return self

    def setUnpaired(self):
        self.paired = False
        self.isMaster = False
        self.isSlave = False
        return self

    def free(self):
        self.setMasterIp(None).setUnpaired()
        self.resetLighting()
        self.audioPlayer.exit()
        return 0

    def pauseIfSync(self, syncTimestamp=None):
        print('synctime in LushRoomsPlayer: ',
              syncTimestamp, " :: ", syncTimestamp)
        if syncTimestamp:
            print("*" * 30)
            print("** syncTimestamp found for pairing mode!")
            print(
                "Pausing next LushRoomsPlayer command until " + str(syncTimestamp) + " time now is " + str(self.getLocalTimestamp()))
            print("*" * 30)
            pause.until(syncTimestamp)

    def getLocalTimestamp(self):
        return datetime.datetime.now()

    def commandFromMaster(self, masterStatus, command, position, startTime):
        """
            When this player is enslaved, map the status of the
            master to a method
        """
        if not self.paired:
            print('Not paired, cannot accept master commands')
            res = 1

        localTimestamp = self.getLocalTimestamp()

        print('commandFromMaster :: currentUnixTimestamp (local on pi: )',
              localTimestamp)

        res = 1

        try:

            print('command from master: ', command)
            print('master status: ', masterStatus)
            print('startTime: ', startTime)

            # All commands are mutually exclusive

            # We do not have a startTime for primeForStart, it is the precursor to
            # all other waits. The master will wait patiently until the slave
            # has been primed
            #
            # Note that _starting_ a track might take longer or shorted depending
            # on the implementation of self.audioPlayer. For the best pairing results, pair identical implementations

            if command == "primeForStart":
                pathToAudioTrack = masterStatus["source"]
                pathToSubsTrack = masterStatus["subsPath"]
                print("Slave :: priming slave player subtitles from " +
                      pathToSubsTrack)
                self.subs = self.loadSubtitles(pathToSubsTrack)
                print('Slave :: priming slave player with track ' + pathToAudioTrack)
                self.audioPlayer.primeForStart(pathToAudioTrack)
                print('Slave :: PLAYER IS PRIMED')

            # LushRooms player is presumed primed for all other commands!
            if command != "primeForStart":
                self.pauseIfSync(startTime)

            if command == "start":
                self.start(
                    masterStatus["source"],
                    None,
                    masterStatus["subsPath"]
                )

            if command == "playPause":
                self.playPause(startTime)

            if command == "stop":
                self.stop(startTime)

            if command == "seek":
                self.seek(position)

            if command == "fadeDown":
                self.fadeDown(masterStatus["source"],
                              masterStatus["interval"],
                              None,
                              masterStatus["subsPath"],
                              startTime)
            res = 0

            return res
        except Exception as e:
            print("Could not process command " +
                  str(command) + " from " + str(self.masterIp))
            print("Why :: ", e)
            # returning 0 here because I'm not sure what will
            # happen to the UI if a 1 is returned
            # TODO: test this!
            return 0

    def sendSlaveCommand(self, command, position=None):
        """
            When this player is acting as master, send commands to
            the slave with a 'sync_timestamp' timestamp
        """
        if self.paired:
            print('sending command to slave: ', command)
            try:
                localTimestamp = self.getLocalTimestamp()

                print('currentUnixTimestamp (local on pi: )', localTimestamp)

                self.eventSyncTime = localTimestamp + \
                    datetime.timedelta(seconds=self.slaveCommandOffset)

                print("*" * 30)
                print("MASTER SENDING COMMAND -> " + str(command) +
                      ", events sync at: " + str(self.eventSyncTime))
                print("*" * 30)

                # send the event sync time to the slave...

                self.audioPlayer.status(self.status)
                postFields = {
                    'command': str(command),
                    'position': str(position),
                    'master_status': self.getStatus(),
                    'sync_timestamp': str(self.eventSyncTime)
                }

                def slaveRequest():
                    slaveRes = requests.post(
                        self.slaveUrl + '/command', json=postFields)
                    print('command from slave, res: ', slaveRes.json())

                if command == "primeForStart":
                    # we only want the primeForStart command to be blocking.
                    # This way we can be absolutely sure that the play button
                    # on the slave player is ready to be pushed...
                    print("sending primeForStart command to slave")
                    slaveRequest()
                    print("after primeForStart response...")
                else:
                    # The slave might take an arbitrary amount of time to complete
                    # the command (e.g. fadeDown, lots of sleeps).
                    # Therefore, start it in a thread
                    # we don't often care about the result
                    print(
                        "sending command to slave where self.slaveUrl :: ", self.slaveUrl)
                    Thread(target=slaveRequest).start()
                    print("after thread finish...")

                return self.eventSyncTime

            except Exception as e:
                print('Could not send command to slave!')
                print('Why: ', e)

        else:
            print('Not paired, cannot send commands to slave')

        return None

    def exit(self):
        print("LushRoomsPlayer exiting...")
        self.stop()

    def __del__(self):
        """
            Called on `del lushroomsPlayerInstance`
        """
        try:
            self.stop()
            print("LushRoomsPlayer died via __del__")
        except Exception as e:
            print("Could not __del__ LushRoomsPlayer")
            print(e)
