#!/bin/bash
cd /workspace/checklist_brainstorm/engine/universe; export OPENBLAS_NUM_THREADS=2
for y in 2025 2026 2023 2022 2021 2020; do
  while [ ! -f chunks/${y}__SHARED.npz ] || ! grep -q "READY $y" watch.log 2>/dev/null; do [ $y -ge 2023 ] && break; sleep 30; done
  prlimit --as=6000000000 python3 -u tr_year.py $y >> tr_chain.log 2>&1 && prlimit --as=5500000000 python3 -u counts_v2.py $y >> tr_chain.log 2>&1 && echo "TRREADY $y" >> tr_chain.log
done
