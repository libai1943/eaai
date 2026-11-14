"""Interleaved repeats on one logical processor. Verify that timed reruns return the recorded motion."""
import csv,ctypes,ctypes.wintypes as w,json,itertools,random,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
 k=ctypes.WinDLL("kernel32",use_last_error=True);k.GetCurrentProcess.restype=ctypes.c_void_p;k.GetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)]
 k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t];k.GetProcessTimes.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(w.FILETIME)]*4
 a=ctypes.c_size_t();b=ctypes.c_size_t();handle=k.GetCurrentProcess()
 if not k.GetProcessAffinityMask(handle,ctypes.byref(a),ctypes.byref(b)) or not k.SetProcessAffinityMask(handle,a.value&-a.value):raise ctypes.WinError()
 jobs=list(itertools.product(["parking","arm","trailer","uav"],"adaptive cma pso de bfgs poll cem random".split(),range(3)));random.Random(153).shuffle(jobs)
 out=R/"timing";out.mkdir(exist_ok=True);rows=[]
 for g,m,r in jobs:
    case=g+"_02";f=out/f"{case}_{m}_{r}.json"
    cmd=([R/"bench/dock.exe",R/"data"/(case+".task")] if g=="trailer" else [R/"bench/shared.exe",g,R.parent/"data"/(case+".task")])+[m,"4201","6000" if g=="parking" else "960",f]
    t=time.perf_counter();p=subprocess.Popen(list(map(str,cmd)));assert p.wait()==0
    wall=time.perf_counter()-t;ts=[w.FILETIME() for _ in range(4)]
    if not k.GetProcessTimes(p._handle,*map(ctypes.byref,ts)):raise ctypes.WinError()
    cpu=sum((z.dwHighDateTime<<32)+z.dwLowDateTime for z in ts[2:])/1e7;ref=R/"runs"/f"{case}_{m}_4201.json"
    assert json.loads(f.read_text())["z"]==json.loads(ref.read_text())["z"]
    rows.append(dict(family=g,method=m,repeat=r+1,wall=wall,cpu=cpu))
 with (R/"output/timing.csv").open("w",newline="") as f:
    wri=csv.DictWriter(f,rows[0]);wri.writeheader();wri.writerows(rows)
 print(len(rows),"timed repeats")
if __name__=="__main__":main()

