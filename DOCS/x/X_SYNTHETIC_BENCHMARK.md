# Human3D 2.0 synthetic benchmark index

| Experiment | Fixtures | Evidence |
|---|---|---|
| P1 anatomical initialization | Same-family controls, four independent spatial warps and two procedural independent-topology proxies | [P1 qualification](P1_QUALIFICATION.md) |
| P2 canonical pose | Three edits on the pinned MakeHuman body, crossed with four poses and three routes | [P2 study](X_CANONICAL_POSE_STUDY.md) |
| P3 VLM evidence | Four procedural MakeHuman-topology warps, three actual Blender views per subject, two visual passes | [P3 evidence study](X_VLM_EVIDENCE_STUDY.md) |
| P4 end-to-end | Two held-out procedural warps, five routes, two downstream poses per resulting asset | [P4 qualification](X_P4_QUALIFICATION.md) |

Geometry uses the pinned MakeHuman asset revision and an explicit authored coordinate frame. P3 selection uses subjects 01 and 02 and P4 evaluation uses subjects 03 and 04. P3/P4 share a topology family, silhouette camera calibration and oracle fixture generation. The dataset supports controlled geometry comparison and exact vertex differences. It does not estimate statistical generalization to independently captured human anatomy.
