#!/usr/bin/env bash

NGINX_IP='127.0.0.1'
NUM_SHARDS=12
STREAM_NAME=taxi_example/driver_stream

for i in `eval echo {0..$NUM_SHARDS}`
do
   echo "curl -v -XDELETE http://$NGINX_IP:8081/1/$STREAM_NAME/$i"
   curl -v -XDELETE http://$NGINX_IP:8081/1/$STREAM_NAME/$i
done

echo "deleting taxi_stream dir"
curl -v -XDELETE http://$NGINX_IP:8081/1/$STREAM_NAME/

