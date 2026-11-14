"""Matched batch, learning rates, scale and initialization controls on original scenes."""
import json,itertools,csv,random
from concurrent.futures import ThreadPoolExecutor
from review_panel import A,R,FAMILIES
from run import execute,SEEDS
from physical import spatial_many,car
from verify import dock_many
METHODS=['cma_matched','cma_regions_equal','cma_regions_adaptive','rc_balanced_first','rc_simple']
def main():
    tasks=[(g,f'{g}_{k:02}',(R if g=='trailer' else R.parent)/'data'/f'{g}_{k:02}.task') for g in FAMILIES for k in range(1,13)]
    jobs=list(itertools.product(tasks,METHODS,SEEDS));random.Random(641).shuffle(jobs)
    def work(job):
        (g,case,p),m,s=job
        execute(case,m,s,6000 if g=='parking' else 960,p,A/'matched/runs'/f'{case}_{m}_{s}.json',resume=True)
    with ThreadPoolExecutor(4) as pool:
        for i,_ in enumerate(pool.map(work,jobs),1):
            if i%80==0:print('matched',i,'/',len(jobs),flush=True)
    rows=[]
    for g,case,p in tasks:
        cfg=json.loads(p.with_suffix('.json').read_text());files=[A/'matched/runs'/f'{case}_{m}_{s}.json' for m,s in itertools.product(METHODS,SEEDS)];rec=[json.loads(f.read_text()) for f in files];idx=[i for i,r in enumerate(rec) if r['loss']==0];checks={}
        if idx:
            if g=='parking':checks={i:car(cfg,rec[i]['z'])[0] for i in idx}
            else:checks=dict(zip(idx,dock_many(cfg,[rec[i] for i in idx])[0] if g=='trailer' else spatial_many(cfg,[rec[i] for i in idx])))
        for i,(f,r) in enumerate(zip(files,rec)):
            a=checks.get(i,{});rows.append(dict(case=case,family=g,method=r['method'],seed=int(f.stem.split('_')[-1]),valid=int(bool(a.get('ok'))),cost=a.get('J') if a.get('ok') else None,first=r['first'],loss=r['loss']))
    with (A/'matched/verified.csv').open('w',newline='') as f:w=csv.DictWriter(f,rows[0]);w.writeheader();w.writerows(rows)
    print(len(rows),'matched records checked',flush=True)
if __name__=='__main__':main()
