#!/bin/sh

# Check if jageocoder dictionary is installed

if [ ! -e "/opt/db2/address.trie" ]; then
  echo "Initialize..." > /data/init.log
  echo "Installing dictionary from ${DICFILE}..." >> /data/init.log
  jageocoder install-dictionary ${DICFILE} >> /data/init.log 2>&1
  echo "Building R-tree for reverse geocoding..." >> /data/init.log
  jageocoder reverse 140.0 35.0 >> /data/init.log 2>&1
  echo "All done." >> /data/init.log
fi

gunicorn app:app --bind=0.0.0.0:5000
