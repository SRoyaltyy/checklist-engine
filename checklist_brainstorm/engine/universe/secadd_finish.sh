#!/bin/bash
cd /workspace/checklist_brainstorm/engine/universe; export OPENBLAS_NUM_THREADS=1
L=../out/secadd_finish.log
# wait until available RAM > 6G (other bots' pulls)
for i in $(seq 1 120); do
  avail=$(free -g | awk '/^Mem:/{print $7}')
  [ "${avail:-0}" -ge 6 ] && break
  echo "$(date '+%F %T') wait mem avail=${avail}G" >> $L
  sleep 60
done
for y in 2024 2020 2021 2022 2023; do
  free_gb=$(df -BG --output=avail / | tail -1 | tr -dc 0-9)
  [ "$free_gb" -lt 4 ] && { echo "$(date '+%F %T') STOP disk ${free_gb}G" >> $L; exit 1; }
  echo "$(date '+%F %T') == $y" >> $L
  if [ $y = 2024 ]; then
    python3 -u secadd_equiv.py >> $L 2>&1
  else
    python3 -u secadd_equiv_y.py $y >> $L 2>&1
  fi && python3 -u secadd_counts.py $y >> $L 2>&1 && echo "$(date '+%F %T') SECADD READY $y" >> $L || echo "$(date '+%F %T') FAILED $y" >> $L
done
