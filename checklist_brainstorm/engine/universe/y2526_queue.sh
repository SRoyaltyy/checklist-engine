#!/bin/bash
cd /workspace/checklist_brainstorm/engine/universe
for y in 2025 2026; do
  while [ "$(free -g | awk '/Mem:/{print $7}')" -lt 5 ]; do echo "$(date +%T) waiting for memory"; sleep 60; done
  echo "$(date +%T) START NB $y"
  ( ulimit -v 3500000; python3 nb_year.py $y --block 150 ) || { echo "FAIL NB $y"; continue; }
  rm -f chunks/${y}__COUNTS2_NB__*.parquet; ( ulimit -v 3500000; python3 nb_counts.py $y | tail -1 ) || echo "COUNTS FAIL NB $y"
  echo "$(date +%T) START NBX $y"
  ( ulimit -v 3500000; python3 nbx_year.py $y | tail -1 ) || { echo "FAIL NBX $y"; continue; }
  rm -f chunks/${y}__COUNTS2_NBX__*.parquet; ( ulimit -v 3500000; python3 nbx_counts.py $y | tail -1 ) || echo "COUNTS FAIL NBX $y"
  echo "$(date +%T) DONE $y"
done; echo ALLDONE
