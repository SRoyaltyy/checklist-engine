"""Compatibility CLI for verified, versioned SEC quarterly fixed fields."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from ci.sec_quarterly_retained import main

if __name__=='__main__':main()
