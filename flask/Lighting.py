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
from numpy import array, ones # pylint: disable=import-error
import os
import json

# dev

DEBUG = True
VERBOSE = True

# dmx

HOST = "127.0.0.1"
PORT = 4223

MAX_BRIGHTNESS = 200
SRT_FILENAME = "Surround_Test_Audio.srt"
HUE1_IP_ADDRESS = ""
HUE2_IP_ADDRESS = ""
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

tfConnect = True

# utils

class LushRoomsLighting(): 

    def __init__(self):
        print('LRLighting init!')
        self.SETTINGS_BASE_PATH = "/media/usb/"
        self.JSON_SETTINGS_FILE = "settings.json"
        self.hue_list = [[]]
        self.player = None
        self.scheduler = None


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

        self.initDMX()
        self.initHUE()

         # Tinkerforge sensors enumeration
    def cb_enumerate(self, uid, connected_uid, position, hardware_version, firmware_version,
                    device_identifier, enumeration_type):
        self.tfIDs.append([uid, device_identifier])

    def initDMX(self):
        # configure Tinkerforge DMX
        self.ipcon.connect(HOST, PORT)

        # Register Enumerate Callback
        self.ipcon.register_callback(IPConnection.CALLBACK_ENUMERATE, self.cb_enumerate)

        # Trigger Enumerate
        self.ipcon.enumerate()

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
            print("No DMX devices found.")

    def initHUE(self):
        settings_path = os.path.join(self.SETTINGS_BASE_PATH, self.JSON_SETTINGS_FILE)
        if os.path.exists(settings_path):
            with open(settings_path) as f:
                settings_json = json.loads(f.read())
                print(json.dumps(settings_json))
                HUE1_IP_ADDRESS = settings_json["hue1_ip"]

        if PLAY_HUE:
            #global hue_list
            #try:
            if True:
                # b = Bridge('lushroom-hue.local')
                self.bridge = Bridge(HUE1_IP_ADDRESS)
                # If the app is not registered and the button is not pressed, press the button and call connect() (this only needs to be run a single time)
                self.bridge.connect()
                # Get the bridge state (This returns the full dictionary that you can explore)
                self.bridge.get_api()
                lights = self.bridge.lights
                for l in lights:
                    # print(dir(l))
                    l.on = False
                sleep(1)
                for l in lights:
                    # print(dir(l))
                    l.on = True
                # Print light names
                # Set brightness of each light to 10
                for l in lights:
                    print(l.name)
                    l.brightness = 255
                for l in lights:
                    # print(l.name)
                    l.brightness = 100
                    l.saturation = 0


                # Get a dictionary with the light name as the key
                light_names = self.bridge.get_light_objects('name')
                print("Light names:", light_names)
                self.hue_list = self.hue_build_lookup_table(lights)
                print(self.hue_list)
            #except PhueRegistrationException:
            #    print("Press the Philips Hue button to link the Hue Bridge to the LushRoom Pi.")

    def getIdentifier(self, ID):
        deviceType = ""
        for t in range(len(self.deviceIDs)):
            if ID[1]==deviceIdentifiersList[t][0]:
                deviceType = deviceIdentifiersList[t][1]
        return(deviceType)

    def find_subtitle(self, subtitle, from_t, to_t, lo=0):
        i = lo
        while (i < len(subtitle)):
            # print(subtitle[i])
            if (subtitle[i].start >= to_t):
                break
            if (subtitle[i].start <= from_t) & (to_t  <= subtitle[i].end):
                # print(subtitle[i].start, from_t, to_t)
                return subtitle[i].text, i
            i += 1
        return "", i

    def end_callback(self, event):
        print('End of media stream (event %s)' % event.type)
        exit(0)

    def hue_build_lookup_table(self, lights):
        #print(lights)
        hue_l = [[]]
        i = 1
        for j in range(len(lights)):
            for l in lights:
                #print(dir(l))
                #lname = "lamp   "+l.name+"   "
                lname = str(l.name)
                #print(lname)
                #print("testing", str(j), lname.find(str(i)), len(hue), l.name.find(str(i)), l.light_id, l.name, l.bridge.ip, l.bridge.name, str(i+1))
                if lname.find(str(j))>=0:
                    #if str(i) in lname:
                    print(j, lname.find(str(j)), l.light_id, l.name, l.bridge.ip, l.bridge.name)
                    if len(hue_l)<=j:
                        hue_l.append([l.light_id])
                    else:
                        hue_l[j].append(l.light_id)
            i += 1
        return(hue_l)


    def trigger_light(self, subs):
        # print(perf_counter(), subs)
        commands = str(subs).split(";")
        global MAX_BRIGHTNESS, DEBUG
        print("Trigger light", self.hue_list)
        for command in commands:
            #try:
            if True:
                # print(command)
                scope,items = command[0:len(command)-1].split("(")
                # print(scope,items)
                if scope[0:3] == "HUE":
                    l = int(scope[3:])
                    print(l)
                    # There seems to be something wrong with the lookup table
                    # so if we can't find the current light in the table (or it doesn't exist)
                    # skip to the next light
                    try:
                        print(self.hue_list[l])
                    except:
                        continue
                    hue, sat, bri, TRANSITION_TIME = items.split(',')
                    # print(perf_counter(), l, items, hue, sat, bri, TRANSITION_TIME)
                    bri = int((float(bri)/255.0)*int(MAX_BRIGHTNESS))
                    # print(bri)
                    cmd =  {'transitiontime' : int(TRANSITION_TIME), 'on' : True, 'bri' : int(bri), 'sat' : int(sat), 'hue' : int(hue)}
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
                            print(hl)
                            self.bridge.set_light(hl, cmd)
                if scope[0:3] == "DMX":
                    l = int(scope[3:])
                    # channels = int(int(MAX_BRIGHTNESS)/255.0*(array(items.split(",")).astype(int)))
                    channels = array(items.split(",")).astype(int)
                    # channels = array(map(lambda i: int(MAX_BRIGHTNESS)*i, channels))
                    if DEBUG:
                        print("Trigger DMX:", l, channels)
                    if PLAY_DMX:
                        self.dmx.write_frame(channels)
            #except:
            #    pass
        print(30*'-')

    def tick(self):
        #try:
        if True:
            # print(subs[0])
            t = perf_counter()
            # ts = str(timedelta(seconds=t)).replace('.',',')
            # tsd = str(timedelta(seconds=t+10*TICK_TIME)).replace('.',',')
            ts = SubRipTime(seconds = t)
            tsd = SubRipTime(seconds = t+1*TICK_TIME)
            # print(dir(player))
            print('in tick, player: ', id(self.player))
            print('in tick, playerDur: ', self.player.getPosition())
            pp = self.player.getPosition()
            #ptms = player.get_time()/1000.0
            #pt = SubRipTime(seconds=(player.get_time()/1000.0))
            #ptd = SubRipTime(seconds=(player.get_time()/1000.0+1*TICK_TIME))
            pt = SubRipTime(seconds=pp)
            ptd = SubRipTime(seconds=(pp+1*TICK_TIME))
            if DEBUG:
                #print('Time: %s | %s | %s - %s | %s - %s | %s | %s' % (datetime.now(),t,ts,tsd,pt,ptd,pp,ptms))
                print('Time: %s | %s | %s | %s | %s ' % (datetime.now(),t,ts,tsd,pp))
                pass
            ## sub, i = find_subtitle(subs, ts, tsd)
            sub, i = self.find_subtitle(self.subs, pt, ptd)
            ## hours, minutes, seconds, milliseconds = time_convert(sub.start)
            ## t = seconds + minutes*60 + hours*60*60 + milliseconds/1000.0
            if sub!="" and i > self.last_played:
                print(i, "Light event:", sub)
                # print("Trigger light event %s" % i)
                self.trigger_light(sub)
                self.last_played = i
        #except:
        #    pass


    def time_convert(self, t):
        block, milliseconds = str(t).split(",")
        hours, minutes, seconds = block.split(":")
        return(int(hours),int(minutes),int(seconds), int(milliseconds))

    def start(self, audioPlayer, subs):
        self.player = audioPlayer
        self.subs = subs

        print("Lighting: Start!")
        print('AudioPlayer: ', self.player)
        print("Number of lighting events",len(self.subs))

        # start lighting player/self.scheduler
        self.last_played = 0
        #if self.scheduler !
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self.tick, 'interval', seconds=TICK_TIME)
        self.scheduler.start(paused=False)
        print("-------------")

    def playPause(self, status):

        print('Lighting pp: ', status)
        if status=="Paused":
            self.scheduler.pause()
        elif status=="Playing":
            self.scheduler.resume()
        print("-------------")

    def fadeDown(self, status):

        print("Lighting: fadeDown")
        # self.scheduler.shutdown()
        self.last_played = 0
        
        if status=="Paused":
            self.scheduler.pause()
        elif status=="Playing":
            self.scheduler.resume()
        print("-------------")

    def exit(self):
        self.__del__()

    def __del__(self):
        self.scheduler.shutdown()
        print("Lighting died!")


class ExitException(Exception):
    def __init__(self, key, scheduler, ipcon):
        scheduler.shutdown()
        #player.stop()
        if tfConnect:
            ipcon.disconnect()
        exit(0)


