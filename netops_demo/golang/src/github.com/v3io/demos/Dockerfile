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
ARG NUCLIO_LABEL=0.5.15
ARG NUCLIO_ARCH=amd64
ARG NUCLIO_BASE_IMAGE=alpine:3.7
ARG NUCLIO_ONBUILD_IMAGE=nuclio/handler-builder-golang-onbuild:${NUCLIO_LABEL}-${NUCLIO_ARCH}-alpine

# Supplies processor uhttpc, used for healthcheck
FROM nuclio/uhttpc:0.0.1-amd64 as uhttpc

# Builds source, supplies processor binary and handler plugin
FROM ${NUCLIO_ONBUILD_IMAGE} as builder

# From the base image
FROM ${NUCLIO_BASE_IMAGE}

# install ca-certificates to get HTTPS
RUN apk add --no-cache --update ca-certificates

# Copy required objects from the suppliers
COPY --from=builder /home/nuclio/bin/processor /usr/local/bin/processor
COPY --from=builder /home/nuclio/bin/handler.so /opt/nuclio/handler.so
COPY --from=uhttpc /home/nuclio/bin/uhttpc /usr/local/bin/uhttpc

# Readiness probe
HEALTHCHECK --interval=1s --timeout=3s CMD /usr/local/bin/uhttpc --url http://127.0.0.1:8082/ready || exit 1

# Run processor with configuration and platform configuration
CMD [ "processor", "--config", "/etc/nuclio/config/processor/processor.yaml", "--platform-config", "/etc/nuclio/config/platform/platform.yaml" ]
