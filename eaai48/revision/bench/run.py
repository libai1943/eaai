import argparse,concurrent.futures,hashlib,itertools,json,random,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parents[1]; OLD=R.parent
METHODS="adaptive proposed pso de cem cma bfgs poll random region_equal region_plain rc_no_refresh rc_no_poll rc_diagonal".split()
SEEDS=[4201,5209,6203]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source_id():
    files=sorted((R/'src').glob('*'))+[R/'bench/build.ps1',Path(__file__)]
    return {p.relative_to(R).as_posix():digest(p) for p in files if p.is_file()}
def identity(task,exe,m,s,b):
    return dict(schema=1,method=m,seed=s,budget=b,task_sha256=digest(task),binary_sha256=digest(exe),sources=source_id(),build=json.loads((R/'bench/build_info.json').read_text(encoding='utf-8-sig')))
def execute(case,m,s,b,task,out,resume=False,force=False):
    kind=case.split('_')[0];exe=R/('bench/dock.exe' if kind=='trailer' else 'bench/shared.exe')
    tag=identity(task,exe,m,s,b);meta=Path(str(out)+'.meta.json');csv=Path(str(out)+'.csv')
    if out.exists():
        if resume and meta.exists() and csv.exists():
            record=json.loads(meta.read_text())
            if record['identity']==tag and record['result_sha256']==digest(out) and record['trace_sha256']==digest(csv):return out
        if not force:raise RuntimeError(f'Existing record has no matching explicit resume identity: {out}; use --force to recompute')
    out.parent.mkdir(parents=True,exist_ok=True);tmp=out.with_suffix('.pending')
    cmd=([exe,task] if kind=='trailer' else [exe,kind,task])+[m,str(s),str(b),tmp]
    t=time.perf_counter();subprocess.run(list(map(str,cmd)),check=True,timeout=1800);elapsed=time.perf_counter()-t
    rec=json.loads(tmp.read_text());log=Path(str(tmp)+'.csv')
    if rec['evaluations']!=b or rec['method']!=m or len(log.read_bytes().splitlines())!=b+1:raise ValueError('Incomplete run output')
    log.replace(csv);tmp.replace(out)
    meta.write_text(json.dumps(dict(identity=tag,result_sha256=digest(out),trace_sha256=digest(csv),wall_seconds=elapsed),indent=2))
    return out
def launch(job,resume=False,force=False):
    case,m,s=job;kind=case.split('_')[0]
    task=(R if kind=='trailer' else OLD)/'data'/(case+'.task')
    return execute(case,m,s,6000 if kind=='parking' else 960,task,R/'runs'/f'{case}_{m}_{s}.json',resume,force)
def main():
    p=argparse.ArgumentParser();p.add_argument('--resume',action='store_true');p.add_argument('--force',action='store_true');p.add_argument('--workers',type=int,default=4);a=p.parse_args()
    (R/"runs").mkdir(exist_ok=True)
    jobs=list(itertools.product([f"{g}_{i:02}" for g in ["parking","trailer","arm","uav"] for i in range(1,13)],METHODS,SEEDS))
    random.Random(572).shuffle(jobs)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as pool:
        for i,_ in enumerate(pool.map(lambda job:launch(job,a.resume,a.force),jobs),1):
            if i%200==0:print(i,flush=True)
    print(len(jobs),"runs complete")
if __name__=="__main__":main()

