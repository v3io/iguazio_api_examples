#!/usr/bin/env bash

NGINX_IP='10.90.1.101'
NUM_SHARDS=12
STREAM_NAME=training/flight_stream


for i in `eval echo {0..$NUM_SHARDS}`
do
   echo "curl -v -XDELETE http://$NGINX_IP:8081/1/$STREAM_NAME/$i"
   curl -v -XDELETE http://$NGINX_IP:8081/1/$STREAM_NAME/$i
done

echo "deleting flight_data dir"
curl -v -XDELETE http://$NGINX_IP:8081/1/$STREAM_NAME/

