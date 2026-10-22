for y in 2020 2021 2022 2023 2024; do
  while [ $(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo) -lt 5 ]; do sleep 30; done
  python3 nbx_year.py $y && python3 nbx_counts.py $y | tail -1
done; echo ALLDONE
