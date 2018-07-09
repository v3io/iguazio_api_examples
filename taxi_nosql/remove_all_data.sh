#!/bin/bash
source set_env.sh
hdfs dfs -rm -r $DRIVERS_TABLE
hdfs dfs -rm -r $PASSENGERS_TABLE
hdfs dfs -rm -r $CELLS_TABLE
