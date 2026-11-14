"""Self-contained source and evidence bundle, excluding reading copies of the author's papers."""
import hashlib,json
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
R=Path(__file__).resolve().parents[1];WORK=R.parents[1];OUT=R/"output"
def main():
    files={}
    def add(p,key=None):
        if not p.is_file():raise FileNotFoundError(p)
        files[key or p.relative_to(WORK).as_posix()]=p
    for root in ["bench","data","src","paper","figures","runs","shooting","timing","audit","output"]:
        for p in (R/root).rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix not in (".zip",".tmp",".pyc",".pending"):add(p)
    add(R/"README.md")
    for g in ["parking","uav","arm"]:
        for i in range(1,13):
            for ext in ["json","task"]:add(R.parent/"data"/f"{g}_{i:02}.{ext}")
    for p in (WORK/"population_motion_research_20261106/third_party/eigen3").rglob("*"):
        if p.is_file():add(p)
    for p in (WORK/"population_motion_research_20261106/metaheuristic_study/licenses").rglob("*"):
        if p.is_file():add(p)
    public=WORK/"parking_benchmark/upstream/CommonParking"
    for p in (public/"cases").glob("*"):
        if p.is_file():add(p)
    add(public/"LICENSE")
    template=R.parent/"tmp/cas.zip";fallback=WORK/"licenses/CAS.zip"
    add(template if template.is_file() else fallback,"licenses/CAS.zip")
    target=OUT/"RegionCovOpt_reproducible.zip";partial=target.with_suffix(".tmp")
    manifest={}
    with ZipFile(partial,"w",ZIP_DEFLATED,compresslevel=5) as arc:
        for n,p in sorted(files.items()):
            b=p.read_bytes();manifest[n]=hashlib.sha256(b).hexdigest();arc.writestr("Research/"+n,b)
        arc.writestr("Research/SHA256.json",json.dumps(manifest,indent=2))
    with ZipFile(partial) as arc:
        if arc.testzip():raise ValueError("Bad archive CRC")
    partial.replace(target);print(len(manifest),target.stat().st_size)
if __name__=="__main__":main()

