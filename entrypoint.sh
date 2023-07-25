#!/bin/sh

# Check if jageocoder dictionary is installed
if [ ! -e "/opt/db2/address.trie" ]; then
  echo "Initialize..." > /data/init.log
  echo "Installing dictionary..." >> /data/init.log
  jageocoder install-dictionary /data/*.zip >> /data/init.log 2>&1
  if [ ${BUILD_RTREE} -ne 0 ] ; then
    echo "Building R-tree for reverse geocoding..." >> /data/init.log
    jageocoder reverse 140.0 35.0 >> /data/init.log 2>&1
  fi
  echo "All done." >> /data/init.log
fi

python run_waitress.py
