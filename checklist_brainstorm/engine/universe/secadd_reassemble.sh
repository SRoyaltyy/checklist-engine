#!/bin/bash
cd /workspace/checklist_brainstorm/engine/universe; export OPENBLAS_NUM_THREADS=2
L=../out/secadd_reassemble.log
for y in 2024 2020 2021 2022 2023; do
  free_gb=$(df -BG --output=avail / | tail -1 | tr -dc 0-9)
  [ "$free_gb" -lt 4 ] && { echo "$(date '+%F %T') STOP disk ${free_gb}G" >> $L; exit 1; }
  echo "$(date '+%F %T') == $y" >> $L
  prlimit --as=8500000000 python3 -u sector_addon.py assemble $y >> $L 2>&1 && \
  { if [ $y = 2024 ]; then prlimit --as=3000000000 python3 -u secadd_equiv.py; else prlimit --as=3000000000 python3 -u secadd_equiv_y.py $y; fi; } >> $L 2>&1 && \
  prlimit --as=4000000000 python3 -u secadd_counts.py $y >> $L 2>&1 && echo "$(date '+%F %T') SECADD READY $y" >> $L || echo "$(date '+%F %T') FAILED $y" >> $L
done
