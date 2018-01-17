#!/usr/bin/env bash

# Stream-data input file
INPUT_FILE="drivers_data.csv"

# Add data to the stream and ingest it into the platform
python stream_drivers_data.py ${INPUT_FILE}

