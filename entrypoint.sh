#!/bin/bash

logfile="/data/init.log"
echo "Checking jageocoder dictionary..." > ${logfile}

# Search the most recent dictionary file
dicfile=$(ls -t /data/*.zip | head -n1)

# Check if jageocoder dictionary is installed
do_install=false
triefile="/opt/db2/address.trie"
if [ ! -e "${triefile}" ]; then
  echo "  No dictionary is installed." >> ${logfile}
  do_install=true
elif [ ! -z "${dicfile}" ] && [ "${dicfile}" -nt "${triefile}" ]; then
  echo "  The dictionary file is newer than the installed dictionary." >> ${logfile}
  do_install=true
fi

if ${do_install} = true; then
  if [ -z "${dicfile}" ]; then
    echo "[NG] Please place the jageocoder dictionary file in the data directory." >> ${logfile}
    exit 1
  fi

  echo "  Installing dictionary from '${dicfile}'..." >> ${logfile}
  jageocoder install-dictionary -y ${dicfile} >> ${logfile} 2>&1
  if [ $? -ne 0 ]; then
    echo "[NG] Dictionary installation failed." >> ${logfile}
    exit 1
  fi

  if [ ${BUILD_RTREE} -ne 0 ] ; then
    echo "  Building R-tree for reverse geocoding..." >> ${logfile}
    jageocoder reverse 140.0 35.0 >> ${logfile} 2>&1
    if [ $? -ne 0 ]; then
      echo "[NG] R-tree build failed." >> ${logfile}
      exit 1
    fi
  fi
  echo "[OK] The dictionary is installed successfully." >> ${logfile}
else
  echo "[OK] The dictionary is already installed." >> ${logfile}
fi

echo "Starting server process..." >> ${logfile}
python run_waitress.py
