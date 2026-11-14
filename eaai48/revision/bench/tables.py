import csv,json,statistics,collections,math
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/"output";P=R/"paper"
def read(name):return list(csv.DictReader((O/name).open()))
def dump(name,rows):
    with (O/name).open("w",newline="") as f:
        w=csv.DictWriter(f,rows[0]);w.writeheader();w.writerows(rows)
def tbl(caption,header,rows,spec):
    return "\\begin{table}[htbp]\\centering\\small\\caption{"+caption+"}\\begin{tabular}{"+spec+"}\\toprule\n"+" & ".join(header)+r"\\\midrule"+"\n"+"\n".join(" & ".join(map(str,row))+r"\\" for row in rows)+"\n\\bottomrule\\end{tabular}\\end{table}\n"
def main():
    ledger=read("verified.csv");groups=["parking","uav","arm","trailer"];base=[x for x in ledger if x["method"]=="adaptive"];labels={"adaptive":"RegionCovOpt","pso":"Particle swarm","cma":"Full-covariance CMA-ES","cem":"Gaussian cross-entropy","de":"Differential evolution","bfgs":"FD--BFGS","poll":"Coordinate polling","random":"Uniform sampling","proposed":"Poll/difference precursor","region_equal":"Equal batch allocation","region_plain":"Gaussian proposals only","rc_no_refresh":"Remove reserved refresh","rc_no_poll":"Remove archive poll","rc_diagonal":"Diagonal covariance"}
    index={(r["case"],r["seed"],r["method"]):r for r in ledger}
    comparisons=[]
    for m,label in labels.items():
        for g in ["all",*groups]:
            pairs=[(a,index[a["case"],a["seed"],m]) for a in base if g=="all" or a["family"]==g]
            joint=[(x,y) for x,y in pairs if x["valid"]==y["valid"]=="1"];ds=[100*(float(x["cost"])/float(y["cost"])-1) for x,y in joint]
            wins=sum(x["valid"]>y["valid"] or (x["valid"]==y["valid"]=="1" and float(x["cost"])<float(y["cost"])-1e-8) for x,y in pairs)
            losses=sum(x["valid"]<y["valid"] or (x["valid"]==y["valid"]=="1" and float(x["cost"])>float(y["cost"])+1e-8) for x,y in pairs)
            comparisons.append(dict(method=m,family=g,valid=sum(int(y["valid"]) for x,y in pairs),joint=len(joint),median=statistics.median(ds),wins=wins,losses=losses,ties=len(pairs)-wins-losses))
    dump("comparisons.csv",comparisons);D={(x["method"],x["family"]):x for x in comparisons}
    base_methods=["adaptive","pso","cma","de","cem","bfgs","poll","random","proposed"];abl=["region_equal","rc_diagonal","rc_no_poll","rc_no_refresh","region_plain"]
    sn=lambda x:f"{x:+.2f}"
    text=tbl("Independently accepted runs. Each family contributes twelve scenes and three seeds.",["Method","Car","Aerial","Arm","Trailer","Total"],[[labels[m],*[D[m,g]["valid"] for g in groups],D[m,"all"]["valid"]] for m in base_methods],"lrrrrr")
    text+=tbl("Paired primary costs relative to each control. Negative percentages favor RegionCovOpt. A successful motion outranks a failure in the win count.",["Control","Joint pairs","Median (\\%)","Wins","Losses","Ties"],[[labels[m],(r:=D[m,"all"])["joint"],sn(r["median"]),r["wins"],r["losses"],r["ties"]] for m in base_methods[1:]],"lrrrrr")
    text+=tbl("Median paired cost change (percent) within each family; jointly feasible pairs only.",["Control","Car","Aerial","Arm","Trailer"],[[labels[m],*[sn(D[m,g]["median"]) for g in groups]] for m in ["pso","cma","de","bfgs"]],"lrrrr")
    (P/"controls.tex").write_text(text,encoding="utf8")
    (P/"ablation.tex").write_text(tbl("Component ablations. All rows compare the full method against a single change, except the last row which removes the entire special-proposal group.",["Variant","Accepted","Joint pairs","Median (\\%)","Wins","Losses"],[[labels[m],(r:=D[m,"all"])["valid"],r["joint"],sn(r["median"]),r["wins"],r["losses"]] for m in abl],"lrrrrr"),encoding="utf8")
    time=read("timing.csv");tim=lambda m,g:min(float(r["cpu"]) for r in time if r["method"]==m and r["family"]==g)
    (P/"times.tex").write_text(tbl("Minimum process CPU seconds on scene 02 of each family. Each setting was repeated three times on one logical processor.",["Method","Car","Aerial","Arm","Trailer"],[[labels[m],*[f"{tim(m,g):.2f}" for g in groups]] for m in base_methods[:-1]],"lrrrr"),encoding="utf8")
    rig=[x for x in base if x["family"]=="trailer" and x["valid"]=="1"];park=[x for x in base if x["family"]=="parking" and x["valid"]=="1"]
    s4201=[r for r in base if r["seed"]=="4201" and r["valid"]=="1"]
    metrics=dict(admitted=D["adaptive","all"]["valid"],park=len(park),docks=len(rig),pairedCMA=D["cma","all"],pairedPSO=D["pso","all"],armCMA=D["cma","arm"],armPSO=D["pso","arm"],minDockGap=min(float(x["clearance"]) for x in rig),maxDockEnd=max(float(x["terminal"]) for x in rig),newSeed=len(s4201),failures=[(x["case"],x["seed"]) for x in base if x["valid"]=="0"])
    (O/"metrics.json").write_text(json.dumps(metrics,indent=2))
    (P/"numbers.tex").write_text(r"\newcommand{\MeasuredAbstract}{"+f"In 144 scene--seed pairs the method delivered {metrics['admitted']} independently accepted motions, including {len(rig)}/36 forward--reverse articulated maneuvers. Its median cost was {abs(D['cma','all']['median']):.2f}\\% lower than global covariance adaptation over {D['cma','all']['joint']} jointly feasible pairs."+"}\n")
    print(metrics)
    with (P/"numbers.tex").open("a") as f:
        f.write(f"\\newcommand{{\\CarCPU}}{{{tim('adaptive','parking'):.2f}}}\n\\newcommand{{\\DockCPU}}{{{tim('adaptive','trailer'):.2f}}}\n")
if __name__=="__main__":main()

