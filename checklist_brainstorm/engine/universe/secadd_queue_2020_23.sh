#!/bin/bash
# Follow-on to secadd_queue.sh: for 2020-23 run A (idempotent, skips done dates), assemble, equivalence, counts.
# B (S&P stock-sector cells) is 2024-only; for 2020-23 the SP500 chunk carries SECTOR_ONLY ids only (STOCK_SECTOR = NR).
cd /workspace/checklist_brainstorm/engine/universe; export OPENBLAS_NUM_THREADS=2
L=../out/secadd_2020_23.log; WAIT=1019209
echo "$(date '+%F %T') start; waiting for secadd_queue.sh pid $WAIT" >> $L
while kill -0 $WAIT 2>/dev/null; do sleep 60; done
echo "$(date '+%F %T') secadd_queue.sh exited" >> $L
for y in 2020 2021 2022 2023; do
  free_gb=$(df -BG --output=avail / | tail -1 | tr -dc 0-9)
  if [ "$free_gb" -lt 5 ]; then echo "$(date '+%F %T') STOP: free disk ${free_gb}G < 5G before $y" >> $L; exit 1; fi
  echo "$(date '+%F %T') == $y (free ${free_gb}G)" >> $L
  prlimit --as=3000000000 python3 -u sector_addon.py A $y --workers 2 >> $L 2>&1 && \
  prlimit --as=5000000000 python3 -u sector_addon.py assemble $y >> $L 2>&1 && \
  prlimit --as=3000000000 python3 -u secadd_equiv_y.py $y >> $L 2>&1 && \
  prlimit --as=4000000000 python3 -u secadd_counts.py $y >> $L 2>&1 && echo "$(date '+%F %T') SECADD READY $y" >> $L || { echo "$(date '+%F %T') FAILED $y" >> $L; }
done
echo "$(date '+%F %T') done" >> $L
