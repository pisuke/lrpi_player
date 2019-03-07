#!/usr/bin/env python3

from phue import Bridge
from random import random
from time import sleep, time, perf_counter
# from sched import scheduler
from pysrt import SubRipFile, SubRipItem, SubRipTime
from pysrt import open as srtopen
from threading import Timer

from datetime import datetime, timedelta
import keyboard

from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler

import vlc
# import ctypes

import argparse

LIGHTING_MSGS = False

# SLEEP_TIME = 0.1 # seconds
MAX_BRIGHTNESS = 200
# TRANSITION_TIME = 10 # milliseconds
SRT_FILENAME = "Surround_Test_Audio.srt"
AUDIO_FILENAME = "Surround_Test_Audio.m4a"
HUE_IP_ADDRESS = "10.0.0.2"
TICK_TIME = 0.2 # seconds
PLAY_HUE = False
PLAY_AUDIO = True

subs = []
last_played = 0
player = None
b = None

def find_subtitle(subtitle, from_t, to_t, lo=0):
    i = lo
    while (i < len(subtitle)):
        # print(subtitle[i])
        if (subtitle[i].start >= to_t):
            break
        if (subtitle[i].start <= from_t) & (to_t  <= subtitle[i].end):
            print(subtitle[i].start, from_t, to_t)
            return subtitle[i].text, i
        i += 1
    return "", i

def end_callback(event):
    print('End of media stream (event %s)' % event.type)
    sys.exit(0)

def trigger_light_hue(subs):
    # print(perf_counter(), subs)
    commands = str(subs).split(";")
    global bridge
    for command in commands:
        try:
            # print(command)
            scope,items = command[0:len(command)-1].split("(")
            # print(scope,items)
            if scope[0:3] == "HUE":
                l = int(scope[3:])
                hue, sat, bri, TRANSITION_TIME = items.split(',')
                print(perf_counter(), l, hue, sat, bri, TRANSITION_TIME)
                cmd =  {'TRANSITION_TIME' : int(TRANSITION_TIME), 'on' : True, 'bri' : int(bri), 'sat' : int(sat), 'hue' : int(hue)}
                if PLAY_HUE:
                    b.set_light(l, cmd)
                if LIGHTING_MSGS:
                    print("Trigger light",l,cmd)
        except:
            pass
    print(30*'-')



def tick():
    global subs
    global player
    global last_played
    global TICK_TIME
    # print(subs[0])
    t = perf_counter()
    # ts = str(timedelta(seconds=t)).replace('.',',')
    # tsd = str(timedelta(seconds=t+10*TICK_TIME)).replace('.',',')
    ts = SubRipTime(seconds = t)
    tsd = SubRipTime(seconds = t+1*TICK_TIME)
    # print(dir(player))
    pp = player.get_position()
    ptms = player.get_time()/1000.0
    pt = SubRipTime(seconds=(player.get_time()/1000.0))
    ptd = SubRipTime(seconds=(player.get_time()/1000.0+1*TICK_TIME))
    print('Time: %s | %s | %s - %s | %s - %s | %s | %s' % (datetime.now(),t,ts,tsd,pt,ptd,pp,ptms))
    # sub, i = find_subtitle(subs, ts, tsd)
    sub, i = find_subtitle(subs, pt, ptd)
    # hours, minutes, seconds, milliseconds = time_convert(sub.start)
    # t = seconds + minutes*60 + hours*60*60 + milliseconds/1000.0
    print("Subtitle:", sub, i)
    if sub!="" and i > last_played:
        trigger_light_hue(sub)
        last_played=i

def time_convert(t):
    block, milliseconds = str(t).split(",")
    hours, minutes, seconds = block.split(":")
    return(int(hours),int(minutes),int(seconds), int(milliseconds))


