#!/usr/bin/env python3
"""CLI: python answer_james.py --ticker X --date YYYY-MM-DD [--out file.csv]
columns: row_id,ticker,date,answer,reason,data_as_of  (answer in YES/NO/NOT_READY)"""
import os,sys,runpy
sys.argv[0]=os.path.join(os.path.dirname(os.path.realpath(__file__)),'readers','james.py')
runpy.run_path(sys.argv[0],run_name='__main__')
