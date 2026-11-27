# Human3D 2.0 — P4 anatomy-to-asset comparison

## Decision

Keep the calibrated M6 reconstruction route as the default. The experimental anatomy-first pipeline can persist a valid native canonical body and generate two independent posed exports. Visual evidence E did not reduce mean reconstruction error across the held-out pair. Oracle evidence reduced canonical error, so the admitted shape basis can improve reconstruction when supplied with stronger observations.

## Comparison design

Subjects 03 and 04 were held out from P3 method selection. Both use independently specified spatial deformations on the same native MakeHuman topology. Calibrated front and side projections are shared across the silhouette paths. The GPT-derived branch consumes visual observations from Blender views of the same subjects. The oracle branch uses a disjoint training subset of 4,460 exact 3D vertex correspondences and reports an additional error over the held-out 8,920 vertices. The oracle route therefore has access to stronger evidence by design.

| Route | Input and geometry method |
|---|---|
| A | Native M6 silhouette scorer, supported control registry and coarse/fine optimizer with two known camera alignments and exact synthetic silhouettes |
| B | Four expanded initialization fields fit to projected waist and hip extents from the same silhouettes |
| C | B followed by a bounded three-field regional refinement against residual section observations |
| D | Seven-field oracle fit from sparse exact 3D anatomy observations |
| E | Seven-field fit from the P3-selected geometry-oriented visual evidence, fused across views |

A controls for the current native optimization path under known camera calibration. The synthetic benchmark does not exercise photographic detection, camera recovery, or the full production observation fusion workflow. Canonical geometry stays in native space per P2. Every candidate is rebound and frozen before two independent target poses are applied. The body-only trial uses placeholder appearance and does not qualify facial identity, garments, cloth contact or photographic texture coverage.

## Numerical results

Canonical mean and P95 use same-topology vertex distances in millimetres. Overall P95 averages subject-level P95 values. Posed means average the two downstream views and the two subjects. IoU measures silhouettes with the same calibrated cameras.

| Route | Subject 03 | Subject 04 | Canonical mean | Canonical P95 | Posed mean | Front / side IoU |
|---|---:|---:|---:|---:|---:|---:|
| A | 24.34 | 23.40 | 23.87 | 76.62 | 19.82 | 0.874 / 0.923 |
| B | 27.13 | 25.08 | 26.10 | 78.27 | 21.79 | 0.863 / 0.896 |
| C | 27.13 | 25.07 | 26.10 | 78.27 | 21.79 | 0.864 / 0.896 |
| D | 20.42 | 17.46 | 18.94 | 47.48 | 19.52 | 0.887 / 0.907 |
| E | 22.51 | 28.89 | 25.70 | 74.63 | 22.37 | 0.859 / 0.897 |

E improves subject 03 and degrades subject 04 versus A. The extra regional stage C produces little change with the available section observations. D improves mean canonical error by about 20.7% relative to A. These findings do not establish general dominance across shape families.

## Native asset qualification

All ten canonical candidates passed native validation, including finite geometry, face/UV references, skeleton, weights and loader digest. All 20 USDZ packages were reopened in OpenUSD, compared in canonical coordinates and evaluated against the native skinned pose. Each supported a point edit in the OpenUSD session layer while the on-disk archive retained its digest and the binding remained valid. The canonical digest remained identical across both downstream poses. Editable USDZ qualification here is in OpenUSD's session-layer model. P1 separately tested Blender save/reopen.

## Published evidence

[GitHub Actions run 46013006743, job 140553532284](https://github.com/egenovese-de/Human3D-2.0/actions/runs/46013006743/job/140553532284) completed on Lab revision `822f153aa156f8316418bda106fe30f43d7a5a5d`. The [admitted bundle](https://github.com/egenovese-de/Human3D-2.0/actions/runs/46013006743/artifacts/15204706728) includes meshes, frozen anatomy, posed USDZ, source observations and 24 comparison renders. The authorized inventory, negative control, exact ZIP SHA-256 and all 72 staged file digests were verified. The 24 images were decoded and visually inspected.

The body-fit, replay and asset validation process took 132.91 seconds with a peak working set of 256.6 MiB. Native M6 calibrated fitting took 46.70 and 45.02 seconds for the two subjects. The maximum native-to-OpenUSD skinned vertex difference was 0.0001431 mm. Every candidate passed validation at its full proposed deformation. Exact per subject regional distances, circumference and volume deviations, proportions, three-dimensional held-out checks, timings and artifact hashes are in the [machine-readable evidence](p3-p4-evidence.json).

This closes P4 in the calibrated, body-only synthetic scope and records a negative result for replacing M6 with the tested visual-evidence path. X-014, X-017 and X-019 remain in progress for broader independent fixtures, high-count independent visual inference and downstream combinations beyond the tested body-only asset.
