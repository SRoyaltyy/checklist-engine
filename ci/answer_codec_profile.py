"""Synthetic-only V1 compatibility/performance measurement against frozen codec."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import time
import types

BASE='9b3957d33b616ed8d12ca6eb6a4b1c24889d8bf4'


def measure(directory):
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import world_answer_cache as current
    source=subprocess.check_output(['git','show',BASE+':world_answer_cache.py'])
    legacy=types.ModuleType('legacy_answer_codec');exec(compile(source,BASE+':world_answer_cache.py','exec'),legacy.__dict__)
    provenance={key:'a'*64 for key in current.PROVENANCE};rng=np.random.default_rng(1704);results=[]
    for rows in (9,1024,4096,16384):
        registry=[dict(question_id='q'+str(i),outcomes=[0,1]) for i in range(128)]
        values=rng.integers(0,3,size=(rows,128)).astype(float);values[values==2]=np.nan
        frame=pd.DataFrame(values,columns=[q['question_id'] for q in registry]);times={}
        a=legacy.encode_answers(frame,registry,provenance);b=current.encode_answers(frame,registry,provenance)
        if a!=b:raise ValueError('V1 compressed bytes or metadata changed')
        old=legacy.decode_answers(*a,registry,provenance);new=current.decode_answers(*b,registry,provenance)
        pd.testing.assert_frame_equal(old,new)
        for label,module in (('legacy',legacy),('current',current)):
            encode=[];decode=[]
            for repeat in range(3):
                started=time.perf_counter();module.encode_answers(frame,registry,provenance);encode.append(time.perf_counter()-started)
                started=time.perf_counter();module.decode_answers(*a,registry,provenance);decode.append(time.perf_counter()-started)
            times[label]=dict(encode_seconds=statistics.median(encode),decode_seconds=statistics.median(decode))
        results.append(dict(rows=rows,questions=128,cells=int(frame.size),compressed_bytes=len(a[0]),
            identical_compressed_bytes_and_metadata=True,identical_decoded_frame=True,timings=times,
            encode_speedup=times['legacy']['encode_seconds']/times['current']['encode_seconds'],
            decode_speedup=times['legacy']['decode_seconds']/times['current']['decode_seconds']))
    modes=[]
    for dtype in ('bool','int8','int64','uint64','float16','float32','float64','object','Int64','Float64'):
        frame=pd.DataFrame({'q':pd.Series([0,1],dtype=dtype)});registry=[dict(question_id='q',outcomes=[0,1])]
        outcomes=[]
        for module in (legacy,current):
            try:outcomes.append(('ACCEPT',module.encode_answers(frame,registry,provenance)))
            except (ValueError,TypeError,NotImplementedError) as exc:outcomes.append((type(exc).__name__,str(exc)))
        if outcomes[0]!=outcomes[1]:raise ValueError('registered dtype acceptance or V1 bytes changed: '+dtype)
        modes.append(dict(dtype=dtype,identical_domain_and_bytes=True,result=outcomes[0][0]))
    report=dict(format='ANSWER_CODEC_SYNTHETIC_PROFILE_V1',baseline_commit=BASE,baseline_source_sha256=hashlib.sha256(source).hexdigest(),
        source_commit=os.environ.get('GITHUB_SHA'),runtime=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,pyarrow=pa.__version__),
        results=results,dtype_parity=modes,status='PASS_EXACT_V1_COMPATIBILITY',market_computations=0,
        limitation='Synthetic binary chunks only; no measured full stock speedup, numerical-price/PIT change or live-run code change. Timing is reported, not a flaky pass threshold.')
    directory.mkdir(parents=True,exist_ok=True);(directory/'ANSWER_CODEC_SYNTHETIC_PROFILE_V1.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=report['status'],dtype_cases=len(modes),results=results),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True);args=parser.parse_args();measure(Path(args.directory))
