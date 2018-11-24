# sample build command: sudo docker build -t media-warrior-base .
# sample run command: sudo docker run -d -p 80:80 arupiot/media_warrior_base:develop
# running resin.io rpi image on ubuntu with qemu
# (but) resin images have qemu built in anyway...
# sudo docker run -v /usr/bin/qemu-arm-static:/usr/bin/qemu-arm-static --rm -ti resin/rpi-raspbian

# get resin.io rpi image. Has QEMU built in
FROM lrpi_rpi_base:local

RUN [ "cross-build-start" ]

# make dirs

RUN mkdir /opt/code
RUN mkdir -p /media/usb/tracks
# ADD media-warrior-07dec249ae7a.json /opt/GCP
# ADD rclone1.43.1_expect.sh /

# copy mw_serve repo

RUN git clone --single-branch -b develop https://github.com/LUSHDigital/lrpi_player.git /opt/code 
# expect rclone1.43.1_expect.sh
# rclone sync arupiot-expect:mlp_samples_test /opt/usb -v -P

# TODO:
# set up rclone cron job
# set up rclone chronjob (updated every evening?)

# don't build angular app on the pi, it takes too long
# we serve the dist from the flask app

# serve Flask from 80
WORKDIR /opt/code/lrpi_player/flask

EXPOSE 80

RUN [ "cross-build-end" ]