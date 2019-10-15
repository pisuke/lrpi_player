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

# dev

DEBUG = True
VERBOSE = False
LIGHTING_MSGS = True


# dmx
MENU_DMX_VAL = os.environ.get("MENU_DMX_VAL", None)
NUM_DMX_CHANNELS = os.environ.get("NUM_DMX_CHANNELS", None)
HOST = os.environ.get("BRICKD_HOST", "127.0.0.1")
PORT = 4223

# lighting

MAX_BRIGHTNESS = 200
SRT_FILENAME = "Surround_Test_Audio.srt"
HUE_IP_ADDRESS = ""
# HUE2_IP_ADDRESS = ""
TICK_TIME = 0.1 # seconds
PLAY_HUE = True
PLAY_DMX = True
# SLEEP_TIME = 0.1 # seconds
# TRANSITION_TIME = 10 # milliseconds

subs = []
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
        self.TRANSITION_TIME = 5 # milliseconds
        self.hue_list = [[]]
        self.player = None
        self.scheduler = None
        self.no_more_dmx_events = False

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

        # init methods

        if PLAY_DMX:
            self.initDMX()
        self.initHUE()

    def emptyDMXFrame(self):
        return zeros((512,), dtype=int)

    def cleaningScene(self):
        pass
        # self.resetHUE()
        # self.resetDMX()

         # Tinkerforge sensors enumeration
    def cb_enumerate(self, uid, connected_uid, position, hardware_version, firmware_version,
                    device_identifier, enumeration_type):
        self.tfIDs.append([uid, device_identifier])

    def initDMX(self):
        # configure Tinkerforge DMX
        try:
            self.ipcon.connect(HOST, PORT)

            # Register Enumerate Callback
            self.ipcon.register_callback(IPConnection.CALLBACK_ENUMERATE, self.cb_enumerate)

            # Trigger Enumerate
            self.ipcon.enumerate()

            # Likely wait for the tinkerforge brickd to finish doing its thing
            sleep(2)

            if DEBUG:
                print("Tinkerforge enumerated IDs", self.tfIDs)

            dmxcount = 0
            for tf in self.tfIDs:
                # try:
                if True:
                    # print(len(tf[0]))

                    if len(tf[0])<=3: # if the device UID is 3 characters it is a bricklet
                        if tf[1] in self.deviceIDs:
                            if VERBOSE:
                                print(tf[0],tf[1], self.getIdentifier(tf))
                        if tf[1] == 285: # DMX Bricklet
                            if dmxcount == 0:
                                print("Registering %s as slave DMX device for playing DMX frames" % tf[0])
                                self.dmx = BrickletDMX(tf[0], self.ipcon)
                                self.dmx.set_dmx_mode(self.dmx.DMX_MODE_MASTER)
                                # channels = int((int(MAX_BRIGHTNESS)/255.0)*ones(512,)*255)
                                # dmx.write_frame([255,255])
                                sleep(1)
                                # channels = int((int(MAX_BRIGHTNESS)/255.0)*zeros(512,)*255)
                                # dmx.write_frame(channels)
                            dmxcount += 1

            if dmxcount < 1:
                if LIGHTING_MSGS:
                    print("No DMX devices found.")
        except Exception as e:
            print("Could not create connection to Tinkerforge DMX. DMX lighting is now disabled")
            print("Error: ", e)
            PLAY_DMX = False

    def resetDMX(self):
        dmxcount = 0
        for tf in self.tfIDs:
            # try:
            if True:
                # print(len(tf[0]))

                if len(tf[0])<=3: # if the device UID is 3 characters it is a bricklet
                    if tf[1] in self.deviceIDs:
                        if VERBOSE:
                            print(tf[0],tf[1], self.getIdentifier(tf))
                    if tf[1] == 285: # DMX Bricklet
                        if dmxcount == 0:
                            # channels = int((int(MAX_BRIGHTNESS)/255.0)*ones(512)*255)
                            if (MENU_DMX_VAL is not None and NUM_DMX_CHANNELS is not None):
                                print('menu values: ', MENU_DMX_VAL)
                                print('number of DMX channels: ', NUM_DMX_CHANNELS)
                                frame_arr = []
                                menu_val_arr = MENU_DMX_VAL.split(",")
                                menu_val_arr = [int(i) for i in menu_val_arr]
                                for i in range(int(int(NUM_DMX_CHANNELS)/3)):
                                    frame_arr += menu_val_arr
                                self.dmx.write_frame(frame_arr)
                            else:
                                print('Resetting DMX...')
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
                        dmxcount += 1
                    if LIGHTING_MSGS:
                        print('dmxcount: ', dmxcount)

    def pauseDMX(self):
        dmxcount = 0
        for tf in self.tfIDs:
            # try:
            if True:
                # print(len(tf[0]))

                if len(tf[0])<=3: # if the device UID is 3 characters it is a bricklet
                    if tf[1] in self.deviceIDs:
                        if VERBOSE:
                            print(tf[0],tf[1], self.getIdentifier(tf))
                    if tf[1] == 285: # DMX Bricklet
                        if dmxcount == 0:
                            # channels = int((int(MAX_BRIGHTNESS)/255.0)*ones(512)*255)
                            # hardcoded values for lighting in LushSpa
                            self.dmx.write_frame([int(0.65*MAX_BRIGHTNESS),
                                                  int(0.40*MAX_BRIGHTNESS),
                                                  int(0.40*MAX_BRIGHTNESS),
                                                  int(0.40*MAX_BRIGHTNESS),
                                                  int(0.40*MAX_BRIGHTNESS),
                                                  int(0.40*MAX_BRIGHTNESS),
                                                  int(0.40*MAX_BRIGHTNESS),
                                                  int(0.40*MAX_BRIGHTNESS),
                                                  int(0.40*MAX_BRIGHTNESS),
                                                  0,0,0,int(0.40*MAX_BRIGHTNESS)])
                        dmxcount += 1
                    if LIGHTING_MSGS:
                        print('dmxcount: ', dmxcount)


    def initHUE(self):
        global PLAY_HUE

        HUE_IP_ADDRESS = find_hue.hue_ip()

        try:
            if PLAY_HUE:
                #global hue_list
                #try:
                if True:
                    # b = Bridge('lushroom-hue.local')
                    self.bridge = Bridge(HUE_IP_ADDRESS, config_file_path="/media/usb/python_hue")
                    # If the app is not registered and the button is not pressed, press the button and call connect() (this only needs to be run a single time)
                    self.bridge.connect()
                    # Get the bridge state (This returns the full dictionary that you can explore)
                    self.bridge.get_api()
                    lights = self.bridge.lights
                    # lplay-85
                    # for l in lights:
                    #     # print(dir(l))
                    #     l.on = False
                    # sleep(1)
                    for l in lights:
                        # print(dir(l))
                        l.on = True
                    # Print light names
                    # Set brightness of each light to 100
                    for l in lights:
                        if LIGHTING_MSGS:
                            print(l.name)
                        l.brightness = 255
                    for l in lights:
                        ## print(l.name)
                        l.brightness = 50
                        ##l.colormode = 'ct'
                        #l.colortemp_k = 2700
                        #l.saturation = 0
                        bri = 50
                        sat = 100
                        hue = 0
                        colormode = 'ct'
                        colortemp = 450
                        cmd =  {'transitiontime' : int(self.TRANSITION_TIME), 'on' : True, 'bri' : int(bri), 'sat' : int(sat), 'hue' : int(hue), 'ct' : colortemp}
                        self.bridge.set_light(l.light_id,cmd)


                    # Get a dictionary with the light name as the key
                    light_names = self.bridge.get_light_objects('name')
                    if LIGHTING_MSGS:
                        print("Light names:", light_names)
                    self.hue_list = self.hue_build_lookup_table(lights)
                    if LIGHTING_MSGS:
                        print(self.hue_list)
                #except PhueRegistrationException:
                #    print("Press the Philips Hue button to link the Hue Bridge to the LushRoom Pi.")
        except Exception as e:
            print("Could not create connection to Hue. Hue lighting is now disabled")
            print("Error: ", e)
            PLAY_HUE = False

    def resetHUE(self):
        global PLAY_HUE
        if PLAY_HUE:
            lights = self.bridge.lights
            # for l in lights:
            #     # print(dir(l))
            #     l.on = False
            # sleep(1)
            for l in lights:
                # print(dir(l))
                l.on = True
            # Print light names
            # Set brightness of each light to 100
            for l in lights:
                if LIGHTING_MSGS:
                    print(l.name)
                l.brightness = 50
                ##l.colormode = 'ct'
                #l.colortemp_k = 2700
                #l.saturation = 0
                bri = 50
                sat = 100
                hue = 0
                colormode = 'ct'
                colortemp = 450
                cmd =  {'transitiontime' : int(self.TRANSITION_TIME), 'on' : True, 'bri' : int(bri), 'sat' : int(sat), 'hue' : int(hue), 'ct' : colortemp}
                self.bridge.set_light(l.light_id,cmd)

    def pauseHUE(self):
        global PLAY_HUE
        if PLAY_HUE:
            print("Pause mode: Hue")
            lights = self.bridge.lights
            # print(lights)
            sleep(0.5)
            for l in lights:
                # print(dir(l))
                l.on = True
            # Print light names
            # Set brightness of each light to 100
            for l in lights:
                l.brightness = 100
                ##l.colormode = 'ct'
                #l.colortemp_k = 2700
                #l.saturation = 0
                bri = 100
                sat = 100
                hue = 0
                colormode = 'ct'
                colortemp = 450
                cmd =  {'transitiontime' : int(self.TRANSITION_TIME), 'on' : True, 'bri' : int(bri), 'sat' : int(sat), 'hue' : int(hue), 'ct' : colortemp}
                self.bridge.set_light(l.light_id,cmd)
                if LIGHTING_MSGS:
                    print(l.name,l.light_id,cmd)

    def getIdentifier(self, ID):
        deviceType = ""
        for t in range(len(self.deviceIDs)):
            if ID[1]==deviceIdentifiersList[t][0]:
                deviceType = deviceIdentifiersList[t][1]
        return(deviceType)

    # Find the next DMX event for interpolation

    def find_next_dmx_event(self, subtitle, from_t, to_t, currentI, currentSubText):
        nextI = currentI + 1
        lenSubs = len(subtitle)

        # TODO: Once we find there are no DMX results left in the file once,
        # memoise the result!
        # Perhaps see: https://dbader.org/blog/python-memoization

        # Idea - use this as a first attempt
        # Meanwhile - fire off a thread that creates a hash table of
        # current dmx event index and next DMX event. If that finishes in time,
        # use the hash table and make this method redundant

        while nextI < lenSubs:
            if subtitle[nextI].text.find("DMX", 0, 5) > -1:
                print('next dmx: ', subtitle[nextI].text)
                return currentSubText, currentI, nextI
            nextI += 1

        self.no_more_dmx_events = True

        return currentSubText, currentI, currentI 

    def find_subtitle(self, subtitle, from_t, to_t, lo=0):
        i = lo

        if DEBUG:
            print("Starting from subtitle", lo, from_t, to_t, len(subtitle))

        # Find where we are

        while (i < len(subtitle)):
            # print(subtitle[i])
            if (subtitle[i].start >= to_t):
                break

            # if (from_t >= subtitle[i].start) & (fro   m_t  <= subtitle[i].end):
            if (subtitle[i].start >= from_t) & (to_t  >= subtitle[i].start):
                # print(subtitle[i].start, from_t, to_t)
                return self.find_next_dmx_event(subtitle, from_t, to_t, i, subtitle[i].text)
            i += 1
        return "", i, i+1

    def end_callback(self, event):
        if LIGHTING_MSGS:
            print('End of media stream (event %s)' % event.type)
        exit(0)

    def hue_build_lookup_table(self, lights):
        if DEBUG:
            print("hue lookup lights: ", lights)
    
        hue_l = [[]]
        i = 1
        for j in range(len(lights)+1):
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
        return(hue_l)

    def trigger_light(self, subs):
        global MAX_BRIGHTNESS, DEBUG, PLAY_HUE
        if DEBUG:
            print(perf_counter(), subs)
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

                if scope[0:3] == "HUE" and PLAY_HUE:
                    l = int(scope[3:])
                    #print(l)
                    try:
                        if VERBOSE:
                            print(self.hue_list[l])
                    except:
                        continue
                    hue, sat, bri, TRANSITION_TIME = items.split(',')
                    # print(perf_counter(), l, items, hue, sat, bri, TRANSITION_TIME)
                    bri = int((float(bri)/255.0)*int(MAX_BRIGHTNESS))
                    # print(bri)
                    cmd =  {'transitiontime' : int(self.TRANSITION_TIME), 'on' : True, 'bri' : int(bri), 'sat' : int(sat), 'hue' : int(hue)}
                    if DEBUG:
                        print("Trigger HUE",l,cmd)
                    if PLAY_HUE:
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
                            if DEBUG:
                                print(hl)
                            self.bridge.set_light(hl, cmd)
                if scope[0:3] == "DMX":
                    l = int(scope[3:])
                    print("l: ", l)

                    if items == "":
                        print("Empty DMX event found! Turning all DMX channels off...")
                        channels = self.emptyDMXFrame()
                    else:
                        # channels = int(int(MAX_BRIGHTNESS)/255.0*(array(items.split(",")).astype(int)))
                        channels = array(items.split(",")).astype(int)
                        # channels = array(map(lambda i: int(MAX_BRIGHTNESS)*i, channels))

                    if DEBUG:
                        print("Trigger DMX:", l, channels)

                    if PLAY_DMX:
                        if self.dmx != None:
                            self.dmx.write_frame(channels)
            except:
               pass
        if LIGHTING_MSGS and DEBUG:
            print(30*'-')

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
            tsd = SubRipTime(seconds = t+1*TICK_TIME)
            # print(dir(player))

            try:
                pp = self.player.getPosition()

                #ptms = player.get_time()/1000.0
                #pt = SubRipTime(seconds=(player.get_time()/1000.0))
                #ptd = SubRipTime(seconds=(player.get_time()/1000.0+1*TICK_TIME))

                pt = SubRipTime(seconds=pp)
                ptd = SubRipTime(seconds=(pp+1*TICK_TIME))

                if DEBUG:
                    #print('Time: %s | %s | %s - %s | %s - %s | %s | %s' % (datetime.now(),t,ts,tsd,pt,ptd,pp,ptms))
                    print('Time: %s | %s | %s | %s | %s | %s | %s ' % (datetime.now(),t,ts,tsd,pp,pt,ptd))
                    pass
                ## sub, i = self.find_subtitle(subs, ts, tsd)
                # sub, i = self.find_subtitle(self.subs, pt, ptd)
                sub, i, i_dmx_next = self.find_subtitle(self.subs, pt, ptd, lo=self.last_played)

                if DEBUG:
                    print(i, "Found Subtitle for light event:", sub)

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

            except Exception as e:
                print('ERROR: It is likely the connection to the audio player has been severed...')
                print('Why? --> ', e)
                print('Scheduler is about to end gracefully...')
                self.__del__()

        # except:
        #    pass


    def time_convert(self, t):
        block, milliseconds = str(t).split(",")
        hours, minutes, seconds = block.split(":")
        return(int(hours),int(minutes),int(seconds), int(milliseconds))

    def start(self, audioPlayer, subs):
        self.player = audioPlayer
        self.subs = subs
        if subs is not None: 
            if LIGHTING_MSGS:
                print("Lighting: Start!")
                print('AudioPlayer: ', self.player)
                print("Number of lighting events",len(self.subs))
            # start lighting scheduler
            self.last_played = 0
            #if self.scheduler !
            self.scheduler = BackgroundScheduler({
            'apscheduler.executors.processpool': {
                'type': 'processpool',
                'max_workers': '10'
            }})
            self.scheduler.add_job(self.tick, 'interval', seconds=TICK_TIME, misfire_grace_time=None, max_instances=16, coalesce=True)
            self.scheduler.start(paused=False)

            if LIGHTING_MSGS:
                print("-------------")
        else:
            print('Subtitle track not found/empty subtitle track. Lighting is now disabled')

    def playPause(self, status):

        print('Lighting PlayPause: ', status)
        if status=="Paused":
            self.scheduler.pause()
            # lplay-86
            # self.pauseHUE()
            # self.pauseDMX()
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
            # self.pauseHUE()
            # self.pauseDMX()
        elif status=="Playing":
            self.scheduler.resume()
        if LIGHTING_MSGS:
            print("-------------")

    def exit(self):
        self.cleaningScene()
        self.__del__()

    def seek(self):
        # This doesn't seem to work fully...
        # But may be solved by LUSHDigital/lrpi_player#114
        self.last_played = 0
        # pass

    def __del__(self):
        try:
            if self.scheduler:
                self.scheduler.shutdown()
        except Exception as e:
            print('Lighting destructor failed: ', e)
        if LIGHTING_MSGS:
            print("Lighting died!")


class ExitException(Exception):
    def __init__(self, key, scheduler, ipcon):
        scheduler.shutdown()
        #player.stop()
        if tfConnect:
            ipcon.disconnect()
        exit(0)
