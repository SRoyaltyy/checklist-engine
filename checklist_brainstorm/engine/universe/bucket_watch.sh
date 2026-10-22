#!/bin/bash
# Rebuild BUCKETS7 per year when SECADD lands. Drive upload must be done by an agent (no Drive creds in shell): marker UPLOAD_PENDING.
cd /workspace/checklist_brainstorm/engine/universe
L=/workspace/checklist_brainstorm/engine/out/bucket_watch.log; END=$(date -d '2026-10-23 02:00' +%s); done=""
echo "$(date '+%F %T HKT') start pid $$" >> $L
while :; do
  for y in 2020 2021 2022 2023 2024; do
    case " $done " in *" $y "*) continue;; esac
    if grep -qs "SECADD READY $y" ../out/secadd_2020_23.log secadd.log || [ -f chunks/${y}__COUNTS2_SECADD_ALL.parquet ]; then
      sleep 60  # let writer finish
      echo "$(date '+%F %T HKT') $y ready; rebuilding" >> $L
      if prlimit --as=6000000000 python3 -u bucket_counts.py $y >> $L 2>&1; then
        tar cf up_b7/buckets7_$y.tar chunks/${y}__BUCKETS7_*.parquet && echo "$(date '+%F %T HKT') UPLOAD_PENDING $y up_b7/buckets7_$y.tar sha256 $(sha256sum up_b7/buckets7_$y.tar|cut -c1-16)" >> $L
      else echo "$(date '+%F %T HKT') REBUILD FAILED $y" >> $L; fi
      done="$done $y"
    fi
  done
  [ $(echo $done | wc -w) -ge 5 ] && { echo "$(date '+%F %T HKT') all years done; exit" >> $L; exit 0; }
  [ $(date +%s) -ge $END ] && { echo "$(date '+%F %T HKT') deadline; exit (done:$done)" >> $L; exit 0; }
  sleep 120
done
