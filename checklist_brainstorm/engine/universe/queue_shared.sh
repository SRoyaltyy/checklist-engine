#!/bin/bash
cd /workspace/checklist_brainstorm/engine/universe

for y in 2024 2025 2026 2023 2022 2021 2020; do prlimit --as=3000000000 python3 -u shared_tier.py $y --workers 3 > shared_$y.log 2>&1; done
