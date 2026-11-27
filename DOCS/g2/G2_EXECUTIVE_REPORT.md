# Human3D 2.0 G2 · Photographic evidence decision

**Decision.** Keep the existing detector and move its photographic evidence onto the G1 anatomical evaluator. Preserve soft silhouette and visibility information. Use registration-aware symmetric contour distance and conservative negative space as the first fitting candidate. The largest observed gain comes from the anatomical model. Additional photographic terms are conditional improvements and require registration qualification before deployment.

| Cohort | M6 controls E0 | G1 + same masks E1 | G2 contour + gap | Photo oracle E9 | Direct geometry E10 |
| --- | --- | --- | --- | --- | --- |
| Original MakeHuman (4) | 37.44 | 4.83 | 4.52 | 4.25 | 0.020 |
| Held-out MakeHuman (2) | 16.87 | 7.32 | 7.30 | 6.59 | 0.832 |
| Independent MB-Lab (4) | 24.82 | 20.09 | 20.80 | 19.77 | 21.187 |

Mean symmetric surface distance in mm. The independent E10 average covers only the two references from G1. The separate product table measures the actual M6 session with estimated camera and pose. The matched E0 probe above fixes camera and observation pose and keeps the M6 parameter set. No VLM was used. The G2 contour+gap candidate was selected on the four original MakeHuman cases. Results on the two held-outs and four MB-Lab references were kept separate from selection.

### Final decisions

| # | Research question | Answer |
| --- | --- | --- |
| 1 | Which evidence is unused? | Soft contours, explicit empty intervals, ambiguity and crop state, regional visibility, camera metadata and geometry novelty. Full-resolution originals are retained. |
| 2 | Are masks sufficient? | For clean Blender-controlled views, mean M6 IoU is 0.966. Original runtime thresholds and binary persistence are limiting under occlusion and partial visibility. Broad real-photo sufficiency remains unqualified. |
| 3 | How much does negative space contribute? | A matched three-case mean gain of 0.62 mm. The asymmetric case gains 1.79 mm. A small effect elsewhere supports a conditional term. |
| 4 | Which contour objective? | Symmetric truncated Chamfer with reliable gaps and a small occupancy stabilizer is the initial candidate. SDF was slower and lacked a repeatable advantage. |
| 5 | Do dense profiles help? | Their 3D advantage was inconsistent. Keep registered widths and depths as diagnostics. Qualify limb-local profiles after G3. |
| 6 | Is human parsing necessary? | Landmark regions are coarse. Rig-oracle regions have mixed fitting value. Keep regional visibility and defer a learned parser. |
| 7 | Are landmarks sufficient? | They support registration, with clean A median projected rig-anchor error 5.63 px. Use confidence and semantic mapping. Contour/depth observations remain necessary for body volume. |
| 8 | Does predicted depth improve geometry? | It helps the asymmetric control (7.82 → 5.00 mm) and regresses other measured cases. Defer as a fitting dependency. |
| 9 | Do normals help? | Depth-gradient normals show orientation information and substantial angular error. A separate specialized normal fitting result remains unqualified. |
| 10 | Is dense correspondence worth it? | Exact visible triangle correspondence helped one control and worsened one. Learned matching and topology mapping are unqualified. Defer. |
| 11 | How should clothing and occlusion be weighted? | Treat loose garment pixels as a soft outer bound; preserve usable exposed regions. Mark occlusion unknown and uncertain boundaries as low confidence. |
| 12 | Which viewpoints add information? | Front plus side gives complementary width and depth. Obliques and rear add visibility or shape separation where the primary views leave ambiguity. |
| 13 | How many photographs help? | Returns diminished around four to eight distinct views in the fixed-pose oracle controls. Thirty views did not reliably improve fit. |
| 14 | Which parameters can be constrained? | Visible transverse width, relative height, gross limb width and side depth can constrain combinations of native morphs. The observability matrix ranks the local tested effects. |
| 15 | What remains ambiguous? | Metric stature with unknown scale, weight versus muscle, hidden shape, chest firmness, about-face yaw without cues, and posture versus posterior/anterior contour. |
| 16 | How much does G1 help? | Original A falls from 37.44 to 4.83 mm with the same predicted masks. Independent B changes from 24.82 to 20.09 mm. |
| 17 | How much does G2 add? | Define positive as improvement versus E1. Original A +0.32 mm, held-out A +0.01 mm, independent B -0.71 mm. The G2 evidence gain does not generalize across all cohorts. |
| 18 | What is the remaining oracle gap? | Original A contour+gap is 4.50 mm above attained G1. The gap combines registration assumptions, evidence, basis and search effects. |
| 19 | What fits a CPU pipeline? | Existing MediaPipe, cached distance transforms, bounded contour/gap residuals and complementary-view weighting. Windows throughput remains unmeasured. |
| 20 | What must G3 deliver? | Per-image perspective and uncertainty, independent scale where available, rig-consistent observation pose, local visibility, and target-independent canonical outputs with held-out reprojection and rebind checks. |

The controlled benchmark includes six MakeHuman configurations, four independent MB-Lab presets, matched ablations, and actual four-view Blender comparisons. The two new MakeHuman combinations were withheld from algorithm selection. The slim rebind guard remains a release blocker for affected shapes. Real scans were not admitted. The independent references use one authored family and their alignment is fixed. Specialized human parsing, learned dense correspondence, independent normal fitting and target Windows CPU qualification remain open.

The isolated [G2 branch](https://github.com/egenovese-de/Human3D-2.0/tree/lab/g2-photographic-evidence) holds the experimental implementation. [Actions run 46065432601](https://github.com/egenovese-de/Human3D-2.0/actions/runs/46065432601) verified permanent Lab Runtime and reproduced the bounded high-mass comparison. Local and Actions E1 agree to about 0.01 mm; the RGB contour+gap result differs by about 0.31 mm across the two Blender versions. E9 and replayed G1 agree at the shown precision. Switching the selected target in the two expanded MB-Lab product runs preserved the shared-fit digest and canonical controls. Production branches stayed at audited revisions. No G3 or G4 implementation was started.
