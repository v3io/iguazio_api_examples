# Copyright 2017 Iguazio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#!/usr/bin/env bash

# Data-container name
CONTAINER_NAME="bigdata"
# IP address of the platform's web-gateway service
NGINX_IP="127.0.0.1"
# Port number of the platform's web-gateway service
NGINX_PORT="8081"
# Stream container-directory path
STREAM_PATH="/taxi_streaming_example/drivers_stream"
# Stream shard count
NUM_SHARDS=12

# Delete the stream by removing its container directory
for i in `eval echo {0..${NUM_SHARDS}}`
do
   echo "curl -v -XDELETE http://${NGINX_IP}:${NGINX_PORT}/${CONTAINER_NAME}/${STREAM_PATH}/$i"
   curl -v -XDELETE http://${NGINX_IP}:${NGINX_PORT}/${CONTAINER_NAME}/${STREAM_PATH}/$i
done

echo "Deleting the ${STREAM_PATH} stream from container ${CONTAINER_NAME} ..."
curl -v -XDELETE http://${NGINX_IP}:${NGINX_PORT}/${CONTAINER_NAME}${STREAM_PATH}/

