PORT=8080

sudo docker run -it --rm --network host -p $PORT:80 \
-v /home/lush/lrpi_player/flask:/opt/code/flask \
-v /opt/vc:/opt/vc \
-v /media/usb:/media/usb \
--device /dev/vchiq:/dev/vchiq \
--device /dev/fb0:/dev/fb0 \
lushdigital/lushroom-player:staging