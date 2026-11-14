"""Adversarial input and cache regressions from the independent review."""
import copy,json,subprocess,tempfile,unittest
from pathlib import Path
import numpy as np
from run import R,execute
from physical import spatial_many,car
from verify import dock_many
class Contracts(unittest.TestCase):
    def test_spatial_records(self):
        for g in ('uav','arm'):
            cfg=json.loads((R.parent/'data'/f'{g}_02.json').read_text());v=json.loads((R/'runs'/f'{g}_02_adaptive_4201.json').read_text())
            self.assertTrue(spatial_many(cfg,[v])[0]['ok'])
            for value in (-v['z'][0],0,.49,101,float('nan'),float('inf')):
                bad=copy.deepcopy(v);bad['z'][0]=value
                with self.assertRaises(ValueError):spatial_many(cfg,[bad])
            bad=copy.deepcopy(v);bad['z'].pop()
            with self.assertRaises(ValueError):spatial_many(cfg,[bad])
            bad=copy.deepcopy(v);bad['z'][10]+=.002
            self.assertFalse(spatial_many(cfg,[bad])[0]['ok'])
    def test_docking_time_and_parking_nan(self):
        cfg=json.loads((R/'data/trailer_02.json').read_text());v=json.loads((R/'runs/trailer_02_adaptive_4201.json').read_text());v['z'][3]=-1
        with self.assertRaises(ValueError):dock_many(cfg,[v])
        with self.assertRaises(ValueError):car({},[0,float('nan')])
    def test_cli_and_budget(self):
        with tempfile.TemporaryDirectory(dir=R/'tmp') as t:
            for prefix in ([R/'bench/dock.exe',R/'data/trailer_02.task'],[R/'bench/shared.exe','uav',R.parent/'data/uav_02.task']):
                for m,b in [('adptive',960),('adaptive',1)]:
                    p=subprocess.run(list(map(str,prefix+[m,4201,b,Path(t)/'bad.json'])),capture_output=True)
                    self.assertNotEqual(p.returncode,0)
    def test_portal_contract(self):
        with tempfile.TemporaryDirectory(dir=R/'tmp') as t:
            lines=(R.parent/'data/uav_02.task').read_text().splitlines();lines[2]='11';del lines[14]
            p=Path(t)/'bad.task';p.write_text('\n'.join(lines))
            z=subprocess.run(list(map(str,[R/'bench/shared.exe','uav',p,'adaptive',4201,24,Path(t)/'bad.json'])),capture_output=True)
            self.assertNotEqual(z.returncode,0);self.assertIn(b'L/R/B/T',z.stderr)
    def test_cache_identity(self):
        with tempfile.TemporaryDirectory(dir=R/'tmp') as t:
            d=Path(t);task=d/'uav_02.task';task.write_bytes((R.parent/'data/uav_02.task').read_bytes());out=d/'r.json'
            args=('uav_02','adaptive',4201,24,task,out);execute(*args)
            execute(*args,resume=True)
            with self.assertRaises(RuntimeError):execute(*args)
            task.write_text(task.read_text()+'\n')
            with self.assertRaises(RuntimeError):execute(*args,resume=True)
            execute(*args,force=True);Path(str(out)+'.csv').write_text('damaged')
            with self.assertRaises(RuntimeError):execute(*args,resume=True)
if __name__=='__main__':unittest.main()
