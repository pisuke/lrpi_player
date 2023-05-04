import os
from os import uname, system
from time import sleep
import time
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
from threading import Thread

from Lighting import LushRoomsLighting

# utils

NTP_SERVER = 'ns1.luns.net.uk'


def findArm():
    return uname().machine == 'armv7l'


if findArm():
    from OmxPlayer import OmxPlayer
else:
    from VlcPlayer import VlcPlayer


class LushRoomsPlayer():
    def __init__(self, playlist, basePath, connections):
        if uname().machine == 'armv7l':
            # we're likely on a 'Pi
            self.playerType = "OMX"
            print('Spawning omxplayer')
            self.audioPlayer = OmxPlayer()
        else:
            # we're likely on a desktop
            print('Spawning vlc player')
            self.playerType = "VLC"
            self.audioPlayer = VlcPlayer()

        self.lighting = LushRoomsLighting(connections)
        self.basePath = basePath
        self.started = False
        self.playlist = playlist
        self.slaveCommandOffset = 2.5  # seconds
        self.slaveUrl = None
        self.status = {
            "source": "",
            "subsPath": "",
            "playerState": "",
            "canControl": "",
            "paired": False,
            "position": "",
            "trackDuration": "",
            "playerType": self.playerType,
            "playlist": self.playlist,
            "error": "",
            "slave_url": None,
            "master_ip": None
        }
        self.subs = None

    def getPlayerType(self):
        return self.playerType

    def isMaster(self):
        print("isMaster", self.audioPlayer.paired, self.status["master_ip"], self.audioPlayer.paired and (
            self.status["master_ip"] is None))
        return self.audioPlayer.paired and (self.status["master_ip"] is None)

    def isSlave(self):
        print("isSlave", self.audioPlayer.paired, self.status["master_ip"], self.audioPlayer.paired and (
            self.status["master_ip"] is None))
        return self.audioPlayer.paired and (self.status["master_ip"] is not None)

    def loadSubtitles(self, subsPath):
        if os.path.isfile(subsPath):
            start_time = time.time()
            print("Loading SRT file " + subsPath + " - " + str(start_time))
            subs = srtopen(subsPath)
            # subs = srtstream(subsPath)
            end_time = time.time()
            print("Finished loading SRT file " +
                  subsPath + " - " + str(end_time))
            print("Total time elapsed: " +
                  str(end_time - start_time) + " seconds")
            return subs
        else:
            print(
                "Subtitle track file " + subsPath + " is not valid. Subtitles will NOT be loaded")
            return None

    # Returns the current position in seconds
    def start(self, path, subs, subsPath, syncTime=None, loop=False):
        self.audioPlayer.status(self.status)
        self.status["source"] = path
        self.status["subsPath"] = subsPath

        print("***************  player wrapper :: start  ********************")
        print('loopval: ', loop)

        # in party mode - these subs need to be loaded _before_ playback start
        # on the slave. Otherwise audio will _always_ play 'Total time elapsed'
        # seconds BEHIND on the slave
        if not self.isMaster() and not self.isSlave():
            self.subs = self.loadSubtitles(subsPath)

        if self.isSlave():
            # wait until the sync time to fire everything off
            print('Slave: Syncing start!')

        if self.isMaster():
            print('Master, sending start!')
            self.subs = self.loadSubtitles(subsPath)
            self.audioPlayer.primeForStart(path, loop=loop)
            self.sendSlaveCommand('primeForStart')
            syncTime = self.sendSlaveCommand('start')
            self.pauseIfSync(syncTime)

        self.started = True
        response = self.audioPlayer.start(
            path, syncTime, master=self.isMaster(), slave=self.isSlave(), loop=loop)

        try:
            self.lighting.start(self.audioPlayer, self.subs)
        except Exception as e:
            print('Lighting start failed: ', e)

        return response

    def playPause(self, syncTime=None):

        if self.isMaster():
            print('Master, sending playPause!')
            syncTime = self.sendSlaveCommand('playPause')
            self.pauseIfSync(syncTime)

        response = self.audioPlayer.playPause(syncTime)

        try:
            print('In Player: ', id(self.audioPlayer))
            self.lighting.playPause(self.getStatus()["playerState"])
        except Exception as e:
            print('Lighting playPause failed: ', e)

        return response

    def stop(self, syncTime=None):
        try:
            print('Stopping...')

            if self.isMaster():
                print('Master, sending stop!')
                syncTime = self.sendSlaveCommand('stop')
                self.pauseIfSync(syncTime)

            self.audioPlayer.exit(syncTime)
            self.lighting.exit()

            return 0
        except Exception as e:
            print("stop failed: ", e)
            return 1

    def setPlaylist(self, playlist):
        self.playlist = playlist
        self.status["playlist"] = playlist

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
        if self.isMaster():
            print('Master, sending fadeDown!')
            syncTime = self.sendSlaveCommand('fadeDown')
            self.pauseIfSync(syncTime)

        if syncTimestamp:
            self.pauseIfSync(syncTimestamp)

        if interval > 0:
            while self.audioPlayer.volumeDown(interval):
                sleep(1.0/interval)
        self.audioPlayer.exit()

        if not self.isSlave():
            return self.start(path, subs, subsPath)
        else:
            return 0

    def seek(self, position):
        if self.started:

            if self.isMaster():
                print('Master, sending seek!')
                syncTime = self.sendSlaveCommand('seek', position)
                self.pauseIfSync(syncTime)

            newPos = self.audioPlayer.seek(position)
            self.lighting.seek(newPos)
            return newPos

    def getStatus(self):
        self.status["slave_url"] = self.slaveUrl
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
                self.audioPlayer.setPaired(True, None)

        else:
            print(hostname, 'is down! Cannot pair!')

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
                self.audioPlayer.setPaired(False, None)
            else:
                print('Error freeing the slave')
                return 1

        return 0

    # Methods called by the slave

    def setPairedAsSlave(self, val, masterIp):
        self.audioPlayer.setPaired(val, masterIp)

    def free(self):
        if self.audioPlayer.paired:
            self.audioPlayer.setPaired(False, None)
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

    # When this player is enslaved, map the status of the
    # master to a method

    def commandFromMaster(self, masterStatus, command, position, startTime):

        localTimestamp = self.getLocalTimestamp()

        print('commandFromMaster :: currentUnixTimestamp (local on pi: )',
              localTimestamp)

        res = 1
        if self.audioPlayer.paired:

            print('command from master: ', command)
            print('master status: ', masterStatus)
            print('startTime: ', startTime)

            # All commands are mutually exclusive

            # We do not have a startTime for primeForStart, it is the precursor to
            # all other waits. The master will wait patiently until the slave
            # has been primed

            if command == "primeForStart":
                pathToAudioTrack = masterStatus["source"]
                pathToSubsTrack = masterStatus["subsPath"]
                print("Slave :: priming slave player subtitles from " +
                      pathToSubsTrack)
                self.subs = self.loadSubtitles(pathToSubsTrack)
                print('Slave :: priming slave player with track ' + pathToAudioTrack)
                self.audioPlayer.primeForStart(pathToAudioTrack)
                print('Slave :: PLAYER IS PRIMED')
            else:
                self.pauseIfSync(startTime)

            if command == "start":
                self.start(
                    masterStatus["source"],
                    None,
                    masterStatus["subsPath"],
                    startTime
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

        else:
            print('Not paired, cannot accept master commands')
            res = 1

        return res

    # When this player is acting as master, send commands to
    # the slave with a 'start' timestamp

    def sendSlaveCommand(self, command, position=None):
        if self.audioPlayer.paired:
            print('sending command to slave: ', command)
            try:
                localTimestamp = self.getLocalTimestamp()

                print('currentUnixTimestamp (local on pi: )', localTimestamp)

                self.eventSyncTime = localTimestamp + \
                    datetime.timedelta(0, self.slaveCommandOffset)

                # print("*" * 30)
                # print(
                #     f"MASTER COMMAND SENT {command}, events sync at: {self.eventSyncTime}")
                # print("*" * 30)

                # send the event sync time to the slave...
                # if we don't get a response don't try and trigger the event!
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
                    print('command from slave, res: ', slaveRes.json)

                if command == "primeForStart":
                    # we only want the primeForStart command to be blocking.
                    # This way we can be absolutely sure that the play button
                    # on the slave player is ready to be pushed...
                    slaveRequest()
                else:
                    # The slave might take an arbitrary amount of time to complete
                    # the command (e.g. fadeDown, lots of sleeps).
                    # Therefore, start it in a thread
                    # we don't often care about the result
                    Thread(target=slaveRequest).start()

                return self.eventSyncTime

            except Exception as e:
                print('Could not send command to slave!')
                print('Why: ', e)

        else:
            print('Not paired, cannot send commands to slave')

        return None

    def exit(self):
        self.audioPlayer.__del__()

    # mysterious Python destructor...

    def __del__(self):
        self.audioPlayer.__del__()
        print("LRPlayer died")
