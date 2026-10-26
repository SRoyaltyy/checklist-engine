"""Execute prerequisite stages while preserving the original upstream failure."""
import argparse,importlib,json,shlex,subprocess,sys
from collections import deque
from pathlib import Path
DEFAULT_IMPORTS=['world_snapshot_v2','world_timeframes','ci.world_v2_leak','ci.world_v2_coverage',
                 'ci.question_quality','price_reconcile','fetch.fetch_fred']


def stage(state_path,name,command,requires=()):
    target=Path(state_path)
    state=json.loads(target.read_text()) if target.exists() else {}
    for required in requires:
        upstream=state.get(required,{})
        if upstream.get('status')!='PASS':
            blocked=dict(status='BLOCKED_UPSTREAM',upstream=required,upstream_failure=upstream)
            state[name]=blocked;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(json.dumps(state,indent=2))
            print(f'BLOCKED_UPSTREAM {name}: '+json.dumps(blocked),flush=True)
            return 1
    tail=deque(maxlen=40)
    try:
        with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace') as process:
            for line in process.stdout:print(line,end='',flush=True);tail.append(line)
            code=process.wait()
    except OSError as exc:code=127;tail.append(str(exc))
    state[name]=dict(status='PASS' if code==0 else 'FAIL',command=command,command_display=shlex.join(command),
                     exit_code=code,log_excerpt=''.join(tail)[-6000:])
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(state,indent=2))
    return code


def publish(directory,tag,source_commit):
    root=Path(directory)
    files=sorted(p for p in root.iterdir() if p.is_file() and p.suffix in ('.parquet','.json','.csv')) if root.exists() else []
    if not files:raise SystemExit('Refusing an empty provisional release: no assets; GitHub was not called')
    notes=f'PROVISIONAL supplied-data evidence. Build source commit: {source_commit}. Read coverage/leak verdicts; no complete world-state approval.'
    subprocess.run(['gh','release','create',tag,'--draft','--target','main','--title',tag,'--notes',notes,*map(str,files)],check=True)
    count=subprocess.run(['gh','release','view',tag,'--json','assets','--jq','.assets | length'],check=True,capture_output=True,text=True)
    if int(count.stdout.strip())<1:raise SystemExit('Refusing to publish a draft release with zero uploaded assets')
    subprocess.run(['gh','release','edit',tag,'--draft=false'],check=True)


def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='operation',required=True)
    imports=sub.add_parser('imports');imports.add_argument('modules',nargs='*')
    run=sub.add_parser('run');run.add_argument('--state',required=True);run.add_argument('--stage',required=True)
    run.add_argument('--requires',nargs='*',default=[]);run.add_argument('command',nargs=argparse.REMAINDER)
    release=sub.add_parser('publish');release.add_argument('--directory',required=True);release.add_argument('--tag',required=True)
    release.add_argument('--source-commit',required=True)
    args=parser.parse_args()
    if args.operation=='imports':
        for module in args.modules or DEFAULT_IMPORTS:importlib.import_module(module);print('IMPORT_OK',module,flush=True)
    elif args.operation=='run':
        command=args.command[1:] if args.command[:1]==['--'] else args.command
        if not command:parser.error('a stage command is required')
        raise SystemExit(stage(args.state,args.stage,command,args.requires))
    else:publish(args.directory,args.tag,args.source_commit)


if __name__=='__main__':main()
