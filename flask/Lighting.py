from phue import Bridge, PhueRegistrationException  # pylint: disable=import-error
from random import random
from time import sleep, time, perf_counter
from pysrt import SubRipFile, SubRipItem, SubRipTime  # pylint: disable=import-error
from pysrt import open as srtopen  # pylint: disable=import-error
from datetime import datetime, timedelta
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler  # pylint: disable=import-error
from tinkerforge.bricklet_dmx import BrickletDMX  # pylint: disable=import-error
from tf_device_ids import deviceIdentifiersList
from numpy import array, ones, zeros  # pylint: disable=import-error
import os
import json
import settings
import find_hue
import logging
from DmxInterpolator import DmxInterpolator

# dev

DEBUG = False
VERBOSE = False
SEEK_EVENT_LOG = False
LIGHTING_MSGS = False

# lighting

MAX_BRIGHTNESS = 200
DMX_FRAME_DURATION = 25
HUE_IP_ADDRESS = ""

logging.basicConfig(level=logging.INFO)

# utils


class LushRoomsLighting():

    def __init__(self, connections):
        print('Lushroom Lighting init!')
        self.PLAY_HUE = True
        self.PLAY_DMX = True
        self.TICK_TIME = 0.1  # seconds
        self.MENU_DMX_VAL = os.environ.get("MENU_DMX_VAL", None)
        self.NUM_DMX_CHANNELS = os.environ.get("NUM_DMX_CHANNELS", None)
        self.POD_MODE = self.MENU_DMX_VAL != None and self.NUM_DMX_CHANNELS != None
        self.TRANSITION_TIME = 5  # milliseconds
        self.hue_list = [[]]
        self.player = None
        self.job = None
        self.connections = connections

        self.scheduler = connections.scheduler
        self.dmx_interpolator = DmxInterpolator()

        # 'last_played' seems to be the last numbered lighting event
        # in the SRT file
        self.last_played = 0
        self.subs = ""

        # Hue
        self.bridge = None

        # DMX
        self.dmx = None
        self.tfIDs = connections.tfIDs
        self.ipcon = connections.tfIpCon

        self.deviceIDs = [i[0] for i in deviceIdentifiersList]
        self.startTime = perf_counter()

        if self.PLAY_DMX:
            self.initDMX()
        if self.PLAY_HUE:
            self.initHUE()

    # LIGHTING FUNCTION METHODS

    def initDMX(self):
        # configure Tinkerforge DMX
        logging.info("DMX init...")
        try:
            if DEBUG:
                print("Tinkerforge enumerated IDs", self.tfIDs)

            dmxcount = 0
            for tf in self.tfIDs:
                if len(tf[0]) <= 3:  # if the device UID is 3 characters it is a bricklet
                    if tf[1] in self.deviceIDs:
                        if VERBOSE:
                            print(tf[0], tf[1], self.getIdentifier(tf))
                    if tf[1] == 285:  # DMX Bricklet
                        if dmxcount == 0:
                            print(
                                "Registering %s as slave DMX device for playing DMX frames" % tf[0])
                            self.dmx = BrickletDMX(tf[0], self.ipcon)
                            self.dmx.set_dmx_mode(self.dmx.DMX_MODE_MASTER)
                            self.dmx.set_frame_duration(DMX_FRAME_DURATION)
                        dmxcount += 1

            if dmxcount < 1:
                if LIGHTING_MSGS:
                    print("No DMX devices found.")
        except Exception as e:
            print(
                "Could not create connection to Tinkerforge DMX. DMX lighting is now disabled")
            print("Why: ", e)
            self.PLAY_DMX = False

    def initHUE(self):
        logging.info("HUE init...")
        try:
            if self.PLAY_HUE:
                HUE_IP_ADDRESS = find_hue.hue_ip()

                if HUE_IP_ADDRESS == None:
                    print("HUE disabled in settings.json, HUE is now disabled")
                    self.PLAY_HUE = False
                    return

                self.bridge = Bridge(
                    HUE_IP_ADDRESS, config_file_path="/media/usb/python_hue")
                # If the app is not registered and the button is not pressed, press the button and call connect() (this only needs to be run a single time)
                self.bridge.connect()
                # Get the bridge state (This returns the full dictionary that you can explore)
                self.bridge.get_api()
                self.resetHUE()
                lights = self.bridge.lights
                self.hue_list = self.hue_build_lookup_table(lights)

                if LIGHTING_MSGS:
                    # Get a dictionary with the light name as the key
                    light_names = self.bridge.get_light_objects('name')
                    print("Light names:", light_names)
                    print(self.hue_list)
        except Exception as e:
            print("Could not create connection to Hue. Hue lighting is now disabled")
            print("Error: ", e)
            self.PLAY_HUE = False

    def resetDMX(self):
        try:
            logging.info("Directly resetting DMX...")
            if not self.POD_MODE:
                logging.info("Resetting in SPA mode...")
                self.dmx.write_frame([int(0.65*MAX_BRIGHTNESS),
                                      int(0.40*MAX_BRIGHTNESS),
                                      int(0.40*MAX_BRIGHTNESS),
                                      int(0.40*MAX_BRIGHTNESS),
                                      int(0.40*MAX_BRIGHTNESS),
                                      int(0.40*MAX_BRIGHTNESS),
                                      int(0.40*MAX_BRIGHTNESS),
                                      int(0.40*MAX_BRIGHTNESS),
                                      int(0.40*MAX_BRIGHTNESS),
                                      0, 0, 0, int(0.40*MAX_BRIGHTNESS)])
            elif self.POD_MODE:
                logging.info("Resetting in POD mode...")
                print('pod mode reset RGD menu values: ', self.MENU_DMX_VAL)
                print('pod mode number of DMX channels: ', self.NUM_DMX_CHANNELS)
                frame_arr = []
                menu_val_arr = self.MENU_DMX_VAL.split(",")
                menu_val_arr = [int(i) for i in menu_val_arr]
                for i in range(int(int(self.NUM_DMX_CHANNELS)/3)):
                    frame_arr += menu_val_arr
                self.dmx.write_frame(frame_arr)

        except Exception as e:
            logging.error("Could not connect to DMX daemon to reset!")
            logging.error(e)
            ########## TODO - THINK ABOUT THIS CAREFULLY #############
            logging.warning("Disabling DMX")
            self.PLAY_DMX = False
            ########## TODO - THINK ABOUT THIS CAREFULLY #############

    def resetHUE(self):
        if self.PLAY_HUE:
            logging.info("Directly resetting HUE...")
            for l in self.bridge.lights:
                l.on = True
            # Print light names
            # Set brightness of each light to 100
            for l in self.bridge.lights:
                if DEBUG:
                    print(l.name)
                l.brightness = 50
                bri = 50
                sat = 100
                hue = 0
                colortemp = 450
                cmd = {'transitiontime': int(self.TRANSITION_TIME), 'on': True, 'bri': int(
                    bri), 'sat': int(sat), 'hue': int(hue), 'ct': colortemp}
                self.bridge.set_light(l.light_id, cmd)

    def emptyDMXFrame(self):
        return zeros((512,), dtype=int)

    # LOW LEVEL LIGHT METHODS

    def getIdentifier(self, ID):
        """ Get TinkerForge device identifier """
        deviceType = ""
        for t in range(len(self.deviceIDs)):
            if ID[1] == deviceIdentifiersList[t][0]:
                deviceType = deviceIdentifiersList[t][1]
        return(deviceType)

    def tick(self):
        """ Callback that runs at every tick of the APScheduler to trigger lighting events """
        # get the float value of current time in seconds
        t = perf_counter()

        try:
            pp = self.player.getPosition()
            if DEBUG:
                logging.info("Player position: " + str(pp))
            if pp < 0:
                self.last_played = 0
                pp = 0
        except Exception as e:
            print(
                "Could not get the current position of the player, shutting down lighting gracefully...")
            logging.error(e)
            self.connections.reset_scheduler()

        # convert time in seconds to subtitle time
        pt = SubRipTime(seconds=pp)
        # convert time in seconds to subtitle time + the tick time increment
        ptd = SubRipTime(seconds=(pp+1*self.TICK_TIME))

        sub, i = self.find_subtitle(self.subs, pt, ptd, lo=self.last_played)

        if DEBUG:
            print(i, "Found Subtitle for light event:", sub, i)

        ## hours, minutes, seconds, milliseconds = time_convert(sub.start)
        ## t = seconds + minutes*60 + hours*60*60 + milliseconds/1000.0

        if sub != "":
            if LIGHTING_MSGS and DEBUG:
                print(i, "Light event:", sub)
            self.trigger_light(sub)
            self.last_played = i
            if DEBUG:
                print('last_played: ', i)

        ready_to_interpolate = self.dmx_interpolator.isRunning() and not \
            self.POD_MODE and self.PLAY_DMX and \
            self.PLAY_DMX and \
            self.dmx != None

        if ready_to_interpolate:
            iFrame = self.dmx_interpolator.getInterpolatedFrame(pt)
            self.dmx.write_frame(iFrame)

    def find_subtitle(self, subtitle, from_t, to_t, lo=0, backwards=False):
        i = lo

        if backwards and SEEK_EVENT_LOG:
            print("searching backwards!")

        # Find where we are
        subLen = len(subtitle)

        while (i < subLen):
            if (subtitle[i].start >= to_t and not backwards):
                break

            if backwards and (subtitle[i].start >= from_t):
                previous_i = max(0, i-1)
                if SEEK_EVENT_LOG:
                    print("In subs, at:", previous_i,
                          " found: ", subtitle[previous_i].text)
                return subtitle[previous_i].text, previous_i

            if (subtitle[i].start >= from_t) & (to_t >= subtitle[i].start):
                if not self.dmx_interpolator.isRunning():
                    self.dmx_interpolator.findNextEvent(i, subtitle)
                return subtitle[i].text, i
            i += 1

        return "", i

    def hue_build_lookup_table(self, lights):
        if DEBUG:
            print("hue lookup lights: ", lights)

        hue_l = [[]]
        i = 0
        for j in range(1+len(lights)+1):
            for l in lights:
                lname = str(l.name)
                if lname.find(str(j)) >= 0:
                    if LIGHTING_MSGS:
                        print(j, lname.find(str(j)), l.light_id,
                              l.name, l.bridge.ip, l.bridge.name)
                    if len(hue_l) <= j:
                        hue_l.append([l.light_id])
                    else:
                        hue_l[j].append(l.light_id)
            i += 1
        if DEBUG:
            print("hue_l: ", hue_l)
        return(hue_l)

    def trigger_hue(self, items, lums):
        hue, sat, bri, TRANSITION_TIME = items.split(',')
        bri = int((float(bri)/255.0)*int(MAX_BRIGHTNESS))
        cmd = {'transitiontime': int(TRANSITION_TIME), 'on': True, 'bri': int(
            bri), 'sat': int(sat), 'hue': int(hue)}

        if LIGHTING_MSGS:
            print("Trigger HUE", lums, cmd)
        if self.PLAY_HUE:
            for hl in self.hue_list[lums]:
                logging.info("Triggering HUE")
                self.bridge.set_light(hl, cmd)

    def trigger_dmx(self, items):
        if items == "":
            print("Empty DMX event found! Turning all DMX channels off...")
            channels = self.emptyDMXFrame()
        else:
            channels = array(items.split(",")).astype(int)

        if self.PLAY_DMX:
            # todo - uncomment!
            # logging.info("Writing DMX frame")
            self.dmx.write_frame(channels)

    def trigger_light(self, subs):
        if DEBUG:
            print("perf_count: ", perf_counter(), subs)

        commands = str(subs).split(";")

        for command in commands:
            try:
                # Parse the command from the current sub:
                scope, items = command[0:len(command)-1].split("(")

                if DEBUG:
                    print("sc[0:3]: ", scope[0:3], "it: ", items)

                if scope[0:3] == "HUE":
                    lums = int(scope[3:])
                    if VERBOSE:
                        print("Trigger HUE: ", lums)
                    self.trigger_hue(items, lums)

                if scope[0:3] == "DMX":
                    if LIGHTING_MSGS:
                        print("Trigger DMX :: ", items)

                    self.trigger_dmx(items)
            except:
                pass
        if LIGHTING_MSGS and DEBUG:
            print(30*'-')

    # PLAYER FUNCTION METHODS

    def time_convert(self, t):
        block, milliseconds = str(t).split(",")
        hours, minutes, seconds = block.split(":")
        return(int(hours), int(minutes), int(seconds), int(milliseconds))

    def start(self, audioPlayer, subs):
        self.player = audioPlayer
        self.subs = subs
        self.dmx_interpolator.__init__()
        self.startTime = perf_counter()
        subs_length = len(self.subs)
        if subs is not None:
            if LIGHTING_MSGS:
                print("Lighting: Start!")
                print('AudioPlayer: ', self.player)
                print("Number of lighting events: ", subs_length)
            # Trigger the first lighting event before the scheduler event starts
            self.triggerPreviousEvent(0)
            self.last_played = 0

            if subs_length == 1:
                if LIGHTING_MSGS:
                    print(
                        "There's only 1 lighting event, so no need to start the scheduler and unleash hell...")
            elif subs_length > 1:
                # https://www.joeshaw.org/python-daemon-threads-considered-harmful/
                self.connections.reset_scheduler()
                logging.info(
                    "**************ADDING TICK TO SCHEDULER**************")
                self.job = self.scheduler.add_job(
                    self.tick, 'interval', seconds=self.TICK_TIME, misfire_grace_time=None, max_instances=1, coalesce=False)

            if LIGHTING_MSGS:
                print("-------------")
        else:
            print(
                'Subtitle track not found/empty subtitle track. Lighting is now disabled')

    def playPause(self, status):

        print('Lighting PlayPause: ', status)
        if status == "Paused":
            self.scheduler.pause()
        elif status == "Playing":
            self.scheduler.resume()
        if LIGHTING_MSGS:
            print("-------------")

    def fadeDown(self, status):

        print("Lighting: fadeDown")
        self.last_played = 0

        if status == "Paused":
            self.scheduler.pause()
        elif status == "Playing":
            self.scheduler.resume()
        if LIGHTING_MSGS:
            print("-------------")

    def exit(self):
        self.__del__()

    def triggerPreviousEvent(self, pos):
        if LIGHTING_MSGS:
            print("Finding last lighting command from pos: ", pos)

        pp = pos
        pt = SubRipTime(seconds=pp)
        ptd = SubRipTime(seconds=(pp+1*self.TICK_TIME))

        if VERBOSE and DEBUG:
            print("Finding last light event, starting from: ")
            print("pt: ", ptd)
            print("ptd: ", ptd)

        sub, i = self.find_subtitle(self.subs, pt, ptd, backwards=True)

        if LIGHTING_MSGS:
            print("Seeking, found sub:", sub, " at pos: ", i)

        if sub != "":  # and i > self.last_played:
            if LIGHTING_MSGS and DEBUG:
                print(i, "Found last lighting event!:", sub)
            # print("Trigger light event %s" % i)
            self.trigger_light(sub)
            self.last_played = i
            if DEBUG:
                print('last_played: ', i)

    def seek(self, pos):
        # This doesn't seem to work fully...
        # But may be solved by LUSHDigital/lrpi_player#116
        # Get the last DMX and HUE events after a seek
        # Then trigger that...
        self.dmx_interpolator.__init__()
        self.triggerPreviousEvent(pos)

    def __del__(self):
        try:
            print("before Lighting obj reset :: ipcon: ", self.ipcon)
            self.connections.reset_scheduler()
            self.resetDMX()
            self.resetHUE()
        except Exception as e:
            print('Lighting destructor failed: ', e)
        if LIGHTING_MSGS:
            print("Lighting died!")


class ExitException(Exception):
    def __init__(self, key, scheduler, ipcon):
        if scheduler:
            for job in scheduler.get_jobs():
                print(job)
                job.remove()
            sleep(.5)
        exit(0)