def main():
    global subs
    global player
    global bridge
    global SRT_FILENAME, AUDIO_FILENAME, MAX_BRIGHTNESS, TICK_TIME, HUE_IP_ADDRESS
    parser = argparse.ArgumentParser(description="LushRoom sound and light command-line player")
    # group = parser.add_mutually_exclusive_group()
    # group.add_argument("-v", "--verbose", action="store_true")
    # group.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("-s","--srt", default=SRT_FILENAME, help=".srt file name for lighting events")
    parser.add_argument("-a","--audio", default=AUDIO_FILENAME, help="audio file for sound stream")
    parser.add_argument("-b","--brightness", default=MAX_BRIGHTNESS, help="maximum brightness")
    parser.add_argument("-t","--time", default=TICK_TIME, help="time between events")
    parser.add_argument("--hue", default=HUE_IP_ADDRESS, help="Philips Hue bridge IP address")

    args = parser.parse_args()

    print(args)

    if PLAY_AUDIO:
        player = vlc.MediaPlayer(AUDIO_FILENAME)
        event_manager = player.event_manager()
        event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, end_callback)

    if PLAY_HUE:
        # b = Bridge('lushroom-hue.local')
        bridge = Bridge(HUE_IP_ADDRESS, config_file_path="/media/usb/python_hue")
        # If the app is not registered and the button is not pressed, press the button and call connect() (this only needs to be run a single time)
        bridge.connect()
        # Get the bridge state (This returns the full dictionary that you can explore)
        bridge.get_api()
        lights = bridge.lights
        # Print light names
        for l in lights:
            print(l.name)
            #print(dir(l))
        # Set brightness of each light to 10
        for l in lights:
            l.brightness = 1

        # Get a dictionary with the light name as the key
        light_names = bridge.get_light_objects('name')
        print("Light names:", light_names)

    subs = srtopen(SRT_FILENAME)

    print("Number of lighting events",len(subs))

    scheduler = BackgroundScheduler()
    scheduler.add_job(tick, 'interval', seconds=TICK_TIME)
    # scheduler.start(paused=True)
    if PLAY_AUDIO:
        player.play()
    scheduler.start(paused=False)

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            sleep(0.01)
            try:
                if keyboard.is_pressed('p'): # pause
                    scheduler.pause()
                    player.pause()
                elif keyboard.is_pressed('r'): # resume
                    scheduler.resume()
                    player.play()
                # elif keyboard.is_pressed('s'): # stop
                #     scheduler.shutdown()
                #     player.stop()
                #     exit(0)
            except:
                pass
    except (KeyboardInterrupt, SystemExit):
        # Not strictly necessary if daemonic mode is enabled but should be done if possible
        scheduler.shutdown()
        player.stop()


if __name__ == "__main__":
    main()

# while True:
#     hue = int(random()*65535)
#     sat = int(random()*254)
#     bri = int(random()*MAX_BRIGHTNESS)
#     l = int(random()*len(lights))+1
#     command =  {'TRANSITION_TIME' : TRANSITION_TIME, 'on' : True, 'bri' : bri, 'sat' : sat, 'hue' : hue}
#     # if l == 0:
#     #     l = 1
#     b.set_light(l, command)
#     sleep(SLEEP_TIME)

#
# # Prints if light 1 is on or not
# b.get_light(1, 'on')
#
# # Set brightness of lamp 1 to max
# b.set_light(1, 'bri', 254)
#
# # Set brightness of lamp 2 to 50%
# b.set_light(2, 'bri', 127)
#
# # Turn lamp 2 on
# b.set_light(2,'on', True)
#
# # You can also control multiple lamps by sending a list as lamp_id
# b.set_light( [1,2], 'on', True)
#
# # Get the name of a lamp
# b.get_light(1, 'name')
#
# # You can also use light names instead of the id
# b.get_light('Kitchen')
# b.set_light('Kitchen', 'bri', 254)
#
# # Also works with lists
# b.set_light(['Bathroom', 'Garage'], 'on', False)
#
# # The set_light method can also take a dictionary as the second argument to do more fancy stuff
# # This will turn light 1 on with a transition time of 30 seconds
# command =  {'TRANSITION_TIME' : 300, 'on' : True, 'bri' : 254}
# b.set_light(1, command)

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

# print("Time before running scheduler", time(), perf_counter())
# for sub in subs:
#     # print(dir(sub))
#     # print(sub.index, dir(sub.shift), sub.position, sub.split_timestamps)
#
#     hours, minutes, seconds, milliseconds = time_convert(sub.start)
#     t = seconds + minutes*60 + hours*60*60 + milliseconds/1000.0
#     #Timer(t, trigger_light_hue, [sub.text_without_tags]).start()
#     #print(time_convert(sub.start), time_convert(sub.end),  time_convert(sub.duration))
#     # for each in sub.position:
#     #     print(each)
#     #print(sub.index, sub.shift, sub.position, sub.duration, sub.start, sub.end, sub.split_timestamps)
#     # print(sub.text_without_tags)
#     # print(sub, dir(sub))
#     # s.enter(5, 1, print_time, ())
#     # s.enter(10, 1, print_time, ())
#
# print("Time after running scheduler", time(), perf_counter())

# print("Running event scheduler ...")

# s = scheduler(time, sleep)

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
