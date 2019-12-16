from phue import Bridge, PhueRegistrationException # pylint: disable=import-error
from random import random
from time import sleep, time, perf_counter
from pysrt import SubRipFile, SubRipItem, SubRipTime # pylint: disable=import-error
from pysrt import open as srtopen # pylint: disable=import-error
from datetime import datetime, timedelta
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler # pylint: disable=import-error
from tinkerforge.ip_connection import IPConnection # pylint: disable=import-error
from tinkerforge.bricklet_dmx import BrickletDMX # pylint: disable=import-error
from tf_device_ids import deviceIdentifiersList
from numpy import array, ones, zeros # pylint: disable=import-error
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
LIGHTING_MSGS = True

# dmx
MENU_DMX_VAL = os.environ.get("MENU_DMX_VAL", None)
NUM_DMX_CHANNELS = os.environ.get("NUM_DMX_CHANNELS", None)
HOST = os.environ.get("BRICKD_HOST", "127.0.0.1")
PORT = 4223

# lighting

MAX_BRIGHTNESS = 200
DMX_FRAME_DURATION=25
HUE_IP_ADDRESS = ""
TICK_TIME = 0.1 # seconds
# SLEEP_TIME = 0.1 # seconds
# TRANSITION_TIME = 10 # milliseconds

player = None
bridge = None
dmx = None
scheduler = None
last_played = 0

tfConnect = False

# utils

