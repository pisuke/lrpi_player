docker run -it --rm -p 80:80 \
-v /opt/vc:/opt/vc \
-v /media/usb:/media/usb \
-v /home/lush/lrpi_player/flask:/opt/code/flask \
--device /dev/vchiq:/dev/vchiq \
--device /dev/fb0:/dev/fb0 \
--entrypoint "/bin/bash" \
--network host \
lushdigital/lushroom-player:staging  
