from pathlib import Path
import csv,json,numpy as np
from run import R
A=R/'audit'
rows=list(csv.DictReader((A/'timing.csv').open()));stats={};out=[]
for g in ('parking','uav','arm','trailer'):
    stats[g]={}
    for m in ('adaptive','cma_matched','cma_regions_adaptive','rc_simple'):
        a=[r for r in rows if r['family']==g and r['method']==m]
        q={k:dict(median=float(np.median([float(r[k]) for r in a])),p90=float(np.quantile([float(r[k]) for r in a],.9))) for k in ['planner_cpu','planner_wall','validation_wall','total_wall']}
        q['median_case_best_cpu']=float(np.median([min(float(r['planner_cpu']) for r in a if r['case']==c) for c in set(r['case'] for r in a)]));stats[g][m]=q
        out.append(dict(family=g,method=m,**{k+'_'+z:v[z] for k,v in q.items() if isinstance(v,dict) for z in v},median_case_best_cpu=q['median_case_best_cpu']))
(A/'timing_summary.json').write_text(json.dumps(stats,indent=2))
with (A/'timing_summary.csv').open('w',newline='') as f:w=csv.DictWriter(f,out[0]);w.writeheader();w.writerows(out)
s=[r'\subsection{Planning and independently verified delivery time}',r'The extended timing test uses cases 02, 05 and 09 of each family, four search rules and three interleaved repeats per rule, giving 144 timed runs on one logical processor. Planning time includes process startup, decoding, scoring and all in-process replay. Independent acceptance is measured separately after reading the returned motion, with task data already loaded. Total wall time is their sum. The table gives median and 90th-percentile wall seconds for RegionCovOpt across the nine runs of each robot; the repository gives all controls and each case\textquotesingle s best-of-three process CPU time.',r'\begin{center}\begin{minipage}{\linewidth}\centering\small',r'\TableHere{Planning and independent acceptance wall times in seconds. Each entry is median / 90th percentile.}',r'\begin{tabular}{@{}lrrr@{}}\toprule Robot & Planning & Acceptance & Total\\\midrule']
for g,name in [('parking','Car'),('uav','Flight'),('arm','Arm'),('trailer','Articulated')]:
    q=stats[g]['adaptive'];s.append(name+' & '+' & '.join(f"{q[k]['median']:.3f} / {q[k]['p90']:.3f}" for k in ['planner_wall','validation_wall','total_wall'])+r'\\')
s += [r'\bottomrule\end{tabular}\end{minipage}\end{center}',r'Independent articulated replay is comparatively expensive because the Python verifier integrates every stroke with 400 RK4 steps and checks both bodies. Its cost should be distinguished from the compiled planner\textquotesingle s runtime when assessing a delivered motion. The timings describe open-loop model-based planning and numerical acceptance; hardware execution is a separate validation question.']
(R/'paper/audit_timing.tex').write_text(('\n\n'.join(s)+'\n').replace(r'\textquotesingle ', chr(39)))
print(json.dumps({g:stats[g]['adaptive'] for g in stats},indent=1))
