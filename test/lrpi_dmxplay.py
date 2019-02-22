#!/usr/bin/env python3
import os

HOST = os.environ.get("BRICKD_HOST", "127.0.0.1")
PORT = 4223

debug = False
verbose = False
srtFilename = "output_dmx.srt"
# reading_interval = 1.0

from tinkerforge.ip_connection import IPConnection
from tinkerforge.bricklet_dmx import BrickletDMX

from os.path import join, splitext
from os import listdir
import math, time, datetime
from numpy import array, zeros, array_equal
# import pysrt
import signal
import sys

from random import random
from time import sleep, time, perf_counter
# from sched import scheduler
from pysrt import SubRipFile, SubRipItem, SubRipTime
from pysrt import open as srtopen
from threading import Timer

from tf_device_ids import deviceIdentifiersList


srtFile = SubRipFile()

tfIDs = []

tfConnect = True

prevFrame = zeros(512)
prevTime = 0
subs = []

ipcon = IPConnection()

# if tfConnect:
#     tfIDs = []

deviceIDs = [i[0] for i in deviceIdentifiersList]

if debug:
    print(deviceIDs)
    for i in range(len(deviceIDs)):
        print(deviceIdentifiersList[i])

def getIdentifier(ID):
    deviceType = ""

    for t in range(len(deviceIDs)):
        if ID[1]==deviceIdentifiersList[t][0]:
            deviceType = deviceIdentifiersList[t][1]
    return(deviceType)

# Tinkerforge sensors enumeration
def cb_enumerate(uid, connected_uid, position, hardware_version, firmware_version,
                 device_identifier, enumeration_type):
    tfIDs.append([uid, device_identifier])

def signal_handler(sig, frame):
    # clean up
    global subs, tfConnect, ipcon, srtFile
    if verbose:
        print(subs, len(subs))
    encoding="utf_8"
    srtFile.close()
    if tfConnect:
        ipcon.disconnect()
    sys.exit(0)

def trigger_light_dmx(subs, dmx):
    # print(perf_counter(), subs)
    commands = str(subs).split(";")
    for command in commands:
        # print(command)
        scope,items = command[0:len(command)-1].split("(")
        # print(scope,items)
        if scope[0:3] == "DMX":
            l = int(scope[3:])
            channels = items.split(",")
            if debug:
                print(perf_counter(), l, channels, len(channels))
            dmx.write_frame(channels)
        if debug:
            print(30*'-')


# >>> def print_some_times():
# ...     print time.time()
# ...     Timer(5, print_time, ()).start()
# ...     Timer(10, print_time, ()).start()
# ...     time.sleep(11)  # sleep while time-delay events execute
# ...     print time.time()
# ...
# >>> print_some_times()
# 930343690.257
# From print_time 930343695.274
# From print_time 930343700.273
# 930343701.301

def time_convert(t):
    block, milliseconds = str(t).split(",")
    hours, minutes, seconds = block.split(":")
    return(int(hours),int(minutes),int(seconds), int(milliseconds))


if __name__ == "__main__":

    subs = srtopen(srtFilename)

    print("Number of events",len(subs))

    # s = scheduler(time, sleep)

    # global ipcon

    ipcon.connect(HOST, PORT)

    # Register Enumerate Callback
    ipcon.register_callback(IPConnection.CALLBACK_ENUMERATE, cb_enumerate)

    # Trigger Enumerate
    ipcon.enumerate()

    sleep(2)

    if verbose:
        print(tfIDs)

    dmxcount = 0
    dmx = None
    for tf in tfIDs:
        # try:
        if True:
            # print(len(tf[0]))

            if len(tf[0])<=3: # if the device UID is 3 characters it is a bricklet
                if tf[1] in deviceIDs:
                    print(tf[0],tf[1], getIdentifier(tf))
                if tf[1] == 285: # DMX Bricklet
                    if dmxcount == 0:
                        print("Registering %s as slave DMX device for capturing DMX frames" % tf[0])
                        dmx = BrickletDMX(tf[0], ipcon)
                        # dmx.set_dmx_mode(BrickletDMX.DMX_MODE_SLAVE)
                        dmx.set_dmx_mode(dmx.DMX_MODE_MASTER)
                        # dmx.register_callback(BrickletDMX.CALLBACK_FRAME, dmxread_callback)
                        # dmx.set_frame_callback_config(False, False, True, False)
                        signal.signal(signal.SIGINT, signal_handler)

                    dmxcount += 1

    # print(dir(dmx))
    print("Time before running scheduler", time(), perf_counter())
    for sub in subs:
        # print(dir(sub))
        # print(sub.index, dir(sub.shift), sub.position, sub.split_timestamps)

        hours, minutes, seconds, milliseconds = time_convert(sub.start)
        t = seconds + minutes*60 + hours*60*60 + milliseconds/1000.0
        Timer(t, trigger_light_dmx, [sub.text_without_tags, dmx]).start()
        #print(time_convert(sub.start), time_convert(sub.end),  time_convert(sub.duration))
        # for each in sub.position:
        #     print(each)
        #print(sub.index, sub.shift, sub.position, sub.duration, sub.start, sub.end, sub.split_timestamps)
        # print(sub.text_without_tags)
        # print(sub, dir(sub))
        # s.enter(5, 1, print_time, ())
        # s.enter(10, 1, print_time, ())
    print("Time after running scheduler", time(), perf_counter())
    sys.exit()

    # 00:00:26,943 --> 00:00:27,223
    # DMX1(255, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    #  ['ITEM_PATTERN', 'TIMESTAMP_SEPARATOR', '__class__', '__delattr__', '__dict__',
    #'__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__',
    #'__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__',
    #'__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__',
    #'__sizeof__', '__str__', '__subclasshook__', '__weakref__', '_cmpkey', '_compare',
    #'characters_per_second', 'duration', 'end', 'from_lines', 'from_string', 'index',
    #'position', 'shift', 'split_timestamps', 'start', 'text', 'text_without_tags']

    # print("Time before running scheduler", time(), perf_counter())
    # # s.run()
    # print("Time after running scheduler", time(), perf_counter())

    print("Running event scheduler ...")

    print("Number of events",len(subs))
