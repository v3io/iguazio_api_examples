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

