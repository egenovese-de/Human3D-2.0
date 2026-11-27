# Photographic evidence architecture decision

Use the existing local detector and the verified G1 evaluator as the minimal candidate stack. Keep the original image reference, oriented RGB transform, soft mask and four-state visibility. Mint per-region, per-observation provenance and uncertainty. Use sparse landmarks for registration, and truncated symmetric contour with conservative negative occupancy and an IoU diagnostic for fitting. Choose complementary views by usable region and expected sensitivity. Retain the canonical shape separately from per-image cameras, observation poses and final target articulation.

| Mechanism | Disposition | Evidence and integration |
| --- | --- | --- |
| Existing MediaPipe masks and anchors | ADOPT WITH LIMITATIONS | High clean-fixture mask overlap and a measured coarse registration signal. Fixed confidence cutoffs, pose dependence and semantic anchor offsets limit direct anatomy fitting. Preserve confidence maps and original transforms. |
| Visible foreground/background plus unknown and uncertain pixels | ADOPT | Photo and occlusion ablations distinguish observed background from unsupported geometry. Build with existing distance transforms. Use asymmetric soft loss for clothing where its class is established. |
| Truncated symmetric contour + gap | ADOPT WITH LIMITATIONS | Matched asymmetric case improved 6.70 → 4.91 mm. Other matched gains were smaller. Candidate selected on original A gave 4.52 mm, with a negligible gain versus E1 on held-out A and the open slim rebind gate. Use a visibility- and pose-dependent term. |
| GrabCut / uniform background key | OPTIONAL | Fast current-detector refinement has mixed extraction and fitting gains. Use the direct border key in calibrated studio captures only. No broad replacement of M6 segmenter is supported. |
| Dense row profiles | OPTIONAL | Good diagnostics and low extraction cost. Dense fit gain was inconsistent and sensitive to registration. Integrate as a regional diagnostic after geometry registration. |
| Region parsing | DEFER | Landmark regions and oracle rig labels showed coarse support, with no qualified learned parser. Keep deterministic regional visibility and add a specialised parser only if matched geometry improves. |
| Relative depth and derived normal | DEFER | Per-view signal and affordable CPU experiment, with inconsistent 3D gains and large side-profile errors. Preserve outside the default stack. |
| Dense body correspondence | DEFER | Exact same-topology control helped one subject and regressed another. A learned cross-topology mapping and chirality/visibility verification would be substantial new work. |
| Visual hull | OPTIONAL | High calibrated volumetric overlap at 8 views and residual concavity errors. The tested fitting penalty changed geometry little. Restrict to static calibrated observations. |
| Static stereo on uncontrolled inputs | REJECT | Calibrated stereo produces informative relative geometry under engineered texture, but practically requires fixed pose and calibrated cameras. This does not qualify an unattended default path. |
| Region-specific fusion and duplicate detection | ADOPT WITH LIMITATIONS | Contradictory-view tests motivate local weighting, per-observation provenance and diversity checks. The tested robust policy is a heuristic. Recalibrate under G3. |

### G3 acceptance requirements

1. Preserve orientation, principal point, focal length or focal prior, resolution, crop and pixel-centre transform. Use the same convention in render, correspondence and fitting modules.
2. Estimate per-image yaw, elevation, roll, translation and camera covariance. Break front/back and mirrored-pose ambiguities with explicit orientation cues, or carry multiple hypotheses.
3. Establish metric scale from independent measurement or expose scale ambiguity. Audit perspective error before choosing weak perspective.
4. Register model-consistent skeletal anchors and observation articulation separately from the canonical fit. Propagate confidence and local registration covariance to contour and landmark terms. Keep candidate pose and final articulation out of shared anatomy.
5. Distinguish external occlusion, self-occlusion, foreground and uncertain boundaries with per-region visibility, including partial frames and clothing. Preserve valid local observations from imperfect images.
6. Pass calibrated versus estimated camera and pose controls using per-image and per-region held-out residuals. Test conflicting views and near duplicates, mixed capture distances and articulation, and post-fit rebind including the known slim case.
7. Certify runtime and memory on Windows 11 / i7-1355U / 16 GB with staged evidence caching.

A bounded implementation of evidence preservation, two confidence-aware contour terms, visibility flags and their regressions is **6–10 engineer-days**. Estimate **10–16 engineer-days** for the G3 calibration and observation-pose work with controlled reconstructions. These ranges assume reuse of the existing runtime, evaluator and detector. Windows performance and practical photo calibration remain gates to adoption. G2 executes research only.
