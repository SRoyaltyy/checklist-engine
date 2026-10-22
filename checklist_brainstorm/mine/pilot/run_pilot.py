#!/usr/bin/env python3
"""Orchestrate Taskforce checklist YES/NO mining pilot.

  python3 run_pilot.py --thin     # smoke: 12×20×james
  python3 run_pilot.py            # full universe×sessions; prefer Grok dumps
"""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thin", action="store_true")
    ap.add_argument("--force-readers", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--readers", default="james,trading-bot-taskforce")
    args = ap.parse_args()

    # 1) labels always
    subprocess.run([sys.executable, str(HERE / "labels.py")], check=True)

    # 2) panel
    cmd = [sys.executable, str(HERE / "build_panel.py"), "--workers", str(args.workers)]
    if args.thin:
        cmd.append("--thin")
    else:
        cmd += ["--readers", args.readers]
    if args.force_readers:
        cmd.append("--force-readers")
    print("EXEC", " ".join(cmd), flush=True)
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        sys.exit(rc)

    # 3) screen
    subprocess.run([sys.executable, str(HERE / "screen_singles.py")], check=True)
    print("DONE", HERE / "reports" / "smoke_report.md")


if __name__ == "__main__":
    main()
