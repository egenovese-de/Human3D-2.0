# Dependencies and critical path
Default execution order is master backlog order; one active task. Each delivery below is a required integration boundary before dependent work. Independent capabilities may be prepared sequentially when prerequisites satisfied, not by concurrent branch writers.
M1 critical path: rights -> contracts/package -> project/import -> orchestrator -> evidence/mask -> freeze -> camera/overlay -> native fit -> rig/USD -> inspection/export -> real-photo/Blender gate. UI shell follows persistence, review follows actual evidence, overlay precedes fit (breaks legacy approval deadlock). M1-015 completes inspection; earlier deliveries require minimal actual preview/report actions as part of their own tasks, not waiting for 015. Rig/USD can be developed against frozen asset after freeze but cannot establish reconstruction acceptance until fit works.
M2: immutable evidence -> fusion -> native torso/limbs -> rig -> independent views -> objective -> alternating fit -> uncertainty -> inclusion/invalidation -> restore -> holdout. Optional VLM can be isolated after binding, must not block local fusion. M2-011 must preserve target-independent body digest. M3: pose/contact/rig and facial refinement precede texture projection; skin masks -> bake -> visibility/seams -> materials -> completion -> textured USD. M4: categories -> segmentation -> independent geometry -> rest UVs -> fit -> materials -> weights -> collision/layering -> assembly -> production GUI -> usability/release. Garment materials and weight transfer can be independent after rest mesh, but final fit requires both.
Risks: monocular depth/scale ambiguity (explicit uncertainty and held-out views); coupled pose/shape (bounded alternating objective, reject distortions); fragmented masks (regional correction); loose clothing (exclude unsupported body contours); rig deformation (real articulation checks); texture lighting and hidden regions (coverage labels); garment scope (limited categories); Blender USD compatibility (actual import early); redistribution (audit before copying). Missing runtime evidence and exact versions remain open. No schedule estimates until M1 measurements.
Conflict resolutions: late GUI vs early empirical access -> thin integrated shell M1, final UX M4; automatic overlay before review region approval; target switch independent from reference inclusion; valid partial export explicitly labeled, never claim complete; optional external provider not required; semantic edits limited to supported operations, no Blender replacement. Source wireframes and technical tests are not empirical proof.

## Delivery gates and independent work
A pending empirical candidate is frozen by SHA, environment, input and artifact digests. Only one active implementation task; independent work may proceed only with accepted prerequisites and without modifying pending candidate or shared contracts. No dependent work on PARTIAL/FAIL/BLOCKED. Milestone acceptance blocks next milestone implementation.

| Delivery | Blocks | Independent work candidate | Human review |
|---|---|---|---|
| D1-01 | migration/package | inventory only | conditional |
| D1-02 | integrated photo workflow | cleared numerical preparation | no |
| D1-03 | photo fitting | bootstrap preparation | yes |
| D1-04 | native consumers | evidence tooling | yes |
| D1-05 | fit | USD fixtures | yes |
| D1-06 | M1 gate | benchmark prep | yes |
| D1-07 | M2 | nonimplementation prep | owner |
| D2-08 | fusion consumers | native deformation prep | conditional |
| D2-09 | shared optimization | independent views | yes |
| D2-10 | multi-view acceptance | independent revision tooling | yes |
| D2-11 | M2 gate | benchmark prep | conditional |
| D2-12 | M3 | nonimplementation prep | owner |
| D3-13 | pose-dependent appearance | independent face work | yes |
| D3-14 | head appearance | body skin masks | yes |
| D3-15 | texture/materials | export fixtures | yes |
| D3-16 | M3 gate | benchmark prep | yes |
| D3-17 | M4 | nonimplementation prep | owner |
| D4-18 | garment fit | independent accessibility | conditional |
| D4-19 | garment deformation | workflow prep | yes |
| D4-20 | assembly | independent accessibility | yes |
| D4-21 | product validation | participant prep | yes |
| D4-22 | final acceptance | release audit | owner |
| D4-23 | release | none affecting candidate | owner |