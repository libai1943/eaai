"""Extract and independently replay one packaged final result for each model."""
from pathlib import Path
from zipfile import ZipFile
import argparse,json,hashlib,subprocess,sys
R=Path(__file__).resolve().parents[1]
def main():
    cli=argparse.ArgumentParser();cli.add_argument("directory",type=Path);a=cli.parse_args();dest=a.directory.resolve();dest.mkdir(parents=True,exist_ok=False)
    with ZipFile(R/"output/RegionCovOpt_reproducible.zip") as z:
        records=json.loads(z.read("Research/SHA256.json"))
        if len(records)+1!=len(z.namelist()):raise ValueError("archive count")
        for k,d in records.items():
            if hashlib.sha256(z.read("Research/"+k)).hexdigest()!=d:raise ValueError(k)
        if z.read("Research/eaai48/revision/output/pdf/RegionCovOpt_EAAI.pdf")!=(R/"output/pdf/RegionCovOpt_EAAI.pdf").read_bytes():raise ValueError("stale PDF")
        z.extractall(dest)
    root=dest/"Research/eaai48/revision"
    for case in ("parking_02","arm_09","uav_03","trailer_04"):
        g=case.split("_")[0];file=dest/(case+".json")
        cmd=([root/"bench/dock.exe",root/"data"/(case+".task")] if g=="trailer" else [root/"bench/shared.exe",g,root.parent/"data"/(case+".task")])
        subprocess.run(list(map(str,cmd+["adaptive","4201","6000" if g=="parking" else "960",file])),check=True)
        subprocess.run([sys.executable,str(root/"bench/check_one.py"),str(file),case,"adaptive","4201"],check=True)
    print(len(records),"hashes, four models independently reproduced")
if __name__=="__main__":main()

