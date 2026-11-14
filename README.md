# RegionCovOpt

Research code and complete experimental records for **RegionCovOpt: An Integrated Metaheuristic Optimizer for Generic Robotic Motion Planning**, by **Bai Li**.

This repository accompanies a research manuscript for Engineering Applications of Artificial Intelligence. It is not a statement of acceptance or publication.

## What the implementation does

The C++ optimizer samples complete endpoint-conditioned motions, ranks constraint violation before cost, and maintains a covariance distribution in each parameter region. It requires no externally supplied trajectory. The proposed `adaptive` method uses no objective/constraint gradient, automatic differentiation, AMPL, CasADi, IPOPT, or other optimization solver. Eigen supplies matrix algebra. The `bfgs` control is explicitly a finite-difference baseline; it is not called by the proposed method.

The search engine is shared across four adapters. Their motion families contain task knowledge: bounded-curvature parking connections, ordered flight portals, joint-space motion constructions, and articulated docking stroke sequences. The code does not represent all possible robotic motions. Car and articulated bodies use oriented rectangles throughout collision checking and plotting.

## Manuscript and figures

- [Manuscript](paper/RegionCovOpt_EAAI.pdf)
- [Integrated search workflow (Fig. 1)](figures/scheme.pdf)
- [All 48 state/control profiles](paper/RegionCovOpt_profiles.pdf)
- [Parking plate](figures/parking.pdf), [flight plate](figures/uav.pdf), [arm plate](figures/arm.pdf), [articulated docking plate](figures/trailer.pdf)
- [Twelve representative scenes](figures/representative.pdf) with forward and reverse travel and gear changes
- [Paired cost contribution plot](figures/attribution.pdf) with matched global and adaptive regional CMA controls
- [Paper sources](eaai48/revision/paper)

## Evidence and interpretation

The original panel contains 48 scenes × 3 seeds × 14 settings = 2,016 runs. The revision adds 300 independent validation runs, 896 held-out perturbation runs and 720 matched-control runs. All 3,932 records retain evaluation traces and failed attempts.

On the original panel, the first 24 shared initialization evaluations already find an oracle-feasible motion in 125/144 scene–seed pairs. RegionCovOpt returns 142/144 final independently accepted motions; DE and uniform sampling return 144/144. Feasibility must therefore be attributed substantially to the common motion representation.

Against the parameter-matched global CMA control, median cost reductions are 28.49% for flight and 27.98% for the arm. Against adaptively allocated independent regional CMA, the additional median improvement is only 0.032% overall. On the 128 held-out pairs that difference is 0.035%, with an exploratory scene-clustered 95% interval spanning zero. The experiments support regional search, but do not establish that every extra proposal is necessary.

Five fixed variants were compared on 12 validation tasks with 5 seeds. A prespecified acceptance-first selection rule chose the original method (59/60). The selected method was then frozen and returned 128/128 motions on 16 task perturbations with 8 new seeds. These are unseen geometric instances of the existing template families, not an unseen distribution of arbitrary environment topologies. The baseline layouts were visible during development.

See [comparisons](eaai48/revision/audit/comparisons.csv), [selection record](eaai48/revision/audit/selection.json), [protocol](eaai48/revision/audit/protocol.json), [budget curves](eaai48/revision/audit/budget_curves.csv), and [separate planning/acceptance timings](eaai48/revision/audit/timing_summary.csv). The timing study has 144 interleaved repeats over 12 scenes; planning and independent acceptance are reported separately.

## Build

A C++17 compiler and Eigen 3 are required. The included Eigen archive can be unpacked together with the evidence. No optimization-library installation is needed.

```sh
python unpack.py
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
```

On Windows, the provided build script also works:

```powershell
./eaai48/revision/bench/build.ps1 -Compiler 'C:/path/to/g++.exe'
```

Python verification requires NumPy. SciPy is needed only when regenerating CommonParking inputs from the upstream MAT files. PDF/paper tooling has its own optional dependencies. MATLAB R2021b generated the scientific plots.

## Reproduce and verify

From the repository root after unpacking the archives:

```powershell
New-Item -ItemType Directory -Force check | Out-Null
./eaai48/revision/bench/dock.exe ./eaai48/revision/data/trailer_04.task adaptive 4201 960 ./check/T04.json
python eaai48/revision/bench/check_one.py check/T04.json trailer_04 adaptive 4201
python eaai48/revision/bench/test_contracts.py
python eaai48/revision/bench/verify.py
```

To recompute the original panel, use `python eaai48/revision/bench/run.py --force`. New runs save source, binary, task, configuration and result identities. `--resume` reuses only exact identity matches with complete traces; old unversioned records are never silently reused. Historical records remain intact in the evidence archives. The supplemental run identities refer to the retained `audit/frozen_source` snapshot; a subsequent runner change only adds support for UTF-8 BOM in build metadata.

The follow-up scripts are `review_panel.py`, `matched_panel.py`, `audit_statistics.py` and `extended_timing.py`. The protocol and selection record are already supplied. To regenerate a split from scratch, use a fresh extracted checkout; keep the validation selection separate from held-out evaluation. `cma_sanity.py` optionally uses pycma 4.5.0 for a functional test on rotated quadratics. That dependency is for verification only and is absent from the planner.

The independent verifier checks positive durations, finite values, dimensions, saved-node consistency, physical limits, terminal state and dense collision replay. Dense replay is a numerical check, not a continuous-time safety certificate for every adapter. The convergence statement concerns positive-mass feasible subsets within the represented motion families and does not give an unconditional finite-budget global-optimality guarantee.

## Data and licensing

Parking inputs derive from [CommonParking](https://github.com/libai1943/CommonParking/tree/476ef8573d9e22578be5c3d42514a9a29f27d07a), revision `476ef8573d9e22578be5c3d42514a9a29f27d07a`. Its GPL-3.0 license is retained under `licenses/CommonParking-GPL-3.0.txt`. The other scenarios and all new search implementations are supplied here. Third-party headers and fonts retain their own notices. Author reference papers used to study writing style are not redistributed.

The software written for this project is distributed under the MIT license in `LICENSE`, excluding separately licensed third-party components and CommonParking-derived data. The evidence ZIPs use relative paths and can be extracted by `unpack.py`. `release_manifest.json` lists their content hashes and byte sizes.
