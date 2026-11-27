# Human3D 2.0 anatomy-first architecture audit

The application source used across P1–P4 is `e0ae4eae57347466b5757bbcdaaa7194bdd31c94`. This audit concerns the body reconstruction path. The experiment code is isolated on the Lab branch.

| Layer | Existing implementation | Experimental finding |
|---|---|---|
| Bootstrap | `bootstrap.py` loads pinned MakeHuman geometry, rig, weights and a restricted target set. | P1 admitted 26 additional targets and separated same-basis capacity from independent deformations. |
| View association | `fusion.py` associates evidence with project views, evaluates observed regions and detects inconsistent references. | P3 replay uses explicit subject and view keys. The measured fields can cover disjoint axes and their absence must survive fusion. |
| Body fitting | `fitting.py` runs bounded silhouette optimization and, when available, adds anatomical penalties and camera refinement. | P4 uses the native calibrated silhouette objective as a control and measures a latent anatomy profile separately. |
| Anatomy controls | `anatomical_evidence.py` provides evidence visibility and quantitative observation types. `regional_morphs.py` applies rig-supported local edits. | The P3 contract contains view-specific projected extent ratios. A production adapter would need to map those to the existing visibility and confidence semantics. |
| Pose and rig | `native_rig.py` rebinds joint locators and computes hierarchical transforms and skinning. | P2 found that fixed-transform transport is exact under LBS. Rebinding changes the result materially. |
| Persistence | `frozen_body.py` validates content-addressed bodies and their topology and rig. `usd_export.py` exports a skinned mesh and pose animation. | P4 reopens native outputs, evaluates skinned poses and verifies the canonical digest after downstream export. |

Full production validation still needs natural images, explicit calibration uncertainty, independent human anatomy, the production landmark/refinement path and downstream garment and texture checks.
