"""Check original and added evaluation records without relabeling old experiments."""
import json,hashlib,csv
from pathlib import Path
from run import R,digest
A=R/'audit'
def main():
    root=A/'frozen_source';root.mkdir(exist_ok=True)
    # The runner's only subsequent edit accepts either UTF-8 or UTF-8-BOM build metadata.
    ref=json.loads(next((A/'validation/runs').glob('*.meta.json')).read_text())['identity']
    for name,sha in ref['sources'].items():
        src=(R/name).read_bytes()
        if hashlib.sha256(src).hexdigest()!=sha and name=='bench/run.py':
            src=src.replace(b".read_text(encoding='utf-8-sig')",b'.read_text()')
            src=src.replace(b'\r\n',b'\n')
        assert hashlib.sha256(src).hexdigest()==sha,name
        p=root/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(src)
    count=0
    for split in ['validation','holdout','matched']:
        groups={}
        for meta in (A/split/'runs').glob('*.meta.json'):
            r=json.loads(meta.read_text());p=Path(str(meta).removesuffix('.meta.json'));v=json.loads(p.read_text());c=Path(str(p)+'.csv');identity=r['identity']
            assert digest(p)==r['result_sha256'] and digest(c)==r['trace_sha256']
            assert v['method']==identity['method'] and v['evaluations']==identity['budget']
            lines=c.read_bytes().splitlines();assert len(lines)==v['evaluations']+1
            # Family + case prefix precedes method; method names may contain underscores.
            scene='_'.join(p.stem.split('_')[:2]);key=scene,identity['seed']
            assert groups.setdefault(key,lines[1:25])==lines[1:25]
            assert identity['sources']==ref['sources']
            kind=scene.split('_')[0];task=(A/split/'data' if split!='matched' else (R if kind=='trailer' else R.parent)/'data')/(scene+'.task')
            assert digest(task)==identity['task_sha256'];count+=1
    assert count==1916
    (A/'integrity.json').write_text(json.dumps(dict(new_records=count,validation=300,held_out=896,matched=720,common_initialization='verified within every scene--seed group',frozen_source='audit/frozen_source',source_hashes=ref['sources']),indent=2))
    print(count,'version-bound records, budgets and common initialization verified')
if __name__=='__main__':main()
