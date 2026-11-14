"""Verify and unpack the published evidence and dependency archives."""
import hashlib,json,shutil
from pathlib import Path
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parent
manifest=json.loads((ROOT/'release_manifest.json').read_text())
for name,info in manifest.items():
    p=ROOT/name
    if hashlib.sha256(p.read_bytes()).hexdigest()!=info['sha256']:raise ValueError(f'Hash mismatch: {name}')
    if p.suffix!='.zip':continue
    with ZipFile(p) as z:
        for member in z.infolist():
            target=(ROOT/member.filename).resolve()
            if ROOT!=target and ROOT not in target.parents:raise ValueError('Unsafe archive path')
        z.extractall(ROOT)
    print('Verified and extracted',name)
revision=ROOT/'eaai48/revision'
(revision/'tmp').mkdir(parents=True,exist_ok=True)
(revision/'output/pdf').mkdir(parents=True,exist_ok=True)
for pdf in (ROOT/'paper').glob('RegionCovOpt*.pdf'):
    shutil.copyfile(pdf,revision/'output/pdf'/pdf.name)
