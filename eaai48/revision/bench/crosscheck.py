"""Recalculate one complete record per family, method and seed from the isolated sources."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import itertools,subprocess,json
from run import R,METHODS,SEEDS
def check(item):
    g,m,s=item;case=f"{g}_02";tmp=R/"tmp"/"rebuilt";tmp.mkdir(exist_ok=True,parents=True)
    out=tmp/f"{case}_{m}_{s}.json";ref=R/"runs"/out.name
    cmd=([R/"bench/dock.exe",R/"data"/(case+".task")] if g=="trailer" else [R/"bench/shared.exe",g,R.parent/"data"/(case+".task")])
    subprocess.run(list(map(str,cmd+[m,str(s),"6000" if g=="parking" else "960",out])),check=True)
    a,b=json.loads(out.read_text()),json.loads(ref.read_text())
    if a["z"]!=b["z"] or a["x"]!=b["x"] or Path(str(out)+".csv").read_bytes()!=Path(str(ref)+".csv").read_bytes():raise ValueError(out)
def main():
    jobs=list(itertools.product(["arm","uav","parking","trailer"],METHODS,SEEDS))
    with ThreadPoolExecutor(12) as pool:list(pool.map(check,jobs))
    print(len(jobs),"full output vectors and evaluation traces reproduced")
if __name__=="__main__":main()

