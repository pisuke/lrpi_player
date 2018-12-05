#!/usr/bin/env python3

from phue import Bridge
from random import random
from time import sleep, time, perf_counter
from sched import scheduler
from pysrt import SubRipFile, SubRipItem, SubRipTime
import pysrt
from threading import Timer

sleep_time = 0.1 # seconds
max_brightness = 20
transitiontime = 10 # milliseconds
srt_filename = "output.srt"

# b = Bridge('lushroom-hue.local')
b = Bridge('10.0.0.2')

# If the app is not registered and the button is not pressed, press the button and call connect() (this only needs to be run a single time)
b.connect()

# Get the bridge state (This returns the full dictionary that you can explore)
b.get_api()

lights = b.lights

# Print light names
for l in lights:
    print(l.name)
    print(dir(l))

# Set brightness of each light to 127
for l in lights:
    l.brightness = 10

# Get a dictionary with the light name as the key
light_names = b.get_light_objects('name')
print("Light names:", light_names)

subs = pysrt.open(srt_filename)

print("Number of events",len(subs))

# s = scheduler(time, sleep)

def trigger_light(subs):
    # print(perf_counter(), subs)
    commands = str(subs).split(";")
    for command in commands:
        # print(command)
        scope,items = command[0:len(command)-1].split("(")
        # print(scope,items)
        if scope[0:3] == "HUE":
            l = int(scope[3:])
            hue, sat, bri, transitiontime = items.split(',')
            print(perf_counter(), l, hue, sat, bri, transitiontime)
            cmd =  {'transitiontime' : int(transitiontime), 'on' : True, 'bri' : int(bri), 'sat' : int(sat), 'hue' : int(hue)}
            b.set_light(l, cmd)
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

print("Time before running scheduler", time(), perf_counter())
for sub in subs:
    # print(dir(sub))
    # print(sub.index, dir(sub.shift), sub.position, sub.split_timestamps)

    hours, minutes, seconds, milliseconds = time_convert(sub.start)
    t = seconds + minutes*60 + hours*60*60 + milliseconds/1000.0
    Timer(t, trigger_light, [sub.text_without_tags]).start()
    #print(time_convert(sub.start), time_convert(sub.end),  time_convert(sub.duration))
    # for each in sub.position:
    #     print(each)
    #print(sub.index, sub.shift, sub.position, sub.duration, sub.start, sub.end, sub.split_timestamps)
    # print(sub.text_without_tags)
    # print(sub, dir(sub))
    # s.enter(5, 1, print_time, ())
    # s.enter(10, 1, print_time, ())
print("Time after running scheduler", time(), perf_counter())

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

# while True:
#     hue = int(random()*65535)
#     sat = int(random()*254)
#     bri = int(random()*max_brightness)
#     l = int(random()*len(lights))+1
#     command =  {'transitiontime' : transitiontime, 'on' : True, 'bri' : bri, 'sat' : sat, 'hue' : hue}
#     # if l == 0:
#     #     l = 1
#     b.set_light(l, command)
#     sleep(sleep_time)

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
# command =  {'transitiontime' : 300, 'on' : True, 'bri' : 254}
# b.set_light(1, command)
