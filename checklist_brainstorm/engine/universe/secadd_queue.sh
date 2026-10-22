#!/bin/bash
# runs only after the main build is idle; one job at a time, memory-capped
cd /workspace/checklist_brainstorm/engine/universe; export OPENBLAS_NUM_THREADS=2
while pgrep -f "queue_shared.sh|watch_years.sh|tr_chain.sh|tr_year.py" > /dev/null; do sleep 30; done
L=secadd.log
prlimit --as=3000000000 python3 -u sector_addon.py A 2024 --workers 2 >> $L 2>&1 && \
prlimit --as=3000000000 python3 -u sector_addon.py B 2024 --workers 2 >> $L 2>&1 && \
prlimit --as=5000000000 python3 -u sector_addon.py assemble 2024 >> $L 2>&1 && \
prlimit --as=3000000000 python3 -u secadd_equiv.py >> $L 2>&1 && prlimit --as=4000000000 python3 -u secadd_counts.py 2024 >> $L 2>&1 && echo "SECADD READY 2024" >> $L
for y in 2025 2023 2022 2021 2020 2026; do prlimit --as=3000000000 python3 -u sector_addon.py A $y --workers 2 >> $L 2>&1; done
