# P1 qualification

## Historical checkpoint

Run 46004218815: SUCCESS. Frozen JSON and native USDZ persistence: 4/4 PASS. Independent procedural deformation oracle: all four subjects improve, mean 22.358 to 20.493 mm (8.34%). Shared topology; not independent human scans. Macro-only fitting, not expanded regional comparison. Local repair: 4/4 PASS. Remaining: independent topology, broader anatomical inventory, regional metrics/refinement and controlled artifact admission. P1 was partially qualified at that checkpoint.

## Editable Blender persistence

[Run 46005412637, job 140527220405](https://github.com/egenovese-de/Human3D-2.0/actions/runs/46005412637/job/140527220405) completed successfully on Lab revision `9f3062612c46aadb8cce557874eab386837ad18b`. The `X_P1_EDITABLE` log verified 4/4 body-only assets through direct USDZ import, articulation, mesh editing and Blender save/reopen. Maximum skin-weight normalization error was `4.470348358154297e-08`. See [machine-readable evidence](p1-editable-persistence.json) for per-subject movements, Blender scene file digests and GitHub artifact metadata.

## Final P1 qualification — 27 November 2026

**P1 is complete in the synthetic, oracle-geometry investigation scope.** Keep expanded MakeHuman as the anatomy-first foundation and regional refinement as a separate stage. Retain the neutral and parametric baselines for the pose study. The evidence does not establish a universal winner among initialization methods, photographic reconstruction quality, or production readiness.

The complete suite passed in [GitHub Actions run 46009817216, job 140542173252](https://github.com/egenovese-de/Human3D-2.0/actions/runs/46009817216/job/140542173252) on Lab revision `eabbb35f6a22377ffb6d22a5a37c3c52811a4507` and application revision `e0ae4eae57347466b5757bbcdaaa7194bdd31c94`. The [admitted bundle](https://github.com/egenovese-de/Human3D-2.0/actions/runs/46009817216/artifacts/15203846653) uses seven-day retention. The archived ZIP digest matched GitHub's reported SHA-256. Offline Lab verification independently matched byte counts and digests for all 72 staged files. The CI log contains `X_P1_ADMISSION_NEGATIVE_PASS` for the rejected unauthorized file. The 24 held-out Blender renders were decoded and inspected as a comparison sheet. All four editable body assets passed the Blender persistence control again.

| Remaining work | Final result |
|---|---|
| P1-R01 | Published the verified Blender log measurements, run, job, revisions and artifact metadata. |
| P1-R02 | Mapped the pinned MakeHuman target library and verified 26 additional regional targets through Lab bootstrap and verification. |
| P1-R03 | Compared all four methods on two independently constructed procedural meshes with 43,376 and 44,584 vertices, using held-out surface samples. |
| P1-R04 | Ran a common regional fit on four spatial warps and two procedural proxies. All 48 initial and refined candidates passed native rebind and articulation. |
| P1-R05 | Published only the staged, SHA-256-inventoried bundle after the allowlist and negative control passed. |
| P1-R06 | Verified CI, raw measurements, proxy limitations and native controls. Archived the findings and updated X-009 and X-010 in the original 23-task backlog. |

## Regional comparison

Global mean surface distance in millimetres. Forward measures reference to candidate. Reverse measures candidate to reference. See the [complete regional measurements](p1-regional-results.json) for mean and P95 in each region, section perimeters, volume deviations, native compatibility, joint results and runtime.

| Fixture family | Initialization | Initial forward / reverse | Refined forward / reverse |
|---|---|---:|---:|
| Spatial warps | Neutral | 14.54 / 14.04 | 9.88 / 12.68 |
| Spatial warps | Parametric | 11.97 / 13.91 | 8.29 / 13.10 |
| Spatial warps | Prototype | 23.94 / 23.36 | 19.91 / 21.80 |
| Spatial warps | Hybrid | 17.08 / 17.71 | 13.14 / 16.46 |
| Independent topology | Neutral | 26.28 / 21.58 | 25.94 / 21.56 |
| Independent topology | Parametric | 25.11 / 21.38 | 25.53 / 21.48 |
| Independent topology | Prototype | 29.56 / 23.56 | 27.92 / 21.99 |
| Independent topology | Hybrid | 25.65 / 20.62 | 24.71 / 19.80 |

After refinement, parametric leads on the forward warp metric and neutral leads on the reverse warp metric. Hybrid leads on both mean proxy metrics, while parametric achieves the lower forward P95 on the proxies (77.04 mm versus 86.72 mm). The regional solve and deformation took 11–20 ms across the 24 fitted candidates in the qualified CI run. The earlier same-family pilot remains evidence of target-basis capacity.

## Experimental scope

- Four MakeHuman-topology fixtures use independent spatial warps. Initialization and regional refinement use the same 4,460 oracle 3D correspondences for every method. The 8,920 held-out vertices provide an additional paired check in the fixed native pose and frame.
- Two original procedural proxies use independently specified ellipsoid unions and marching tetrahedra. Their training surface samples and evaluation surface samples use separate seeds. The initialization fits in the authored native frame and uses fixed nearest-point correspondences derived from the neutral mesh. The proxy is an unrigged geometric control with coarse anatomy, no reference joints and no independent human measurements. Residuals can include differences in local pose and proportions. The warp experiment isolates morphology in the shared pose and frame. Neither experiment consumes photographic evidence.
- Neutral, parametric, prototype and hybrid candidates receive identical observations and a shared regional solver with a coefficient bound of ±0.35 per field. The candidate basis uses 3 previously admitted torso fields and the 13 positive directions from the new manifest. Signed coefficients provide a linear approximation to the negative directions. The 26 files preserve the original paired endpoints, with direct upstream targets on each limb side.
- Forward and reverse distances are computed between held-out surface points and independently sampled candidate surfaces. They are finite-density, nearest-sample estimates. Warp forward measurements use held-out vertices while candidate evaluation is area-sampled, so the two directions have different sampling densities. The warp paired error provides a separate correspondence-based check. Global P95 values in the summary are means of subject-level P95 values.
- Seven spatial region labels support mean and P95 distances. Circumferences are fixed-plane convex-hull perimeters, with a central crop for torso sections and a unilateral crop for leg sections. Volume uses signed closed-mesh geometry. Joint errors are available for the warps, and unavailable for the unrigged proxies. Runtime covers the regional fit and deformation, with export, rendering and metric computation outside that interval.
- Native candidate checks include structural rebinding, skin-weight normalization, effective arm articulation and unchanged UV indexing. The procedural proxy triangulations contain a small number of near-zero-area facets at the numerical threshold. Their original surfaces remain closed by edge incidence. This benchmark did not test self-intersections or photograph-derived reconstruction.

## Evidence

- [Anatomical capacity and licensing inventory](P1_ANATOMICAL_CAPACITY.md)
- [CI provenance and aggregate numerical results](p1-final-evidence.json)
- [Regional results for all 48 candidate states](p1-regional-results.json)
- [Exact staged file inventory](p1-artifact-manifest.json)
- [Editable Blender persistence evidence](p1-editable-persistence.json)
- [Investigation backlog](../BACKLOG_X.md)
