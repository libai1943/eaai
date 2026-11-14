import argparse,json
from pathlib import Path
from verify import R,car,spatial_many,dock_many
def main():
    p=argparse.ArgumentParser();p.add_argument("file",type=Path);p.add_argument("case");p.add_argument("method");p.add_argument("seed",type=int);a=p.parse_args()
    ref=R/"runs"/f"{a.case}_{a.method}_{a.seed}.json";r=json.loads(ref.read_text());q=json.loads(a.file.read_text())
    for k in ("method","x","z","evaluations","first","loss","J"):
        if q[k]!=r[k]:raise ValueError(f"Different {k}")
    if Path(str(ref)+".csv").read_bytes()!=Path(str(a.file)+".csv").read_bytes():raise ValueError("Trace differs")
    kind=a.case.split("_")[0]
    if q["first"]:
        cfg=json.loads(((R if kind=="trailer" else R.parent)/"data"/(a.case+".json")).read_text())
        if kind=="trailer":out=dock_many(cfg,[q])[0][0]
        elif kind=="parking":out=car(cfg,q["z"])[0]
        else:out=spatial_many(cfg,[q])[0];out=out[0] if isinstance(out,list) else out
        if not out["ok"]:raise ValueError("Replay rejected")
        print(out)
    print(q["evaluations"],"matched evaluations")
if __name__=="__main__":main()

