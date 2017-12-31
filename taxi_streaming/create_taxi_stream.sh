#!/usr/bin/env bash

NGINX_IP=‘127.0.0.1’

STREAM_NAME=taxi_example/driver_stream

curl  -X PUT \
     --header "Content-type: application/json" \
     --header "X-v3io-function: CreateStream" \
     --header "Cache-Control: no-cache" \
     --data '{"ShardCount": 12, "RetentionPeriodHours": 1}' \
     http://127.0.0.1:8081/1/$STREAM_NAME/


