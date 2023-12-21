# lushroom-player Dockerfile

docker build -t lushroom-player . -f Dockerfile.rpi3_32bit && \
docker images && \
docker tag lushroom-player lushdigital/lushroom-player:rpi3-32bit && \
docker push lushdigital/lushroom-player:rpi3-32bit
