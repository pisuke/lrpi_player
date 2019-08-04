# LushRoom Pi player
Cloud connected sound and light player for Lush treatment rooms

Flask/omxplayer/vlcplayer/DMX/HUE/Tinkerforge/SRT

## Helpers

Sample sshfs command:

```
sudo sshfs -o allow_other,defer_permissions,IdentityFile=./lrpi_id_rsa lush@xxx.xxx.xxx.xxx:/home/lush ./mnt
```

Run dev code inside a running Dockerised player (only works on a 'Pi!):

```
sudo docker run -it --rm -p 80:80 \ 
-v ./flask:/opt/code/flask \ 
-v /opt/vc:/opt/vc \ 
-v /media/usb:/media/usb \ 
--device /dev/vchiq:/dev/vchiq \ 
--device /dev/fb0:/dev/fb0 \ 
lushroom-player:local
```


