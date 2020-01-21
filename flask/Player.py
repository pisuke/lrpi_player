import os
from os import uname, system
from time import sleep
import time
import urllib.request
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib import parse
import requests
import ntplib # pylint: disable=import-error
from time import ctime
import pause # pylint: disable=import-error
from pysrt import open as srtopen # pylint: disable=import-error
from pysrt import stream as srtstream
import datetime, calendar
import json

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
            self.player = OmxPlayer()
        else:
            # we're likely on a desktop
            print('Spawning vlc player')
            self.playerType = "VLC"
            self.player = VlcPlayer()

        self.lighting = LushRoomsLighting(connections)
        self.basePath = basePath
        self.started = False
        self.playlist = playlist
        self.slaveCommandOffset = 2.0 # seconds
        self.slaveUrl = None
        self.status = {
            "source" : "",
            "subsPath" : "",
            "playerState" : "",
            "canControl" : "",
            "paired" : False,
            "position" : "",
            "trackDuration" : "",
            "playerType": self.playerType,
            "playlist": self.playlist,
            "error" : "",
            "slave_url": None,
            "master_ip": None
        }
        self.subs = None

    def getPlayerType(self):
        return self.playerType

    def isMaster(self):
        print("isMaster",self.player.paired,self.status["master_ip"],self.player.paired and (self.status["master_ip"] is None))
        return self.player.paired and (self.status["master_ip"] is None)

    def isSlave(self):
        print("isSlave",self.player.paired,self.status["master_ip"],self.player.paired and (self.status["master_ip"] is None))
        return self.player.paired and (self.status["master_ip"] is not None)

    # Returns the current position in seconds
    def start(self, path, subs, subsPath, syncTime=None, loop=False):
        self.player.status(self.status)
        self.status["source"] = path
        self.status["subsPath"] = subsPath

        print("***************  start  ********************")

        print('loopval: ', loop)

        if os.path.isfile(subsPath):
            start_time = time.time()
            print("Loading SRT file " + subsPath + " - " + str(start_time))
            subs = srtopen(subsPath)
            #subs = srtstream(subsPath)
            end_time = time.time()
            print("Finished loading SRT file " + subsPath + " - " + str(end_time))
            print("Total time elapsed: " + str(end_time - start_time) + " seconds")

        if self.isSlave():
            # wait until the sync time to fire everything off
            print('Slave: Syncing start!')

        if self.isMaster():
            print('Master, sending start!')
            self.player.primeForStart(path, loop=loop)
            syncTime = self.sendSlaveCommand('start')

        self.started = True
        response = self.player.start(path, syncTime, master=self.isMaster(), loop=loop)

        try:
            print('In Player: ', id(self.player))
            self.lighting.start(self.player, subs)
        except Exception as e:
            print('Lighting failed: ', e)

        return response

    def playPause(self, syncTime=None):

        if self.isMaster():
            print('Master, sending playPause!')
            syncTime = self.sendSlaveCommand('playPause')

        response = self.player.playPause(syncTime)

        try:
            print('In Player: ', id(self.player))
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

            self.player.exit(syncTime)
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
            pause.until(syncTime)

        if syncTimestamp:
            pause.until(syncTimestamp)

        if interval > 0:
            while self.player.volumeDown(interval):
                sleep(1.0/interval)
        self.player.exit()

        if not self.isSlave():
            return self.start(path, subs, subsPath)
        else:
            return 0


    def seek(self, position):
        if self.started:
            newPos = self.player.seek(position)
            self.lighting.seek(newPos)
            return newPos

    def getStatus(self):
        self.status["slave_url"] = self.slaveUrl
        return self.player.status(self.status)

    # Pair methods called by the master

    def pairAsMaster(self, hostname):
        response = os.system("ping -c 1 " + hostname)
        if response == 0:
            print(hostname, 'is up!')
            self.slaveUrl = "http://" + hostname
            print("slaveUrl: ", self.slaveUrl)
            statusRes = urllib.request.urlopen(self.slaveUrl + "/status").read()
            print("status: ", statusRes)
            if statusRes:
                print('Attempting to enslave: ' + hostname)
                enslaveRes = urllib.request.urlopen(self.slaveUrl + "/enslave").read()
                print('res from enslave: ', enslaveRes)
                self.player.setPaired(True, None)

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
                self.player.setPaired(False, None)
            else:
                print('Error freeing the slave')
                return 1

        return 0

    # Methods called by the slave

    def setPairedAsSlave(self, val, masterIp):
        self.player.setPaired(val, masterIp)

    def free(self):
        if self.player.paired:
            self.player.setPaired(False, None)
            self.resetLighting()
            self.player.exit()
            return 0

    # When this player is enslaved, map the status of the
    # master to a method

    def commandFromMaster(self, masterStatus, command, startTime):
        res = 1
        if self.player.paired:

            print('command from master: ', command)
            print('master status: ', masterStatus)
            print('startTime: ', startTime)

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

    def sendSlaveCommand(self, command):
        if self.player.paired:
            print('sending command to slave: ', command)
            try:
                # tx_time is a unix timestamp
                # this, among a few other things, means 'party mode'
                # is only available on the 'Pi'/other unix like systems

                localTimestamp = calendar.timegm(datetime.datetime.now().timetuple())

                print('currentUnixTimestamp (local on pi: )', localTimestamp)
                self.eventSyncTime = localTimestamp + self.slaveCommandOffset
                print('events sync at: ', ctime(self.eventSyncTime))


                # send the event sync time to the slave...
                # if we don't get a response don't try and trigger the event!
                self.player.status(self.status)
                postFields = { \
                    'command': str(command), \
                    'master_status': self.getStatus(), \
                    'sync_timestamp': self.eventSyncTime \
                }
                slaveRes = requests.post(self.slaveUrl + '/command', json=postFields)
                print('command from slave, res: ', slaveRes)

                return self.eventSyncTime

            except Exception as e:
                print('Could not get ntp time!')
                print('Why: ', e)


        else:
            print('Not paired, cannot send commands to slave')

        return None


    def exit(self):
        self.player.__del__()

    # mysterious Python destructor...

    def __del__(self):
        self.player.__del__()
        print("LRPlayer died")
