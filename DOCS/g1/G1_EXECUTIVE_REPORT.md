# Human3D 2.0 G1 — MakeHuman anatomy decision

**Decision.** Keep MakeHuman as Human3D's primary parametric anatomy engine. Integrate a pinned dependency-aware evaluator for native rest geometry and retain the existing rig, UV and pose path. Start with a bounded parameter set and use geometric observations with confidence and abstention. There is enough evidence to fix the integration gap. There is no basis for claiming a general human likeness ceiling or replacing the topology.

| Branch | Audited revision |
|---|---|
| main | `480195f05fb2d1ed6c71dceabf4ba54b8bed69db` |
| development/m6 | `e0ae4eae57347466b5757bbcdaaa7194bdd31c94` |
| lab/render | `66d84ba5775b0ab22f6e587e83efa0999180255c` |
| MakeHuman v1.3.0 | `1f508f6083b2f823dab15de924b3bde72e08d77c` |

**What was tested.** G1 verified 291 modifier definitions, 1,280 target files, three asset manifests, 21 direct native equivalence controls, and 36 model–subject oracle fits. Blender rendered standardized front, side, rear and three-quarter comparisons for six configurations and verified two editable rigged exports with save/reopen. There were four same-family MakeHuman configurations and two independent MB-Lab presets. The independent inputs have different topology from MakeHuman and come from one asset library. No VLM was used.

| Question | Answer |
|---|---|
| 1. What is wrong today? | The fixed raw seed is treated as initialized anatomy. The native default is 30.00 mm away on average by seed vertex correspondence. The admitted endpoint sign, units and accumulation checked out. |
| 2. What is unused? | Dependency-weighted macro initialization for sex-shaped morphology, age, mass, muscle, height, proportion and chest fields, plus most regional, face and asymmetric targets. Ancestry factors stayed fixed during this study. |
| 3. Can it reproduce native geometry? | Current M6 matches tested incremental endpoints, with ≤0.000014 mm max after removing the default macro offset. The independent native-equivalent evaluator matched the complete 21-case suite within **0.000631 mm** max. |
| 4. What do macros improve? | Mean symmetric error fell **36.51 → 2.80 mm** on MakeHuman references. On two independent presets, macro-only fit went **24.10 → 25.56 mm**. |
| 5. What do regional modifiers add? | Adding 19 regional controls and the improved solver schedule reduced macro-only means to **0.020 mm** on family A and **21.19 mm** on B. The selected regional targets have no macro tokens at this version. Restarts explain the M3-to-M4 gap at equal basis. A secondary wider probe improved both independent cases on a separate metric. |
| 6–7. Where is the ceiling? | Demonstrated native-equivalent mean **0.020 mm** same-family and **21.19 mm** independent. On B, individual means were 20.40 and 21.97 mm, P95 85.80 and 76.86 mm. The experiment establishes attained fits. It leaves the global optimum and intrinsic ceiling open. |
| 8. What remains unrepresentable? | No anatomical property was proven intrinsically unrepresentable. Torso/arm transitions, local asymmetry, face and hand correspondence retain significant or unqualified residuals. |
| 9. Which custom fields remain necessary? | Keep current custom corrections optional. They added **0.97 mm** mean improvement on B (21.19 → 20.22 mm) and negligible gain on A. Necessity of a particular field was unproven. |
| 10. Which geometry is observable in photos? | Frontal width and relative height, well-registered side depth and projected segment lengths are best candidates. Absolute height needs scale. Silhouettes alone cannot isolate latent weight, muscle, breast firmness or posture reliably. |
| 11. Best optimizer? | Bounded global-to-regional solver with joint refinement, a small basis and a limited number of geometry-driven restarts. |
| 12. Best integration? | Extend the lightweight evaluator with native factor semantics, keep untouched upstream execution as a parity oracle, and bind future pose after canonical rebind. |
| 13. Effort? | **8–12 engineer-days** for a bounded evaluator/registry, immutable canon integration, parity and rig regressions, and CPU profiling. |
| 14. Next photographic evidence? | Scaled frontal and profile silhouettes with visible pelvis/shoulder landmarks and repeated height-aligned contours. Add rear/oblique views for visibility, local symmetry and hard depth cases. |

The slim native test profile tripped the existing M6 face-area guard. M6 bind orientations also differ from upstream roll frames even where the landmark and weight checks agree. These are integration qualification items. Keep rebind validation in the path and qualify the approved parameter range instead of weakening the gate. Independent scans, larger posture-matched samples and high-detail face/body region ground truth remain open in the backlog.

The [isolated Lab branch](https://github.com/egenovese-de/Human3D-2.0/tree/lab/g1-makehuman/tools/g1) holds the published benchmark source. The [corrected G1 Actions run](https://github.com/egenovese-de/Human3D-2.0/actions/runs/46062204700) passed permanent Lab verification, benchmark, Blender rendering and artifact upload. The downloaded artifact matched its archive SHA-256 and all 32 entries. The evidence archive includes both run dispositions, detailed measurements and editable examples. M6 local regression passed 91 tests.
