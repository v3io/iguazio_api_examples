#!/usr/bin/env bash

# Stream-data input file
STREAM_DATA_INPUT_FILE="drivers_data.csv"

# Generate a file with random drivers stream data
python create_random_drivers_data.py > ${STREAM_DATA_INPUT_FILE}

