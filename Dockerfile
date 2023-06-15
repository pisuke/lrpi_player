# sample build command: sudo docker build -t lrpi_player .
# running resin.io rpi image on ubuntu with qemu
# (but) resin images have qemu built in anyway...
# sudo docker run -v /usr/bin/qemu-arm-static:/usr/bin/qemu-arm-static --rm -ti resin/rpi-raspbian
# Sample run command with kernel/usb stick links
#### create symlinks for kernel libraries first!
#### In /opt/vc/lib of Hypriot v1.9.0:
#### sudo ln -s libbrcmEGL.so libEGL.so
#### sudo ln -s libbrcmGLESv2.so libGLESv2.so
#### sudo ln -s libbrcmOpenVG.so libOpenVG.so
#### sudo ln -s libbrcmWFC.so libWFC.so
# Then run with:
# docker run -it --rm -p 80:80 -v /opt/vc:/opt/vc -v /media/usb:/media/usb --device /dev/vchiq:/dev/vchiq --device /dev/fb0:/dev/fb0 lrpi_player

# get base image (based itself on a resin image). Has QEMU built in
FROM lushdigital/lushroom-base:latest

RUN [ "cross-build-start" ]

# make dirs

RUN mkdir /opt/code
RUN mkdir -p /media/usb

# Update stretch repositories
# see https://stackoverflow.com/questions/76094428/debian-stretch-repositories-404-not-found/76094521#76094521
RUN sed -i -e 's/deb.debian.org/archive.debian.org/g' \
    -e 's|security.debian.org|archive.debian.org/|g' \
    -e '/stretch-updates/d' /etc/apt/sources.list

# install a version of python that supports f strings (3.6)
# otherwise some dependency of zeroconf breaks everything

# deps for pyenv: https://github.com/pyenv/pyenv/wiki#suggested-build-environment

# RUN apt update 
# RUN apt-get install python3

RUN sudo apt-get install libatlas-base-dev psmisc

COPY flask /opt/code/flask
COPY requirements.txt /opt/code/requirements.txt
RUN pip3 install --no-cache-dir -r /opt/code/requirements.txt

# serve Flask from 80
WORKDIR /opt/code/flask

ENTRYPOINT ["python3"]
CMD ["Server.py"]

RUN [ "cross-build-end" ]
