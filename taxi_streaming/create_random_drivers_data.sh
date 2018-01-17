#!/usr/bin/env bash

# Stream-data input file
INPUT_FILE="drivers_data.csv"

# Generate a file with random drivers stream data
python create_random_drivers_data.py > ${INPUT_FILE}

