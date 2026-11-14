from pathlib import Path
import itertools,concurrent.futures,subprocess,json
R=Path(__file__).resolve().parents[1]
def solve(job):
    case,m=job;kind=case.split("_")[0];file=R/"shooting"/f"{case}_{m}_4201.json"
    cmd=([R/"bench/shoot_dock.exe",R/"data"/(case+".task")] if kind=="trailer" else [R/"bench/shoot_shared.exe",kind,R.parent/"data"/(case+".task")])
    subprocess.run(list(map(str,cmd+[m,"4201","6000" if kind=="parking" else "960",file])),check=True)
def main():
    (R/"shooting").mkdir(exist_ok=True)
    jobs=list(itertools.product([f"{g}_{i:02}" for g in ["parking","uav","arm","trailer"] for i in range(1,13)],["adaptive","de"]))
    with concurrent.futures.ThreadPoolExecutor(9) as p:list(p.map(solve,jobs))
    files=list((R/"shooting").glob("*.json"));print(len(files),sum(json.loads(f.read_text())["first"]>0 for f in files),"nodally feasible")
if __name__=="__main__":main()

