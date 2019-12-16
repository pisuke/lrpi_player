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

RUN sudo apt-get install libatlas-base-dev psmisc

COPY flask /opt/code/flask
COPY requirements.txt /opt/code/requirements.txt
RUN pip3 install -r /opt/code/requirements.txt

# serve Flask from 80
WORKDIR /opt/code/flask

ENTRYPOINT ["python3"]
CMD ["Server.py"]

RUN [ "cross-build-end" ]
