# The docker-compose file starts the player on port 80
# By default, $PORT is set to 8080 so you can run the dev code in tandem

PORT=8080

docker run -it --rm -p $PORT:$PORT \
-v /opt/vc:/opt/vc \
-v /media/usb:/media/usb \
-v /home/lush/lrpi_player/flask:/opt/code/flask \
--device /dev/vchiq:/dev/vchiq \
--device /dev/fb0:/dev/fb0 \
--entrypoint "/bin/bash" \
--network host \
--env PORT=$PORT \
lushdigital/lushroom-player:staging  
