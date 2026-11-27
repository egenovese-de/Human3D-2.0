# Runtime qualification
Qualified scope: Windows CI, pinned source v0.2.0, synthetic CC0 anatomy and original procedural outputs. This is not production reconstruction accuracy qualification.

| Criterion | Result | Evidence |
|---|---|---|
| A Linux clean bootstrap | PASS historical; final platform deferred | lr-002 |
| B Windows clean bootstrap | PASS | lr-002 |
| C reuse | PASS | lr-002, lr-006 |
| D numerical deterministic runner | PASS | lr-004 |
| E native reconstruction | PASS synthetic | lr-009 |
| F Blender human render | PASS | lr-009 |
| G save/reopen rig and geometry | PASS counts; numerical weight equivalence unmeasured | lr-009 |
| H historical Q/M6 | PARTIAL/DEFERRED by approval | lr-005-acceptance |
| I evidence replay | PASS offline synthetic only; application adapter integration untested | lr-009 |
| J negative controls | PASS isolated six controls; runner timeout propagation untested | lr-009 |
| K GitHub execution/artifacts | PASS | lr-007, lr-009 |
| L extended anatomy | PASS six signed targets, deterministic deformation, articulation and render | lr-009 |

Machine-readable evidence: lab/manifests/lr-002-qualification.json through lr-009-qualification.json (LR-005 uses lr-005-acceptance.json). Final native run 45996285366, jobs 140496386848 and 140496500512, both successful. Artifact 15195673563, 26 files verified in CI, SHA256 cd126ed17e1e1fde2694b32eaceb5729caa13c7e862412fed5bd592100d6473c.
No claim of real GPT inference or historical fixture recovery. Morph aliases are lab-only; IoU refers to the original hips oracle, not the expanded torso export.
