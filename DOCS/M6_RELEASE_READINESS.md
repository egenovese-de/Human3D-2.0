# Human3D 2.0 v0.3.0 release readiness

**BLOCKED.**

| Gate | Outcome |
|---|---|
| Locked Linux/Windows CI and clean Windows install | PASS on product code `b2a84312ccf2d2119f9b7667f6368684f02455e0` |
| Local regression suite | 91 PASS |
| Editable direct Blender USDZ round-trips | 4/7 PASS |
| Qualified pose, depth, twist and contact improvements | BLOCKED on independent anatomical correspondence and evaluation |
| Qualified automatic regional geometry and acceptance | BLOCKED on realistic independent source-family evidence |
| Facial and identity reference validation | BLOCKED on independent ground truth and a qualified reference mechanism |
| Paired independent held-out quality suite | BLOCKED. Stylized adverse fixture exercised; realistic cohort incomplete |

Development may continue with the existing package version while the mandatory gates remain open. The highest priority next implementation is an armpit/seam-aware constrained repair that handles both skinned contact and shell self contact together, followed by a repeat of all seven USDZ controls. Independent realistic meshes and two blind annotation passes can proceed in parallel. See the [signed acceptance criteria](ACCEPTANCE_M6.md) and [exact blockers](M6_BLOCKER_RESOLUTION.md).
