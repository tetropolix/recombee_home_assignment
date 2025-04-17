#!/bin/bash

START_TIME=$(date +%s.%N)
echo "First request sent at: $(date +"%Y-%m-%d %H:%M:%S.%3N")"

seq 1 20 | xargs  -P 20 -I {} curl -s -X POST \
  -H "Content-Type: application/xml" \
  --data @feed_example.xml \
  http://localhost:4444/feeds -o /dev/null

END_TIME=$(date +%s.%N)
echo "Last request sent at: $(date +"%Y-%m-%d %H:%M:%S.%3N")"