class LushRoomsLighting():

    def __init__(self):
        print('Lushroom Lighting init!')
        self.PLAY_HUE = True
        self.PLAY_DMX = True
        self.TRANSITION_TIME = 5 # milliseconds
        self.hue_list = [[]]
        self.player = None
        self.scheduler = None
        self.dmx_interpolator = DmxInterpolator()

        # 'last_played' seems to be the last numbered lighting event
        # in the SRT file
        self.last_played = 0
        self.subs = ""

        # Hue
        self.bridge = None

        # DMX
        self.dmx = None
        self.tfIDs = []
        self.ipcon = IPConnection()
        self.deviceIDs = [i[0] for i in deviceIdentifiersList]

        if self.PLAY_DMX: self.initDMX()
        if self.PLAY_HUE: self.initHUE()

    def emptyDMXFrame(self):
        return zeros((512,), dtype=int)

    # Tinkerforge sensors enumeration
    def cb_enumerate(self, uid, connected_uid, position, hardware_version, firmware_version,
                    device_identifier, enumeration_type):
        self.tfIDs.append([uid, device_identifier])

    ############################### LIGHTING FUNCTION METHODS

    def initDMX(self):
        # configure Tinkerforge DMX
        try:
            self.ipcon.connect(HOST, PORT)

            # Register Enumerate Callback
            self.ipcon.register_callback(IPConnection.CALLBACK_ENUMERATE, self.cb_enumerate)

            # Trigger Enumerate
            self.ipcon.enumerate()

            # Likely wait for the tinkerforge brickd to finish doing its thing
            sleep(0.7)

            if DEBUG:
                print("Tinkerforge enumerated IDs", self.tfIDs)

            dmxcount = 0
            for tf in self.tfIDs:
                if len(tf[0])<=3: # if the device UID is 3 characters it is a bricklet
                    if tf[1] in self.deviceIDs:
                        if VERBOSE:
                            print(tf[0],tf[1], self.getIdentifier(tf))
                    if tf[1] == 285: # DMX Bricklet
                        if dmxcount == 0:
                            print("Registering %s as slave DMX device for playing DMX frames" % tf[0])
                            self.dmx = BrickletDMX(tf[0], self.ipcon)
                            self.dmx.set_dmx_mode(self.dmx.DMX_MODE_MASTER)
                            self.dmx.set_frame_duration(DMX_FRAME_DURATION)
                        dmxcount += 1

            if dmxcount < 1:
                if LIGHTING_MSGS:
                    print("No DMX devices found.")
        except Exception as e:
            print("Could not create connection to Tinkerforge DMX. DMX lighting is now disabled")
            print("Why: ", e)
            self.PLAY_DMX = False

    def resetDMX(self):
        print("Directly resetting DMX...")
        if self.dmx:
            self.dmx.write_frame([ int(0.65*MAX_BRIGHTNESS),
                                        int(0.40*MAX_BRIGHTNESS),
                                        int(0.40*MAX_BRIGHTNESS),
                                        int(0.40*MAX_BRIGHTNESS),
                                        int(0.40*MAX_BRIGHTNESS),
                                        int(0.40*MAX_BRIGHTNESS),
                                        int(0.40*MAX_BRIGHTNESS),
                                        int(0.40*MAX_BRIGHTNESS),
                                        int(0.40*MAX_BRIGHTNESS),
                                        0,0,0,int(0.40*MAX_BRIGHTNESS) ])
        else:
            logging.error("Could not connect to DMX daemon to reset!")

    def initHUE(self):
        try:
            if self.PLAY_HUE:
                HUE_IP_ADDRESS = find_hue.hue_ip()

                if HUE_IP_ADDRESS == None:
                    print("HUE disabled in settings.json, HUE is now disabled")
                    self.PLAY_HUE = False
                    return
                self.bridge = Bridge(HUE_IP_ADDRESS, config_file_path="/media/usb/python_hue")
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

    def resetHUE(self):
        if self.PLAY_HUE:
            for l in self.bridge.lights:
                # print(dir(l))
                l.on = True
            # Print light names
            # Set brightness of each light to 100
            for l in self.bridge.lights:
                if LIGHTING_MSGS:
                    print(l.name)
                l.brightness = 50
                ##l.colormode = 'ct'
                #l.colortemp_k = 2700
                #l.saturation = 0
                bri = 50
                sat = 100
                hue = 0
                colortemp = 450
                cmd =  {'transitiontime' : int(self.TRANSITION_TIME), 'on' : True, 'bri' : int(bri), 'sat' : int(sat), 'hue' : int(hue), 'ct' : colortemp}
                self.bridge.set_light(l.light_id,cmd)

    ############################### LOW LEVEL LIGHT METHODS

    def getIdentifier(self, ID): 
        deviceType = ""
        for t in range(len(self.deviceIDs)):
            if ID[1]==deviceIdentifiersList[t][0]:
                deviceType = deviceIdentifiersList[t][1]
        return(deviceType)

    # tick()
    # callback that runs at every tick of the apscheduler

    def tick(self):
        # Leaving the comments below in for Francesco, they could be part of
        # a mysterious but useful debug strategy
        # try:

        if True:
            # print(subs[0])
            t = perf_counter()

            # ts = str(timedelta(seconds=t)).replace('.',',')
            # tsd = str(timedelta(seconds=t+10*TICK_TIME)).replace('.',',')

            ts = SubRipTime(seconds = t)
            tsd = SubRipTime(seconds = t + (1*TICK_TIME))
            # print(dir(player))

            try:
                pp = self.player.getPosition()
            except Exception as e:
                print("Could not get the current position of the player, shutting down lighting gracefully...")
                logging.error(e)
                self.__del__()


            #ptms = player.get_time()/1000.0
            #pt = SubRipTime(seconds=(player.get_time()/1000.0))
            #ptd = SubRipTime(seconds=(player.get_time()/1000.0+1*TICK_TIME))

            pt = SubRipTime(seconds=pp)
            ptd = SubRipTime(seconds=(pp+1*TICK_TIME))

            if DEBUG:
                #print('Time: %s | %s | %s - %s | %s - %s | %s | %s' % (datetime.now(),t,ts,tsd,pt,ptd,pp,ptms))
                # print('Time: %s | %s | %s | %s | %s | %s | %s ' % (datetime.now(),t,ts,tsd,pp,pt,ptd))
                pass
            ## sub, i = self.find_subtitle(subs, ts, tsd)
            # sub, i = self.find_subtitle(self.subs, pt, ptd)
            sub, i = self.find_subtitle(self.subs, pt, ptd, lo=self.last_played)

            if DEBUG:
                print(i, "Found Subtitle for light event:", sub, i)

            ## hours, minutes, seconds, milliseconds = time_convert(sub.start)
            ## t = seconds + minutes*60 + hours*60*60 + milliseconds/1000.0

            if sub!="": #and i > self.last_played:
                if LIGHTING_MSGS and DEBUG:
                    print(i, "Light event:", sub)
                # print("Trigger light event %s" % i)
                self.trigger_light(sub)
                self.last_played = i
                if DEBUG:
                    print('last_played: ', i)

            pod_mode = MENU_DMX_VAL != None

            if self.dmx_interpolator.isRunning() and pod_mode is False:
                if self.PLAY_DMX:
                        if self.dmx != None:
                            iFrame = self.dmx_interpolator.getInterpolatedFrame(pt)
                            self.dmx.write_frame(iFrame)

            # except Exception as e:
            #     print('ERROR: It is likely the connection to the audio player has been severed...')
            #     print('Why? --> ', e)
            #     print('Scheduler is about to end gracefully...')
            #     self.__del__()

        # except:
        #    pass

    def find_subtitle(self, subtitle, from_t, to_t, lo=0, backwards=False):
        i = lo

        if backwards and SEEK_EVENT_LOG:
            print("searching backwards!")

        if DEBUG and VERBOSE:
            pass
            # print("Starting from subtitle", lo, from_t, to_t, len(subtitle))

        # Find where we are
        subLen = len(subtitle)

        while (i < subLen):
            if (subtitle[i].start >= to_t and not backwards):
                break

            if backwards and (subtitle[i].start >= from_t):
                previous_i = max(0, i-1)
                if SEEK_EVENT_LOG:
                    print("In subs, at:", previous_i, " found: ", subtitle[previous_i].text)
                return subtitle[previous_i].text, previous_i

            # if (from_t >= subtitle[i].start) & (fro   m_t  <= subtitle[i].end):
            if (subtitle[i].start >= from_t) & (to_t  >= subtitle[i].start):
                # print(subtitle[i].start, from_t, to_t)
                if not self.dmx_interpolator.isRunning():
                    self.dmx_interpolator.findNextEvent(i, subtitle)
                return subtitle[i].text, i
            i += 1

        return "", i

    def end_callback(self, event):
        if LIGHTING_MSGS:
            print('End of media stream (event %s)' % event.type)
        exit(0)

    def hue_build_lookup_table(self, lights):
        if DEBUG:
            print("hue lookup lights: ", lights)
    
        hue_l = [[]]
        i = 0
        for j in range(1+len(lights)+1):
            for l in lights:
                #print(dir(l))
                #lname = "lamp   "+l.name+"   "
                lname = str(l.name)
                #print(lname)
                #print("testing", str(j), lname.find(str(i)), len(hue), l.name.find(str(i)), l.light_id, l.name, l.bridge.ip, l.bridge.name, str(i+1))
                if lname.find(str(j))>=0:
                    #if str(i) in lname:
                    if LIGHTING_MSGS:
                        print(j, lname.find(str(j)), l.light_id, l.name, l.bridge.ip, l.bridge.name)
                    if len(hue_l)<=j:
                        hue_l.append([l.light_id])
                    else:
                        hue_l[j].append(l.light_id)
            i += 1
        if DEBUG:
            print("hue_l: ", hue_l)
        return(hue_l)

    def trigger_light(self, subs):
        global MAX_BRIGHTNESS, DEBUG
        if DEBUG:
            print("perf_count: ", perf_counter(), subs)
        commands = str(subs).split(";")

        if DEBUG:
            print("Trigger light", self.hue_list)
        for command in commands:
            try:
                # if True:
                # print(command)
                if DEBUG:
                    print(command[0:len(command)-1].split("("))
                scope,items = command[0:len(command)-1].split("(")

                if DEBUG:
                    print("sc: ", scope, "it: ", items)

                if scope[0:3] == "HUE" and self.PLAY_HUE:
                    l = int(scope[3:])
                    #print(l)
                    if VERBOSE:
                        print(self.hue_list[l])
                    hue, sat, bri, TRANSITION_TIME = items.split(',')
                    # print(perf_counter(), l, items, hue, sat, bri, TRANSITION_TIME)
                    bri = int((float(bri)/255.0)*int(MAX_BRIGHTNESS))
                    # print(bri)
                    cmd =  {'transitiontime' : int(self.TRANSITION_TIME), 'on' : True, 'bri' : int(bri), 'sat' : int(sat), 'hue' : int(hue)}
                    if LIGHTING_MSGS:
                        print("Trigger HUE",l,cmd)
                    if self.PLAY_HUE:
                        #lights = bridge.lights
                        #for light in lights:
                        #   print(light.name)
                        #   if light.name.find(str(l)):
                        #       light.brightness = bri
                        #       light.hue = hue
                        #lights[l].brightness = bri
                        #lights[l].saturation = sat
                        #lights[l].hue = hue

                        for hl in self.hue_list[l]:
                            self.bridge.set_light(hl, cmd)

                if scope[0:3] == "DMX":
                    l = int(scope[3:])
                
                    if items == "":
                        print("Empty DMX event found! Turning all DMX channels off...")
                        channels = self.emptyDMXFrame()
                    else:
                        # channels = int(int(MAX_BRIGHTNESS)/255.0*(array(items.split(",")).astype(int)))
                        channels = array(items.split(",")).astype(int)
                        # channels = array(map(lambda i: int(MAX_BRIGHTNESS)*i, channels))

                    if LIGHTING_MSGS:
                        print("Trigger DMX:", l, channels)

                    if self.PLAY_DMX:
                        if self.dmx != None:
                            self.dmx.write_frame(channels)
            except:
               pass
        if LIGHTING_MSGS and DEBUG:
            print(30*'-')

    ############################### PLAYER FUNCTION METHODS

    def time_convert(self, t):
        block, milliseconds = str(t).split(",")
        hours, minutes, seconds = block.split(":")
        return(int(hours),int(minutes),int(seconds), int(milliseconds))

    def start(self, audioPlayer, subs):
        self.player = audioPlayer
        self.subs = subs
        self.dmx_interpolator.__init__()
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
                    print("There's only 1 lighting event, so no need to start the scheduler and unleash hell...")
            elif subs_length > 1:
                # start lighting scheduler
                self.scheduler = BackgroundScheduler({
                'apscheduler.executors.processpool': {
                    'type': 'processpool',
                    'max_workers': '10'
                }})
                self.scheduler.add_job(self.tick, 'interval', seconds=TICK_TIME, misfire_grace_time=None, max_instances=16, coalesce=True)
                # This could be the cause of the _very_ first event, after a cold boot, not triggering correctly:
                self.scheduler.start(paused=False)

            if LIGHTING_MSGS:
                print("-------------")
        else:
            print('Subtitle track not found/empty subtitle track. Lighting is now disabled')

    def playPause(self, status):

        print('Lighting PlayPause: ', status)
        if status=="Paused":
            self.scheduler.pause()
        elif status=="Playing":
            self.scheduler.resume()
        if LIGHTING_MSGS:
            print("-------------")

    def fadeDown(self, status):

        print("Lighting: fadeDown")
        # self.scheduler.shutdown()
        self.last_played = 0

        if status=="Paused":
            self.scheduler.pause()
        elif status=="Playing":
            self.scheduler.resume()
        if LIGHTING_MSGS:
            print("-------------")

    def exit(self):
        self.resetDMX()
        self.resetHUE()
        self.__del__()

    def triggerPreviousEvent(self, pos):
        if LIGHTING_MSGS:
            print("Finding last lighting command from pos: ", pos)

        pp = pos
        pt = SubRipTime(seconds=pp)
        ptd = SubRipTime(seconds=(pp+1*TICK_TIME))

        if VERBOSE and DEBUG:
            print("Finding last light event, starting from: ")
            print("pt: ", ptd)
            print("ptd: ", ptd)

        sub, i = self.find_subtitle(self.subs, pt, ptd, backwards=True)

        if LIGHTING_MSGS:
            print("Seeking, found sub:", sub, " at pos: ", i)

        if sub!="": #and i > self.last_played:
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
            print("ipcon: ", self.ipcon)
            if self.scheduler:
                logging.info("Shutting down scheduler...")
                self.scheduler.shutdown()
           
            logging.info("Disconnecting from tinkerforge...")
            self.ipcon.disconnect()
            self.dmx = None
            self.ipcon = None
        except Exception as e:
            print('Lighting destructor failed: ', e)
        if LIGHTING_MSGS:
            print("Lighting died!")


class ExitException(Exception):
    def __init__(self, key, scheduler, ipcon):
        scheduler.shutdown()
        if tfConnect:
            ipcon.disconnect()
        exit(0)
