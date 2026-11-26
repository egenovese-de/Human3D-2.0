# Human3D v0.2.0 Q benchmark

The [held-out follow-up](Q_HOLDOUT_FOLLOWUP.md) adds four preset identities, articulated fixtures and changed reference inputs. This report records the original pilot.

27/43 tasks completed, 16 blocked. 12/12 controlled native runs completed. 6 calibrated independent geometry sweeps, 6 matched factorial sweeps, 6 independent pose diagnostics and 6 structural component sweeps. Each calibrated geometry sweep covers six view configurations and two direct 3D search schedules. 2 independent subjects completed a separate sixteen-view controlled repeat.

Release CI jobs scan, classify, Linux foundation, Windows foundation and Required summary passed in [run 45869017319](https://github.com/egenovese-de/Human3D-2.0/actions/runs/45869017319). Local release tests 69/69. The existing calibrated Lab runner, unchanged, reproduced 99.6724% held-out IoU and 3.7899 mm vertex RMSE. The original stabilization report records 75.669% native fitting IoU and 90.128% observed UV coverage on the historical four-view fixture. Source reports are [M5](M5_FINAL_BENCHMARK.md) and [stabilization](https://github.com/egenovese-de/Human3D-2.0/blob/480195f05fb2d1ed6c71dceabf4ba54b8bed69db/DOCS/STABILIZATION_CANDIDATE.md). The raw historical photographic fixture was not rerun here. Agreement to detector masks with image and pose estimation differs from a fit to exact masks formed mostly by the solver morph basis on matching topology. The 99.67%-versus-75.67% historical difference cannot be assigned to one component. Held-out independent pilot results and matched interventions bound the contributions under the published protocol.

| Native fit reported IoU (%) | n | Mean | Median | SD | P05 | P95 | Min |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 photo(s) | 6 | 66.044 | 63.098 | 7.210 | 60.129 | 76.573 | 59.886 |
| 4 photo(s) | 6 | 66.689 | 66.243 | 8.501 | 57.397 | 77.125 | 57.312 |

| Observed UV coverage (%) | n | Mean | Median | SD | P05 | P95 | Min |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 photo(s) | 6 | 38.294 | 37.828 | 2.007 | 36.212 | 40.873 | 36.065 |
| 4 photo(s) | 6 | 84.575 | 83.086 | 2.940 | 82.245 | 88.754 | 82.102 |

| Native elapsed runtime (s) | n | Mean | Median | SD | P05 | P95 | Min |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 photo(s) | 6 | 59.202 | 59.875 | 6.221 | 50.731 | 65.747 | 48.174 |
| 4 photo(s) | 6 | 127.535 | 118.766 | 22.172 | 114.461 | 160.397 | 113.815 |

Initial release detector launch failed on a missing system GLES shared object. Provisioning the stock Debian library locally fixed the error. A wrapper attempt with absent GNU time and a single retry due to the Lab clean-tree guard are recorded separately. Native peak RAM and texture/export stage breakdown were unavailable in the legacy runner. Geometry evaluator peak RSS and native artifact sizes are recorded.

## Outstanding evidence

- **Q0-005** Camera/calibration validation passed. Independent subject holdout remains unavailable with two base meshes and their paired deformation variants.
- **Q1-006** A torso displacement stress case was executed. Independently rigged spinal and pelvic rotations were unavailable.
- **Q2-004** Rig endpoints exist for selected bones. An independent 33-landmark surface protocol with detector-equivalent visibility was unavailable.
- **Q2-005** A calibrated yaw-only probe ran. True anatomical measurements and shape have no provider field. Oracle visibility could not be established at the provider’s region level.
- **Q2-007** Fixed-camera/mask fits and separate limb-direction substitutions ran. A jointly valid pose and landmark oracle was unavailable.
- **Q2-008** Independent meshes have different topology, UV and rig. Texture and garment builders require a compatible frozen asset and its rig/UV bindings. No compatible independent adapter was validated.
- **Q3-004** The supplemental repeat includes duplicated frontal input when its report is present. Truly contradictory and differently posed calibrated pairs remain unavailable. Unrelated AI photos were kept separate.
- **Q4-005** Clothed AI cases lack independently paired bare-body geometry and garment masks.
- **Q5-001** Cranial surface distance was measured. Annotated facial landmarks and dense facial region masks were unavailable.
- **Q5-002** Jaw control locality was exercised. Facial profile/cranial identity ground truth and controlled expressions were unavailable.
- **Q5-003** Rest-anchor position and segment-direction errors were measured. Registered ground-truth joint rotations were unavailable.
- **Q5-004** The pilot has a neutral stance. Independent articulated wrists, torsion and ground-contact annotations were unavailable.
- **Q5-005** Observed UV coverage was measured. A radiometrically calibrated texture target with correspondence was unavailable.
- **Q5-006** Measured observed fraction only. Matched UV seams, texture charts and occluder-labelled texels were unavailable.
- **Q5-007** Sampled shell clearance was measured. Independent garment mesh, hem alignment and exact triangle intersection labels were unavailable.
- **Q5-008** USD package structure and shell motion were inspected. Layered independent cloth and a USD-capable Blender executable were unavailable.

Machine-readable [measurements](q/measurements.json) and [dataset hashes](q/manifest.json).
