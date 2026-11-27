# Human3D 2.0 executive recommendation

**Continue anatomy-first research. Keep the M6 path as the default.**

- P1 supports retaining the MakeHuman base and opening more of its anatomical control space. Results depend on the fixture and the direction of the distance metric.
- P2 supports native-space anatomy and joint rebinding. A-pose distorts the neutral surface less than X and T in this benchmark. Pose-space morph transport is exact only when the same LBS transforms are used.
- P3 selects geometry-oriented projected evidence for continued testing. Missing visibility remains explicit. The experiment does not establish calibrated uncertainty or an advantage for specialist prompts.
- P4 shows that the native canonical contract and two independent downstream poses are technically feasible for the synthetic body-only control. Visual evidence averaged 25.70 mm canonical error against 23.87 mm for calibrated M6. The 18.94 mm oracle result establishes headroom with stronger observations.

A production decision needs held-out examples across anatomy families and cameras, an isolated visual evaluator, distinct reference diversity at higher counts, and comparison against the full production pipeline. Retain the content-addressed canonical asset and the pinned, measurable evaluation path.
