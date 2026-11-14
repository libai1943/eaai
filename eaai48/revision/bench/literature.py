"""Build bibliographic records from Crossref's published-work metadata. Reject weak matches."""
from pathlib import Path
import json,re,time,concurrent.futures,urllib.parse,urllib.request,difflib,unicodedata
HERE=Path(__file__).resolve().parents[1]
LIST="""rrt|Sampling-based algorithms for optimal motion planning
prm|Probabilistic roadmaps for path planning in high-dimensional configuration spaces
connect|RRT-Connect: An efficient approach to single-query path planning
sst|Asymptotically optimal sampling-based kinodynamic planning
fmt|Fast marching tree: A fast marching sampling-based method for optimal motion planning in many dimensions
bit|Batch informed trees (BIT*): Informed asymptotically optimal anytime search
informed|Informed RRT*: Optimal sampling-based path planning focused via direct sampling of an admissible ellipsoidal heuristic
bench|Benchmarking motion planning algorithms: An extensible infrastructure for analysis and visualization
ompl|The Open Motion Planning Library
kpiece|Kinodynamic motion planning by interior-exterior cell exploration
chomp|CHOMP: Covariant Hamiltonian optimization for motion planning
trajopt|Motion planning with sequential convex optimization and convex collision checking
stomp|STOMP: Stochastic trajectory optimization for motion planning
gpmp|Continuous-time Gaussian process motion planning via probabilistic inference
obca|Optimization-based collision avoidance
rosmann|Integrated online trajectory planning and optimization in distinctive topologies
kelly|An introduction to trajectory optimization: How to do your own direct collocation
betts|Survey of numerical methods for trajectory optimization
gusto|GuSTO: Guaranteed sequential trajectory optimization via sequential convex programming
scp|Successive convexification for real-time 6-DoF powered descent guidance with state-triggered constraints
cfs|The convex feasible set algorithm for real time optimization in motion planning
ipopt|On the implementation of an interior-point filter line-search algorithm for large-scale nonlinear programming
pso|Particle swarm optimization
de|Differential evolution: A simple and efficient heuristic for global optimization over continuous spaces
cem|A tutorial on the cross-entropy method
cma|Completely derandomized self-adaptation in evolution strategies
cma2|Reducing the time complexity of the derandomized evolution strategy with covariance matrix adaptation
cma3|Principled design of continuous stochastic search: From theory to practice
niching|Niching methods for multimodal function optimization
quality|Quality diversity: A new frontier for evolutionary computation
cmame|Covariance matrix adaptation for the rapid illumination of behavior space
cvt|Using centroidal Voronoi tessellations to scale up the multidimensional archive of phenotypic elites algorithm
solis|Minimization by random search techniques
global|Convergence rates of the pure random search method
deb|An efficient constraint handling method for genetic algorithms
runar|Stochastic ranking for constrained evolutionary optimization
sample|A comprehensive survey on evolutionary computation approaches to constraint handling
mpnet|Motion planning networks
diffusion|Motion planning diffusion: Learning and adapting robot motion planning with diffusion models
reeds|Optimal paths for a car that goes both forwards and backwards
dubins|On curves of minimal length with a constraint on average curvature, and with prescribed initial and terminal positions and tangents
tractor|A path planning and path-following control framework for a general 2-trailer with a car-like tractor
abc|A balance-evolution artificial bee colony algorithm for protein structure optimization based on a three-dimensional AB off-lattice model
liom|A lightweight iterative optimization method for time-optimal motion planning of tractor-trailer vehicles
eaai1|Learning from experience for rapid generation of local car maneuvers
eaai2|Visually-guided motion planning for autonomous driving from interactive demonstrations
eaai3|Path planning via reinforcement learning with closed-loop motion control and field tests
eaai4|Integration of multiple constraint-treating approaches for uncertain automatic parking path optimization utilizing competition and cooperation-driven differential evolution
kino|Kinodynamic motion planning
kino2|Randomized kinodynamic planning
elastic|Elastic bands: Connecting path planning and control
inference|Motion planning as probabilistic inference using Gaussian processes
direct|Direct trajectory optimization using nonlinear programming and collocation
mesh|Mesh adaptive direct search algorithms for constrained optimization
comp|Generalized pattern searches for linearly constrained minimization
basin|A scalable stochastic global optimization algorithm for global optimization of smooth functions
rigid|A fast procedure for computing the distance between complex objects in three-dimensional space
gk|A fast and robust GJK implementation for collision detection of convex objects
time|Time-optimal path parameterization for redundantly actuated robots: A numerical integration approach
topp|A new approach to time-optimal path parameterization based on reachability analysis
survey|A survey of motion planning and control techniques for self-driving urban vehicles
uav|Polynomial trajectory planning for aggressive quadrotor flight in dense indoor environments
snap|Minimum snap trajectory generation and control for quadrotors
fast|Robust and efficient quadrotor trajectory generation for fast autonomous flight"""
def norm(t):return re.sub(r"[^a-z0-9]","",unicodedata.normalize("NFKD",t).lower())
def get(row):
 key,title=row.split("|");cache=HERE/"tmp"/("ref_"+key+".json")
 if cache.exists():return key,json.loads(cache.read_text(encoding="utf8"))
 url="https://api.crossref.org/works?"+urllib.parse.urlencode({"query.title":title,"rows":4,"select":"DOI,title,author,container-title,published,type,volume,page,article-number"})
 for attempt in range(3):
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"ResearchBibliography/1.0 (metadata verification)"})
        with urllib.request.urlopen(req,timeout=25) as stream:items=json.load(stream)["message"]["items"]
        options=[x for x in items if x.get("type") in ["journal-article","proceedings-article","book-chapter","monograph","book"] and x.get("title") and x.get("author")]
        best=max(options,key=lambda x:difflib.SequenceMatcher(None,norm(title),norm(x["title"][0])).ratio())
        similarity=difflib.SequenceMatcher(None,norm(title),norm(best["title"][0])).ratio()
        if similarity<.80:return key,None
        cache.write_text(json.dumps(best,ensure_ascii=False),encoding="utf8");return key,best
    except Exception as exc:
        if attempt==2:print(key,str(exc)[:100],flush=True)
        time.sleep(1+attempt)
 return key,None
def main():
 with concurrent.futures.ThreadPoolExecutor(5) as ex:results=dict(ex.map(get,LIST.splitlines()))
 records={k:r for k,r in results.items() if r}
 # Ambiguous short titles require author and venue disambiguation below.
 for k,r in records.items():print(k,r["author"][0].get("family"),str(r.get("published")),r["title"][0],r["DOI"])
 (HERE/"paper/references.json").write_text(json.dumps(records,ensure_ascii=False,indent=1),encoding="utf8")
 print("matched",len(records),"missing",[k for k,r in results.items() if not r])
if __name__=="__main__":main()

