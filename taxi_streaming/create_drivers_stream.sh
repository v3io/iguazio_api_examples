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

# IP address of the platform's web-gateway service
NGINX_IP="127.0.0.1"
# Port number of the platform's web-gateway service
NGINX_PORT="8081"
# Data-container name
CONTAINER_NAME="bigdata"
# Stream container-directory path
STREAM_PATH="/taxi_streaming_example/drivers_stream"
# Stream shard count - the number of shards into which to divide the stream
NUM_SHARDS=12
# Stream retention period (starting from the stream's creation time), in hours.
# When this period elapses, earlier data records might be deleted to make room
# for newer records.
RETENTION_PERIOD=1

# Create a new stream object using the platform's Streaming Web API
# CreateStream operation
curl -X PUT \
    --header "Content-type: application/json" \
    --header "X-v3io-function: CreateStream" \
    --header "Cache-Control: no-cache" \
    --data "{'ShardCount': ${NUM_SHARDS}, 'RetentionPeriodHours': ${RETENTION_PERIOD}}" \
    http://${NGINX_IP}:${NGINX_PORT}/${CONTAINER_NAME}${STREAM_PATH}/

