# The docker-compose file starts the player on port 80
# By default, $PORT is set to 8080 so you can run the dev code in tandem

PORT=80

docker run -it --rm -p $PORT:$PORT \
--privileged \
-v /opt/vc:/opt/vc \
-v /media/usb:/media/usb \
-v /home/lush/workshop/LushRooms/lrpi_player/flask:/opt/code/flask \
--device /dev/vchiq:/dev/vchiq \
--device /dev/fb0:/dev/fb0 \
--entrypoint "/bin/bash" \
--network host \
--env PORT=$PORT \
lushdigital/lushroom-player:rpi3-pairing-fixes
