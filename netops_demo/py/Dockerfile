ARG NUCLIO_TAG=0.5.8
ARG NUCLIO_ARCH=amd64
ARG NUCLIO_BASE_IMAGE=python:3.7


# Supplies processor uhttpc, used for healthcheck
FROM nuclio/uhttpc:0.0.1-amd64 as uhttpc

# Supplies processor binary, wrapper
FROM nuclio/handler-builder-python-onbuild:${NUCLIO_TAG}-${NUCLIO_ARCH} as processor

# From the base image
FROM ${NUCLIO_BASE_IMAGE}

ARG MODEL_LOCATION_URL=http://192.168.224.49:8081/1/netops.model
ARG MODEL_FILE=/tmp/model/netops.model

ENV MODEL_FILE $MODEL_FILE
ENV MODEL_LOCATION_URL $MODEL_LOCATION_URL

# Copy required objects from the suppliers
COPY --from=processor /home/nuclio/bin/processor /usr/local/bin/processor
COPY --from=processor /home/nuclio/bin/py /opt/nuclio/
COPY --from=uhttpc /home/nuclio/bin/uhttpc /usr/local/bin/uhttpc

# Copy the appropriate functions
COPY functions/generate /opt/nuclio/functions/generate

# Copy all of the shared code
COPY libs /opt/nuclio/libs

# Copy requirements
COPY requirements.txt /opt/nuclio

# Readiness probe
HEALTHCHECK --interval=1s --timeout=3s CMD /usr/local/bin/uhttpc --url http://localhost:8082/ready || exit 1

# Run processor with configuration and platform configuration
CMD [ "processor", "--config", "/etc/nuclio/config/processor/processor.yaml", "--platform-config", "/etc/nuclio/config/platform/platform.yaml" ]

# Install packages
RUN echo "${MODEL_LOCATION_URL} && ${MODEL_FILE}"

## Download the model file and make it available locally
RUN mkdir -p /tmp/model &&  cd /tmp/model && \
curl -X GET \
    ${MODEL_LOCATION_URL} \
    -o ${MODEL_FILE} \
    -H 'authorization: Basic aWd1YXppbzpkYXRhbEBrZSE=' \
    -H 'cache-control: no-cache' \
    -H 'content-type: application/json'

RUN cd /opt/nuclio && pip install -r requirements.txt