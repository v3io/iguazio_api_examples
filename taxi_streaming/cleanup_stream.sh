#!/usr/bin/env bash

# Data-container ID
CONTAINER_ID = 1  # assumes a default container with ID 1
# IP address of the platform's web-gateway service
NGINX_IP="127.0.0.1"
# Port number of the platform's web-gateway service
NGINX_PORT = "8081"
# Stream container-directory path
STREAM_PATH = "taxi_example/driver_stream"
# Stream shard count
NUM_SHARDS=12

# Delete the stream by removing its container directory
for i in `eval echo {0..${NUM_SHARDS}}`
do
   echo "curl -v -XDELETE http://${NGINX_IP}:${NGINX_PORT}/${CONTAINER_ID}/${STREAM_PATH}/$i"
   curl -v -XDELETE http://${NGINX_IP}:${NGINX_PORT}/${CONTAINER_ID}/${STREAM_PATH}/$i
done

echo "Deleting the ${STREAM_PATH} stream from container #${CONTAINER_ID} ..."
curl -v -XDELETE http://${NGINX_IP}:${NGINX_PORT}/1/${STREAM_PATH}/

