#!/usr/bin/env bash

export NGINX_IP='10.90.1.11'

STREAM_NAME=training/flight_stream


curl  -X PUT \
     --header "Content-type: application/json" \
     --header "X-v3io-function: CreateStream" \
     --header "Cache-Control: no-cache" \
     --data '{"ShardCount": 12, "RetentionPeriodHours": 1}' \
     http://$NGINX_IP:8081/1/$STREAM_NAME/


