"""Exit-grid regression tests (METHODOLOGY 0b 2026-10-24 ~13:30: a test that rule (20%%, 15d, no stop) reproduces
scoring/trades.py exit_v1 exactly, plus first-hit edge cases). Run: pytest tests/test_exit_grid.py
or simply: python -m scoring.exit_grid  (module self-checks, same assertions)."""
import subprocess, sys, os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_exit_grid_self_checks():
    r = subprocess.run([sys.executable, '-m', 'scoring.exit_grid'], cwd=HERE,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    assert 'exit_v1 reproduction OK' in r.stdout
