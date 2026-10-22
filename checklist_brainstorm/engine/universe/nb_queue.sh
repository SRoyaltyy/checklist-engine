#!/bin/bash
# one year at a time; wait for >=5 GB available; ~3 GB virtual cap per job
cd /workspace/checklist_brainstorm/engine/universe
for y in "$@"; do
  while [ "$(free -g | awk '/Mem:/{print $7}')" -lt 5 ]; do echo "$(date +%T) waiting for memory"; sleep 60; done
  echo "$(date +%T) START $y"
  ( ulimit -v 3500000; python3 nb_year.py $y ) || { echo "FAIL $y"; continue; }
  ( ulimit -v 3500000; python3 nb_counts.py $y ) || echo "COUNTS FAIL $y"
  echo "$(date +%T) DONE $y"
done
