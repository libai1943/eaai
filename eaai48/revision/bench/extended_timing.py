"""Serial planning, independent acceptance and total delivery wall times, one CPU affinity."""
import csv,ctypes,ctypes.wintypes as w,itertools,json,random,subprocess,time
from run import R
from review_panel import A,accept
def main():
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=ctypes.c_void_p
    k.GetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)];k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t];k.GetProcessTimes.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(w.FILETIME)]*4
    a=ctypes.c_size_t();b=ctypes.c_size_t();handle=k.GetCurrentProcess();assert k.GetProcessAffinityMask(handle,ctypes.byref(a),ctypes.byref(b));assert k.SetProcessAffinityMask(handle,a.value&-a.value)
    jobs=list(itertools.product(['parking','uav','arm','trailer'],[2,5,9],['adaptive','cma_matched','cma_regions_adaptive','rc_simple'],range(3)));random.Random(2481).shuffle(jobs);rows=[];d=A/'timing';d.mkdir(exist_ok=True)
    for i,(g,j,m,rep) in enumerate(jobs):
        case=f'{g}_{j:02}';data=(R if g=='trailer' else R.parent)/'data';out=d/'timed.json';cfg=json.loads((data/(case+'.json')).read_text());cfg['kind']=g
        cmd=([R/'bench/dock.exe',data/(case+'.task')] if g=='trailer' else [R/'bench/shared.exe',g,data/(case+'.task')])+[m,4201,6000 if g=='parking' else 960,out]
        t=time.perf_counter();p=subprocess.Popen(list(map(str,cmd)));assert p.wait()==0;planned=time.perf_counter()-t
        ts=[w.FILETIME() for _ in range(4)];assert k.GetProcessTimes(p._handle,*map(ctypes.byref,ts));cpu=sum((z.dwHighDateTime<<32)+z.dwLowDateTime for z in ts[2:])/1e7
        t=time.perf_counter();rec=json.loads(out.read_text());a=accept(cfg,rec);verified=time.perf_counter()-t
        rows.append(dict(case=case,family=g,method=m,repeat=rep+1,planner_cpu=cpu,planner_wall=planned,validation_wall=verified,total_wall=planned+verified,accepted=int(bool(a['ok'])),cost=a.get('J')))
        if (i+1)%12==0:print('timing',i+1,'/',len(jobs),flush=True)
    with (A/'timing.csv').open('w',newline='') as f:z=csv.DictWriter(f,rows[0]);z.writeheader();z.writerows(rows)
    out.unlink();Path(str(out)+'.csv').unlink()
from pathlib import Path
if __name__=='__main__':main()
