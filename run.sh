PORT=80

# --entrypoint "/bin/bash" \

sudo docker run -it --rm --network host -p $PORT:$PORT \
--env PORT=$PORT \
-v /opt/vc:/opt/vc \
-v /media/usb:/media/usb \
--device /dev/vchiq:/dev/vchiq \
--device /dev/fb0:/dev/fb0 \
lushdigital/lushroom-player:rpi3-pairing-fixes