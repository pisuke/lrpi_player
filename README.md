# LushRoom Pi player

Cloud connected sound and light player for Lush treatment rooms

Flask/omxplayer/vlcplayer/DMX/HUE/Tinkerforge/SRT

## Helpers

Sample sshfs command:

```
sudo sshfs -o allow_other,defer_permissions,IdentityFile=./lrpi_id_rsa lush@xxx.xxx.xxx.xxx:/home/lush ./mnt
```

Run dev code inside a running Dockerised player (only works on a 'Pi!):

In Pod mode:

```
sudo docker run --env MENU_DMX_VAL="255,172,36" --env NUM_DMX_CHANNELS=192 -it --rm -p 80:80 \
-v /home/lush/lrpi_player/flask:/opt/code/flask \
-v /opt/vc:/opt/vc \
-v /media/usb:/media/usb \
--env BRICKD_HOST=localhost \
--network host \
--device /dev/vchiq:/dev/vchiq \
--device /dev/fb0:/dev/fb0 \
lushdigital/lushroom-player:staging
```

In Spa mode:

```
sudo docker run -it --rm -p 80:80 \
-v /home/lush/lrpi_player/flask:/opt/code/flask \
-v /opt/vc:/opt/vc \
-v /media/usb:/media/usb \
--env BRICKD_HOST=localhost \
--network host \
--device /dev/vchiq:/dev/vchiq \
--device /dev/fb0:/dev/fb0 \
lushdigital/lushroom-player:staging
```

Run a bash terminal for in depth debugging:

```
docker run -it --rm -p 80:80 -v /opt/vc:/opt/vc -v /media/usb:/media/usb --device /dev/vchiq:/dev/vchiq --device /dev/fb0:/dev/fb0 --entrypoint "/bin/bash" lushdigital/lushroom-player:staging

```

## Notes on running a dev environment in 2023

- Burn SD image using Rpi imager - Raspbian Legacy (buster) 32 bit
  - The required static libs in /opt/vc/lib are NOT THERE on bullseye+
- install docker with:

```
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

- then the usual https://docs.docker.com/engine/install/linux-postinstall/
- install docker compose [with this](https://dev.to/elalemanyo/how-to-install-docker-and-docker-compose-on-raspberry-pi-1mo)

```
sudo apt-get install libffi-dev libssl-dev
sudo apt install python3-dev
sudo apt-get install -y python3 python3-pip
sudo pip3 install docker-compose
sudo systemctl enable docker
```

- install sshfs

```
sudo apt install -y sshfs
```

- mount remote code with, e.g.

```
sudo sshfs -o allow_other,default_permissions inbrewj@pop-os:/home/inbrewj/workshop/LushRooms/lrpi_player ~/workshop/LushRooms/lrpi_player
```

unount remote code with, e.g.

https://askubuntu.com/a/1046832

```
sudo fusermount -u ~/workshop/LushRooms/lrpi_player
```

## Notes on cloning SD cards / volumes in general

https://beebom.com/how-clone-raspberry-pi-sd-card-windows-linux-macos/
