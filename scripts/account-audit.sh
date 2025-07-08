#!/bin/bash

# Check if an output filename was provided
if [ -z "$1" ]; then
  echo "Usage: $0 output_filename"
  exit 1
fi

OUTPUT="$1".txt

python3 backups.py >> "$OUTPUT" 2>&1
python3 event-bridge.py >> "$OUTPUT" 2>&1
python3 iam.py >> "$OUTPUT" 2>&1
python3 kms.py >> "$OUTPUT" 2>&1
python3 lambda.py >> "$OUTPUT" 2>&1
python3 ram.py >> "$OUTPUT" 2>&1
python3 security-services.py >> "$OUTPUT" 2>&1
python3 region-service-discover.py >> "$OUTPUT" 2>&1
python3 s3.py >> "$OUTPUT" 2>&1
python3 ami.py >> "$OUTPUT" 2>&1

