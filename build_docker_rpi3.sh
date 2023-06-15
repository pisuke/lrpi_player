# lushroom-player Dockerfile, rpi4 edition (64 bit, mpv based)

BUILD_DIR="./docker-builds"
BUILD_TAG="32-bit-rpi3"

echo "***** Building Lushrooms Pi Rpi4..."

mkdir $BUILD_DIR || true && \
sudo docker build -t lushroom-player:$BUILD_TAG -f ./Dockerfile . && \
echo "***** Saving Lushrooms Pi Rpi3 img to tarball..." && \
docker save -o $BUILD_DIR/lrpi3-img-32.tar lushroom-player:$BUILD_TAG && \
echo "***** Lushrooms Pi Rpi3 image built and saved..." && \
echo "***** Tarred up image: " && \
ls -lah $BUILD_DIR
