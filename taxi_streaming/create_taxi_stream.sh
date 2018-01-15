#!/usr/bin/env bash

# IP address of the platform's web-gateway service
NGINX_IP="127.0.0.1"
# Port number of the platform's web-gateway service
NGINX_PORT="8081"
# Data-container ID
CONTAINER_ID=1  # assumes a default container with ID 1
# Stream container-directory path
STREAM_PATH="taxi_example/driver_stream"
# Stream shard count - the number of shards into which to divide the stream
NUM_SHARDS=12
# Stream retention period (starting from the stream's creation time), in hours.
# When this period expires, earlier data records might be deleted to make room
# for newer records.
RETENTION_PERIOD=1

# Create a new stream object using the platform's Streaming Web API
# CreateStream operation
curl -X PUT \
    --header "Content-type: application/json" \
    --header "X-v3io-function: CreateStream" \
    --header "Cache-Control: no-cache" \
    --data '{"ShardCount": ${NUM_SHARDS}, "RetentionPeriodHours": ${RETENTION_PERIOD}}' \
    http://${NGINX_IP}:${NGINX_PORT}/${CONTAINER_ID}/${STREAM_PATH}/

