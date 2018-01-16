#!/usr/bin/env bash

# Stream-data input file
STREAM_DATA_INPUT_FILE="drivers_data.csv"

# Add data to the stream and ingest it into the platform
python stream_driver_data.py ${STREAM_DATA_INPUT_FILE}

