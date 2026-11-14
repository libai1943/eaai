"""Frozen audit follow-up. Validation selects a variant before held-out results exist."""
import argparse,csv,json,copy,itertools,random,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from run import R,execute,source_id
from physical import spatial_many,car
from verify import dock_many
A=R/'audit';FAMILIES=['parking','uav','arm','trailer']
VARIANTS=['adaptive','rc_no_poll','rc_diagonal','rc_balanced_first','rc_simple']
CONTROLS=['cma','cma_matched','cma_regions_equal','cma_regions_adaptive','de','random']
def write_task(c,p):
    g=c['kind']
    if g=='parking':lines=[c['endpoints'],[len(c['polygons'])]]+[np.asarray(x).ravel() for x in c['polygons']]
    elif g=='trailer':lines=[[*c['start'],*c['goal'],len(c['rectangles'])]]+c['rectangles']+[[int(c['withdrawal'])]]
    else:
        lines=[[g,c['N'],c['nx'],c['nu']],[12],[len(c['obstacles'])]]+c['obstacles']+[c['lower'],c['upper'],c['start'],c['goal']]
    p.write_text('\n'.join(' '.join(map(str,row)) for row in lines)+'\n')
def generate():
    for split,count,seed in [('validation',3,110141),('holdout',4,110142)]:
        d=A/split/'data';d.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(seed)
        for g in FAMILIES:
            for k in range(1,count+1):
                base=([2,5,9][k-1] if split=='validation' else [1,4,8,11][k-1]);name=f'{g}_{k:02}'
                c=json.loads(((R if g=='trailer' else R.parent)/'data'/f'{g}_{base:02}.json').read_text());c['kind']=g
                c['parent_scene']=f'{g}_{base:02}';c['split']=split
                if g=='parking':
                    e=np.array(c['endpoints']);e[:3]+=rng.uniform([-0.25,-0.25,-.05],[.25,.25,.05]);c['endpoints']=e.tolist()
                    c['polygons']=[(np.array(o)+rng.uniform(-.06,.06,2)).tolist() for o in c['polygons']]
                elif g=='uav':
                    o=np.array(c['obstacles'])
                    for i in range(0,len(o),4):
                        dy,dz=rng.uniform([-.35,-.15],[.35,.15]);wy=(o[i+1,1]-o[i,4])*rng.uniform(.9,1.1);wz=(o[i+3,2]-o[i+2,5])*rng.uniform(.9,1.1)
                        y=(o[i+1,1]+o[i,4])/2+dy;z=(o[i+3,2]+o[i+2,5])/2+dz
                        o[i,4]=y-wy/2;o[i+1,1]=y+wy/2;o[i+2:i+4,1]=y-wy/2;o[i+2:i+4,4]=y+wy/2;o[i+2,5]=z-wz/2;o[i+3,2]=z+wz/2
                    c['obstacles']=o.tolist();c['goal'][1]+=float(rng.uniform(-.3,.3))
                elif g=='arm':
                    o=np.array(c['obstacles']);offset=rng.uniform(-.06,.06,(len(o),3));o[:,:3]+=offset;o[:,3:]+=offset;c['obstacles']=o.tolist()
                    c['goal'][:3]=(np.array(c['goal'][:3])+rng.uniform(-.08,.08,3)).tolist()
                else:
                    c['start'][:2]=(np.array(c['start'][:2])+rng.uniform(-.25,.25,2)).tolist()
                    for box in c['rectangles'][3:]:box[0]+=float(rng.uniform(-.12,.12));box[1]+=float(rng.uniform(-.12,.12))
                (d/(name+'.json')).write_text(json.dumps(c,indent=2));write_task(c,d/(name+'.task'))
    (A/'protocol.json').write_text(json.dumps(dict(variants=VARIANTS,controls=CONTROLS,validation_seeds=[7101,7103,7109,7121,7127],holdout_seeds=[8101,8107,8111,8117,8123,8147,8161,8167],selection='Highest independent acceptance count, then lowest median cost normalized by the best accepted candidate in each pair; fixed tie order in variants.',scope='New endpoint and obstacle perturbations of fixed task templates; not a new environment topology distribution.',source=source_id()),indent=2))
def accept(cfg,rec):
    if rec['loss']!=0:return dict(ok=False,J=None)
    g=cfg['kind']
    return car(cfg,rec['z'])[0] if g=='parking' else dock_many(cfg,[rec])[0][0] if g=='trailer' else spatial_many(cfg,[rec])[0]
def run(split):
    spec=json.loads((A/'protocol.json').read_text());seeds=spec[split+'_seeds'];methods=VARIANTS if split=='validation' else [json.loads((A/'selection.json').read_text())['selected'],'adaptive']+CONTROLS
    methods=list(dict.fromkeys(methods));tasks=sorted((A/split/'data').glob('*.task'));jobs=list(itertools.product(tasks,methods,seeds));random.Random(531).shuffle(jobs)
    def work(job):
        p,m,s=job;case=p.stem;out=A/split/'runs'/f'{case}_{m}_{s}.json'
        execute(case,m,s,6000 if case.startswith('parking') else 960,p,out,resume=True)
    with ThreadPoolExecutor(4) as pool:
        for i,_ in enumerate(pool.map(work,jobs),1):
            if i%40==0:print(split,i,'/',len(jobs),flush=True)
    rows=[]
    for p in tasks:
        cfg=json.loads(p.with_suffix('.json').read_text());case=p.stem
        # Batch the expensive articulated/spatial independent replay.
        fs=[A/split/'runs'/f'{case}_{m}_{s}.json' for m,s in itertools.product(methods,seeds)]
        rec=[json.loads(f.read_text()) for f in fs];idx=[i for i,r in enumerate(rec) if r['loss']==0];checks={}
        if idx:
            if cfg['kind']=='parking':checks={i:car(cfg,rec[i]['z'])[0] for i in idx}
            else:
                a=dock_many(cfg,[rec[i] for i in idx])[0] if cfg['kind']=='trailer' else spatial_many(cfg,[rec[i] for i in idx]);checks=dict(zip(idx,a))
        for i,(f,r) in enumerate(zip(fs,rec)):
            a=checks.get(i,{});rows.append(dict(case=case,family=cfg['kind'],method=r['method'],seed=int(f.stem.split('_')[-1]),valid=int(bool(a.get('ok'))),cost=a.get('J') if a.get('ok') else None,first=r['first'],loss=r['loss']))
    with (A/split/'verified.csv').open('w',newline='') as f:w=csv.DictWriter(f,rows[0]);w.writeheader();w.writerows(rows)
    if split=='validation':
        groups={}
        for r in rows:
            if r['valid']:groups.setdefault((r['case'],r['seed']),[]).append(r['cost'])
        score={m:dict(success=sum(r['valid'] for r in rows if r['method']==m),ratio=float(np.median([r['cost']/min(groups[r['case'],r['seed']]) for r in rows if r['method']==m and r['valid']]))) for m in methods}
        winner=min(methods,key=lambda m:(-score[m]['success'],score[m]['ratio'],methods.index(m)))
        (A/'selection.json').write_text(json.dumps(dict(selected=winner,scores=score,source=source_id()),indent=2));print('SELECTION',winner,score,flush=True)
    print(split,len(rows),'independently checked',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['generate','validation','holdout']);a=p.parse_args()
    if a.action=='generate':generate()
    else:run(a.action)
