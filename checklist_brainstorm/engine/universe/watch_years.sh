#!/bin/bash
cd /workspace/checklist_brainstorm/engine/universe
export OPENBLAS_NUM_THREADS=2
for y in 2023 2022 2021 2020; do
  while [ ! -f shared/$y.parquet ]; do sleep 30; done
  prlimit --as=4000000000 python3 labels_year.py $y >> watch.log 2>&1
  prlimit --as=5000000000 python3 -u engine_year.py $y >> watch.log 2>&1 && prlimit --as=5000000000 python3 counts_v2.py $y >> watch.log 2>&1 && tar -cf upload_$y.tar -C chunks $(cd chunks; ls ${y}__* | grep -v "__COUNTS\.parquet") && echo "READY $y" >> watch.log
done
