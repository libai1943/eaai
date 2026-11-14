"""Verify empirical counts, publication metadata, layout and figure geometry."""
from pathlib import Path
import csv,json,re
import numpy as np
from PIL import Image
import pdfplumber
from pypdf import PdfReader
R=Path(__file__).resolve().parents[1]
def main():
    p=R/"paper";pdf=PdfReader(R/"output/pdf/RegionCovOpt_EAAI.pdf")
    text="\n".join(pg.extract_text() for pg in pdf.pages)
    assert pdf.metadata.author=="Bai Li" and "Shanghai 200241, China" in text
    assert "Research manuscript" in pdf.pages[0].extract_text() and "s.t." in re.sub(r"\s+","",text)
    assert "Appendix A. Regional update constants" in text and "Appendix B. Convergence of the best admissible cost" in text
    assert not any(t in text for t in ("Graphical Abstract","Declaration of generative AI","??"))
    src="\n".join((p/f).read_text(encoding="utf8") for f in ("manuscript.tex","method.tex","experiments.tex","audit_results.tex","audit_timing.tex","appendix.tex"))
    c={k for s in re.findall(r"\\cite\{([^{}]+)\}",src) for k in s.split(",")}
    b=(p/"references.tex").read_text(encoding="utf8")
    assert c==set(re.findall(r"\\bibitem\{([^{}]+)\}",b)) and len(c)>=45 and len(set(re.findall(r'https://doi.org/([^}]+)',b)))==len(c)
    titles=re.findall(r"\\section\{([^{}]+)\}",src);assert titles[:6]==["Introduction","Related Works","Problem formulation","Methodology","Experiments and discussion","Conclusion"]
    labels=re.findall(r"\\(?:Eq|ProbRow)\{([^{}]+)\}",src)
    assert not re.search(r"\\cite\{[^}]*,",src), "Grouped reference"
    assert src.count(r"\ProbRow{")==5
    assert re.search(r"\\section\{Related Works\}\s+[A-Za-z].+?\\subsection",src,re.S)
    alg=src.split(r"\begin{algorithm}",1)[1].split(r"\end{algorithm}",1)[0]
    assert alg.count(r"\For{")==2 and r"\SetAlgoVlined" in src
    assert not re.search(r"(?<![A-Za-z\\])\d+(?![A-Za-z])",re.sub(r"N_0|Section~4\.2","",alg)), "Unexplained numeric literal in Algorithm 1"
    boxes=pdfplumber.open(R/"output/pdf/RegionCovOpt_EAAI.pdf")
    tags={}
    for page in boxes.pages:
        # Isolate the number columns so neighboring body text cannot merge into a tag.
        words=[]
        for right in (288.64,557.69):
            words.extend(page.crop((right-21,0,right+1,page.height)).extract_words(x_tolerance=1))
        for w in words:
            m=re.fullmatch(r"\((\d+)\)",w["text"])
            if not m or min(abs(w["x1"]-x) for x in (288.64,557.69))>1:continue
            # Only the separately typeset right-margin equation tags are counted.
            tags[int(m[1])]=round(w["x1"],3)
        # The representative plate composes clipped MATLAB pages. PDF text extraction
        # also sees invisible source-panel glyphs outside those clipping rectangles.
        assert not any((ch["x0"]<-.2 or ch["x1"]>page.width+.2)
                       and 'TimesNewRoman' not in ch['fontname'] for ch in page.chars)
    assert set(tags)==set(range(1,len(labels)+1)),(len(tags),len(labels))
    plots=["parking","uav","arm","trailer"];media=[tuple(PdfReader(R/"figures"/(g+".pdf")).pages[0].mediabox) for g in plots]
    assert len(set(media))==1
    sizes=[Image.open(R/"figures"/(g+".png")).size for g in plots];assert len(set(sizes))==1
    rows=list(csv.DictReader((R/"output/verified.csv").open()));assert len(rows)==2016 and all(r["valid"]==r["accepted"] for r in rows)
    gallery=json.loads((R/"figures/data.json").read_text());assert len(gallery)==48
    geometric_checks = 0
    for item in gallery:
        family = item["kind"]
        if family not in ("parking", "trailer"):
            continue
        for track in item["tracks"]:
            case = item["name"]
            run = json.loads((R/"runs"/f"{case}_{track['method']}_4201.json").read_text())
            poses = np.asarray(track["poses"])
            directions = np.asarray(track["direction"])
            strokes = np.asarray(run["z"]).reshape(-1, 2 if family=="parking" else 5)
            gears = strokes[:, -1]
            gears = np.sign(gears[np.abs(gears)>=1.e-9])
            changes = np.flatnonzero(np.diff(directions)) + 1
            assert directions.shape == (len(poses)-1,) and np.isin(directions, [-1,1]).all(), case
            assert np.array_equal(directions[np.r_[0, changes]], gears[np.r_[True, np.diff(gears)!=0]]), case
            np.testing.assert_allclose(poses[changes,:2], np.asarray(track["switches"]).reshape(-1,2), atol=1.e-8, rtol=0)
            # Independently compare each drawn interval with its displacement along the body axis.
            yaw = (poses[:-1,2]+poses[1:,2])/2
            signed = (np.diff(poses[:,:2],axis=0)*np.column_stack([np.cos(yaw),np.sin(yaw)])).sum(axis=1)
            assert np.all(signed*directions>=-1.e-10), case
            geometric_checks += 1
    atlas=PdfReader(R/"output/pdf/RegionCovOpt_profiles.pdf")
    profile_index=json.loads((R/"figures/profiles/index.json").read_text())
    assert len(atlas.pages)==24 and len(profile_index)==48
    for row in profile_index:
        case=row["case"]
        candidates=[r for r in rows if r["case"]==case and r["method"]=="adaptive" and r["valid"]=="1"]
        selected=min(candidates,key=lambda r:(float(r["cost"]),int(r["seed"])))
        assert int(selected["seed"])==row["seed"] and abs(float(selected["cost"])-row["cost"])<1.e-6
        assert (R/"figures/profiles"/(case+".csv")).is_file()
    assert r"u(\cdot),\,z(\cdot),\,T>0" in src
    assert "Scheme" not in text and "SHA-256" not in text
    assert re.findall(r"Fig\.\s*(\d+)\.",text)==list("12345")
    chart = PdfReader(R/"figures/attribution.pdf").pages[0].extract_text().replace("\u2212", "-")
    compact = re.sub(r"\s+", "", chart)
    stats = list(csv.DictReader((R/"audit/comparisons.csv").open()))
    global_row = next(r for r in stats if r["split"]=="matched" and r["method"]=="cma_matched")
    regional_row = next(r for r in stats if r["split"]=="holdout" and r["method"]=="cma_regions_adaptive")
    for key in ("parking","uav","arm","trailer"):
        assert format(float(global_row[key]), "+.4f" if key=="parking" else "+.2f") in compact
    for key in ("median","ci_low","ci_high"):
        assert format(float(regional_row[key]), "+.3f") in compact
    records=json.loads((p/"references.json").read_text(encoding="utf8"))
    assert set(records)==c and len(records)==56
    assert not any(a.get("family")=="Li" and a.get("given")=="Bai" for r in records.values() for a in r["author"])
    assert any("CharisSIL" in ch["fontname"] for ch in boxes.pages[1].chars)
    assert any(ch.get("non_stroking_color") and isinstance(ch["non_stroking_color"],(tuple,list)) and len(ch["non_stroking_color"])==3 and all(abs(a-v)<.003 for a,v in zip(ch["non_stroking_color"],(0,.502,.675))) for ch in boxes.pages[1].chars)
    assert all(k in src for k in ("profile_ground.pdf","profile_spatial.pdf"))
    data=dict(profile_cases=len(profile_index),profile_atlas_pages=len(atlas.pages),pages=len(pdf.pages),author=pdf.metadata.author,cited_published_works=len(c),sections=titles[:6],right_aligned_equation_tags=len(tags),figure_size_pt=list(map(float,media[0])),verified_runs=len(rows),plate_png_size=sizes[0])
    data.update(direction_checked_tracks=geometric_checks, figure_count=5, attribution_values_checked=7)
    (R/"output/preflight.json").write_text(json.dumps(data,indent=2));print(data)
if __name__=="__main__":main()

