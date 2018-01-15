#!/usr/bin/env bash

NGINX_IP="127.0.0.1"
NGINX_PORT="8081"
CONTAINER_ID=1
STREAM_PATH="taxi_example/driver_stream"

curl -X PUT \
    --header "Content-type: application/json" \
    --header "X-v3io-function: CreateStream" \
    --header "Cache-Control: no-cache" \
    --data '{"ShardCount": 12, "RetentionPeriodHours": 1}' \
    http://${NGINX_IP}:${NGINX_PORT}/${CONTAINER_ID}/${STREAM_PATH}/
