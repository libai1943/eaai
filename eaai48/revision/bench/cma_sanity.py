"""Functional sanity check against pycma. Not bitwise equivalence or a timing comparison."""
import sys,json,subprocess
import numpy as np
from run import R
sys.path.insert(0,str(R/'tmp/cma_check'))
import cma
rows=[]
for n in [7,9,13]:
 for seed in [101,211,307,401]:
    budget=12000
    def f(x):
        a=np.asarray(x)-.37;a=a-2*a.sum()/n
        return float(np.sum(np.power(1000.,np.arange(n)/(n-1))*a*a))
    native=float(subprocess.check_output([str(R/'tmp/cma_sanity.exe'),str(n),str(seed),str(budget)],text=True))
    es=cma.CMAEvolutionStrategy([.5]*n,.24,{'popsize':24,'CMA_mu':12,'CMA_active':False,'bounds':[0,1],'seed':seed,'verbose':-9,'verb_log':0})
    while es.countevals<budget and not es.stop():
        x=es.ask();es.tell(x,[f(v) for v in x])
    rows.append(dict(dimension=n,seed=seed,native_best=native,pycma_best=float(es.best.f),pycma_evaluations=es.countevals,budget=budget))
    assert native<1e-8 and es.best.f<1e-8
record=dict(version=cma.__version__,objective='Householder-rotated positive quadratic; condition number 1000; optimum x=0.37.',scope='Functional convergence check only. Initialization, boundary handling and stopping conventions differ; this does not certify equivalence of constrained planning runs.',rows=rows)
(R/'audit/cma_sanity.json').write_text(json.dumps(record,indent=2));print('12 functional convergence checks passed against pycma',cma.__version__)
