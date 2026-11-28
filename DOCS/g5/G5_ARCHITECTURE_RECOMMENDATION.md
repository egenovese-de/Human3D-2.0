# G5 architecture recommendation

Select **Strategy A** for the next production release. The experimental branch retains oracle evidence as a diagnostic for registration and representation. Depth Anything V2 Small and DSINE quantify available monocular information under the current controlled acquisition. The result tables govern the scope of those findings.

| Scope | Decision | Prerequisite and expected benefit |
| --- | --- | --- |
| Exact depth | GO for Lab | Retain aligned depth for metric calibrated diagnosis. A validated depth sensor and body-surface attribution would be required for runtime use. |
| Predicted depth | DEFER | Require reproducible held-out benefit on independent bodies across view subsets. The 99.1 MB ONNX path is available for offline CPU trials. |
| Exact normals | GO for Lab | Retain independent orientation evidence for diagnosing camera, surface and regional fidelity under calibrated capture. |
| Predicted normals | DEFER | Require an independently usable licensed checkpoint, capture-domain evaluation, Windows packaging and an independent paired gain. |
| Combined evidence | DEFER | Fit and held-out data must show incremental gains over either channel, including conditions with pose error and loose clothing. |
| Local surface refinement | DEFER | Require geometric gain after all crossing and rig checks and within the same displacement budget as a photographic control. |
| CPU deployment | CONDITIONAL GO for Lab | Both predictors execute on Linux CPU and pass separate Windows Server CPU smoke checks. |
| Windows integration | DEFER | Require the physical Windows 11 target benchmark, full system memory and startup measurements, and normal-model rights and runtime disposition. |

| Strategy | Decision | Risk and effort |
| --- | --- | --- |
| A · Retain M7 | GO | No added runtime, deployment assets or licenses. Preserves the measured D0 behavior and current registration limitations. |
| B · Depth only | DEFER | 5–9 engineer-days. One CPU model, scale anchoring, visible-surface attribution and a registration gate. |
| C · Normals only | DEFER | 8–14 engineer-days. Offline CPU demonstrated on Linux and Windows Server. Resolve rights, desktop deployment, pose and camera conventions. |
| D · Combined | DEFER | 10–18 engineer-days. Both dependency chains plus evidence disagreement diagnostics and calibration-aware weighting. |
| E · Combined with local refinement | DEFER | 15–25 engineer-days. Adds collision and rebind checks, deterministic validation and greater sensitivity to visible-surface errors. |



## Observed decision metrics

| Arm | Evidence | Held-out cases | Mean gain mm | Median gain mm | Mean Δ held-out IoU | ≥10% gain | ≥5% loss |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D0 | Qualified M7 Engine B | 7 | 0.00 | 0.00 | 0.000 | 0 | 0 |
| D1 | Exact depth | 7 | 1.29 | 0.82 | 0.012 | 2 | 0 |
| D2 | Exact normals | 7 | 0.46 | 0.54 | 0.003 | 0 | 1 |
| D3 | Exact combined | 7 | 0.99 | 1.08 | 0.011 | 3 | 0 |
| D4 | Depth Anything V2 Small | 7 | 0.15 | 0.11 | 0.005 | 1 | 1 |
| D5 | DSINE normals | 7 | 0.36 | 0.68 | 0.003 | 2 | 1 |
| D6 | Predicted combined | 7 | 0.27 | 0.25 | 0.006 | 1 | 1 |
| D7 | Exact combined with local | 7 | 1.57 | 1.20 | 0.018 | 5 | 0 |
| D8 | Predicted combined with local | 7 | 0.27 | 0.25 | 0.006 | 1 | 1 |
| L0 | Photographic local control | 7 | 0.08 | 0.00 | 0.001 | 0 | 0 |
| D9 | Direct geometry oracle | 7 | 3.55 | 2.58 | 0.041 | 5 | 0 |

Exact depth and normals earn conditional impact for calibrated Lab work. Exact local refinement earns conditional impact in the independent-topology cohort. Predicted depth, normals and fusion have low or conditional impact under the tested CPU cost and held-out scope. Adoption remains deferred across the predicted strategies.
