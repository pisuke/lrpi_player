# lushroom-player Dockerfile

sudo docker build -t lushroom-player . && \
sudo docker images && \
sudo docker tag lushroom-player lushdigital/lushroom-player:"$1" && \
sudo docker push lushdigital/lushroom-player:"$1"
