# RegionCovOpt · EAAI working manuscript and reproduction package

The paper is in output/pdf/RegionCovOpt_EAAI.pdf. The six sections are Introduction, Related Works, Problem formulation, Methodology, Experiments and discussion, and Conclusion. Appendix A states the learning rates; Appendix B proves the conditional archive-cost convergence theorem. Algorithm 1 and Fig. 1 are in Section 4. The title is RegionCovOpt: A Metaheuristic Optimizer for Endpoint-Conditioned Robotic Motion Planning.

## Reproduce a motion

From the Research directory of the extracted archive, run in PowerShell:

~~~powershell
New-Item -ItemType Directory -Force check | Out-Null
.\eaai48\revision\bench\dock.exe .\eaai48\revision\data\trailer_04.task adaptive 4201 960 .\check\T04.json
python eaai48/revision/bench/check_one.py check/T04.json trailer_04 adaptive 4201
~~~

The docking planner takes the map, search rule, RNG seed, full evaluation budget and output path. The other families use bench/shared.exe with the family name before the map argument. Inputs for the unchanged families reside in eaai48/data and contain endpoint/model/geometry data. The executable accepts no upstream path. Docking returns signed strokes and durations, ordered in execution order. T04, T08 and T11 require reverse withdrawal, forward staging and reverse docking; the other nine require forward staging and reverse docking. Each articulated vehicle consists of an oriented tractor rectangle and a separately oriented trailer rectangle. All planar collision and display tests in this release use the declared polygons.

## Experiments

- 48 scenes × 3 seeds × 14 settings give 2,016 runs under runs/. Each JSON has an associated evaluation CSV. The preserved seeds are 4201, 5209 and 6203. The first 24 evaluations count toward the car budget of 6,000 and other family budget of 960. Accepted and failed runs are retained. The layout choices were visible during development.
- The 14 settings consist of RegionCovOpt (CLI key adaptive), seven controls, the poll/difference precursor and five RegionCovOpt ablations. region_equal retains equal work and alternating reserved refreshes in eight-batch cycles; rc_diagonal suppresses cross-coordinate covariance; rc_no_poll and rc_no_refresh remove individual special proposals; region_plain removes all special proposals. Complete rows and paired definitions are in output/verified.csv and output/comparisons.csv.
- Independent replay reconstructs each accepted stroke from the specified start and checks the actual controls, both headings, final state and geometry. Docking uses 400 RK4 steps per stroke and explicit gear-sequence verification. The raw output returns the least violating candidate if the archive contains no admissible motion. A separate 96-run control-knot experiment is in shooting/. Single-core, interleaved CPU and wall timings are supplied in timing/ and output/timing.csv.
- Only search-coordinate region membership is used; it is not presumed to identify a homotopy class. The proof concerns an infinite idealized independent-refresh process and the infimum in the represented feasible families. The off-axle vehicle benchmark verifies sampled clearance by dense open-loop replay. It is not a closed-loop deployment or an interval-arithmetic safety certificate.

## Build and verify

The included executables are for Windows x64. They can be rebuilt from the provided source using bench/build.ps1 -Compiler 'C:/path/to/g++.exe'. Eigen is used for matrix algebra. Python with NumPy supports numerical validation; regenerating the public parking inputs from MAT files requires SciPy. MATLAB R2021b produced the figures; The LaTeX source uses the Elsevier CAS base with a publication-style two-column grid, Charis SIL text, STIX math and the first-page journal masthead. The fonts and their SIL Open Font License are included under paper/fonts. The photographic appearance of a plot is not used as evidence for numerical feasibility.

1. bench/scenes.py regenerates the twelve rectangular docking maps. bench/run.py runs the statistical panel. Use --force to recompute or --resume to reuse only records whose source, binary, inputs, configuration and complete traces match. Historical unversioned results are never silently adopted.
2. bench/verify.py verifies the entire panel, and writes the scene gallery input, verified rows and count checks. bench/encoding.py and bench/timing.py reproduce the two separate experiments. bench/tables.py emits the paper's aggregate tables. The MATLAB entry plots in the bench folder produces the four vector scene plates. Run bench/representative.py to assemble the twelve selected panels. In both vehicle rows, the sign of each recorded stroke sets the line style and the two adjacent legs share the exact switch pose. MATLAB attribution_plot reads audit/comparisons.csv and exports the paired-cost panel for the main text. All four PDF plates have the same media box and every planar panel has equal x and y scale.
3. bench/scheme.py generates the vector algorithm diagram. The source manuscript is paper/manuscript.tex. The publisher metadata for the 56 cited publications is in paper/references.json. All 56 have a DOI. Bench/bibliography.py regenerates the bibliography from those records.
4. bench/profiles.py reconstructs all controls, states and free terminal times for the lowest-cost independently accepted RegionCovOpt seed in each scene. The CSV files and the selection ledger are in figures/profiles. Run MATLAB profile_plots from the bench folder, then bench/profile_book.py, to regenerate the two manuscript profile figures and the separate 24-page atlas output/pdf/RegionCovOpt_profiles.pdf. Repeated timestamps preserve the left and right limits of controls at switches.
5. The ZIP has a SHA256 manifest. It includes the formal records, results tables, source and PDFs. Private USB papers used to check the author's exposition are not part of the archive.


## Revision following independent review

The public repository is https://github.com/libai1943/eaai. The audit directory contains 300 validation, 896 held-out perturbation, and 720 matched-control runs, along with separate timing and clustered statistics. The main paper uses one twelve-panel scene plate; the complete plates and profile atlas remain supplementary. See the public root README for the attribution findings and representation scope.
