# Human3D 2.0 · M5 and B synthetic validation

## Historical subject

The original four views come from `Human3D_2.0_Curvy_Woman_4Views.zip` with SHA-256 `f673f4ecb9957ee0c06676a175bbbc29128655c5c582a07ae4cb2586dac709f5`. Their anatomy and poses are not a calibrated 3D reference. The historical M4 values were supplied by the Project Lead. M4 at `16136fd` aborted on the original dimensions in segmentation. The paired rerun used the same four Lanczos-resized 1120×1408 files for both revisions, with the original and resized hashes retained in the manifests. Its M4 result did not reproduce the historical M4 report. Therefore the clean protocol comparison is between rerun columns. Both paired Blender scenes use the same camera center, span, lighting, directions and Cycles settings.

| Metric | Historical M4 reference | M4 paired rerun | Final M5 paired rerun | Final M5 originals |
|---|---:|---:|---:|---:|
| Mean silhouette IoU | 68.94% | 54.99% | 75.94% | 75.47% |
| Front | 77.98% | 75.42% | 78.07% | 77.93% |
| Three-quarter | 58.85% | 69.03% | 74.12% | 74.28% |
| Profile | 65.49% | 52.84% | 74.95% | 72.87% |
| Rear | 73.41% | 22.67% | 76.62% | 76.80% |
| Observed UV coverage | 88.88% | 58.18% | 90.44% | 90.39% |
| Mean normalized landmark RMSE | — | 6.69% | 3.05% | 2.92% |
| Mean normalized contour error | — | 3.44% | 1.42% | 1.44% |

IoU uses the 256 px fitting resolution. Overlays and contour/landmark diagnostics use 512 px and divide errors by detected silhouette height. Landmark RMSE measures agreement with visible detector landmarks, and includes no independently annotated photographic ground truth. The M5 original-resolution rear view exceeds 3% even though the mean passes. The paired mean landmark gate fails by 0.05 percentage points. Both final photographic IoU scores fail the 85% target. Mean contour error passes the 2% target. Benchmark execution succeeded.

The final bounded camera-only adjustment held fitted shape fixed. In the original-resolution rerun it moved mean IoU from 74.04% to 75.47%, leaving a 9.53-point gap to the target. Abdomen and glute depth and several circumferences remain bounded at saturation. The historical silhouettes include clothing and pose differences and provide no independent neutral shapes. The results support a camera contribution and remaining geometry/evidence ambiguity, with no basis for increasing limits. No morph bounds were increased.

## Coherent calibrated fixture

The solver used front, profile and rear masks. The 130° view was held out. Ground truth includes an independent localized analytic torso displacement in addition to known morph controls. Camera-only, geometry-only, jointly corrected, and single-photo results are in `evidence/geometry.json`, including global IoU, per-band IoU, normalized contour and held-out metrics. Optimization used bounded coordinate steps of 0.25 then 0.125. This is a finite search with no claim of global convergence.

| Held-out result | Value |
|---|---:|
| Correct camera, bootstrap geometry | 97.64% IoU |
| Front-only anatomy fit | 99.20% IoU |
| Multi-view anatomy fit | 99.67% IoU |
| Joint projection RMSE / body height | 0.081% |
| Contour error / image diagonal | 0.0083% |
| Fitted vertex RMSE | 3.790 mm |
| Voxel hull IoU, bootstrap → fitted | 92.13% → 95.89% |
| Saturated controls | 0 |

A 32³ voxel lookup contributes to fitting calibrated neutral silhouettes. Native articulated fitting additionally penalizes projected canonical samples outside the observed silhouettes. The evaluation hull is independently measured on a 36³ grid. The calibrated render shows the fitted asset with a procedural UV diagnostic material.

## Integration and structural checks

- Studio fixtures: 3/3 negatives rejected and 6/6 positives retained. The cropped case remains in review. Four original-resolution views completed. Native M4 original-resolution aborts are archived separately.
- Original-resolution project passed full export and direct Blender 4.5.16 import. Body and top kept their own meshes and shared a 163-bone rig. Both remained posed after reopening the editable Blender file.
- Pose validation checks finite points, face collapse, bone lengths and sampled stance. Supported floor placement is derived from modeled feet. A raised foot can remain raised and a lower non-foot contact disables this placement. There is no independent floor calibration in the historical images.
- UV and canonical invariants passed the jaw deformation check. The controlled visibility test recorded the occluded texel as unobserved and retained the expected observed color on the front face. The historical run records separate skin, hair-candidate and top coverage masks. Hair remains an appearance contribution.
- Top, shorts and trousers had zero sampled violations beyond 1 mm on front and profile poses. The exported separate top had a minimum signed sampled gap of −0.944 mm, inside the existing 1 mm tolerance. This does not establish zero triangle intersections at arbitrary poses.
- 29 automated tests passed, including persistence, target switching, dependency invalidation, cancellation/recovery, wrist roll and provider binding. Packaged wheel installation and Qt startup succeeded.
- The native pipeline operates on frozen assets after bootstrap. Render and diagnostic tools use the frozen project artifacts. No photos or benchmark-derived meshes were committed to Git.

## Provider

B3-003 stays BLOCKED. The runtime has no configured real VLM provider, credentials, or accessible endpoint supplied for this run. The deterministic adapter tests cover ambiguous candidate suppression and photo-bound evidence. They do not validate an external model.

## Reproduce

Python 3.11.18, Linux, MediaPipe 0.10.33, NumPy 1.26.4, SciPy 1.15.3, Pillow 13.0.0, Qt 6.8.3, OpenUSD 25.11 and Blender 4.5.16 LTS. Pose Landmarker Lite v1 SHA-256 `59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a`. Per-image SHA-256, model provenance, fitted controls and local runner SHAs are included in the evidence. Code trees correspond to the published implementation and Lab sources listed in the handoff, with later documentation and regression-test additions.

Install the platform lock and wheel in `build/` using Python 3.11, then start `human3d-desktop`. Linux requires EGL, GL and GLES system libraries. Use `lab/tools/benchmark_native.py` with the selected checkout on PYTHONPATH, input manifest, authorized bootstrap assets and verified detector. Use `--target subject_01_front.png`; the original-resolution final run additionally used `--garment top --ground`. The calibrated runner uses `--regional --carve --independent`. `diagnose_native.py`, `check_visual_hull.py` and `check_supported_garments.py` produce the accompanying diagnostics. The paired M5 Blender renderer reads the M4 render report via `--framing`.

Empirical real-photo acceptance and production readiness were not evaluated.
