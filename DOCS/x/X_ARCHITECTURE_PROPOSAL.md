# Human3D 2.0 anatomy-first proposal

Keep a content-addressed, native-space canonical anatomy asset. Store evidence and its aggregate profile independently of the target photograph. Use the aggregate to initialize pinned MakeHuman targets. Permit a bounded regional correction only when supported by observations and native structural validation. Rebind after every accepted anatomy change. Use posed views for inspection and pose-space interactions, with edits mapped back through the native controls or a validated inverse. Treat downstream articulation and appearance as consumers of the frozen body.

| Phase | Input | Output |
|---|---|---|
| Observe | Subject-associated image and viewpoint | Sparse projected extents with explicit missingness, uncertainty and provenance |
| Aggregate | Validated observations | Per-axis profile with duplicate handling and conflict state |
| Initialize | Profile, MakeHuman base and target set | Candidate native geometry and reproducible coefficients |
| Refine and rebind | Candidate plus applicable regional evidence | Validated neutral mesh, UV indexing, skin weights and joints |
| Persist | Validated native asset | Content-addressed frozen body |
| Downstream | Frozen body and independent target pose | Posed geometry and appearance bindings |

A-pose is the first posed inspection candidate from P2. Consider X-pose where leg separation contributes useful observations. A production switch should depend on a repeatable improvement against the calibrated M6 baseline for diverse held-out subjects. P4 supplies an engineering feasibility control and an empirical comparison within the synthetic scope.
