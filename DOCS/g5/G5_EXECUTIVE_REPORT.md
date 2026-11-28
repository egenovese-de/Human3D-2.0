# Human3D 2.0 G5 — feasibility decision

**Retain Strategy A for M7 and the next production release.** Exact channels establish the value of measured surface geometry under controlled acquisition. The predicted path requires a repeatable independent-topology benefit and reliable registration before it qualifies for integration. G5 measured the original G4 cohort with a separately executed Engine B baseline. The study remains open for the outstanding qualification listed below.

Qualified Engine B completed **10/10 calibrated** and **9/10 estimated** full service runs. The calibrated D0–D9 matrix plus the photographic local control is available for **10/10 subjects**. Mean metrics below use held-out subjects, paired by configuration, with separate camera paths.


## MakeHuman · calibrated

| Configuration | Mean surface error | Improvement vs M7 | Held-out impact | Runtime | Decision |
| --- | --- | --- | --- | --- | --- |
| D0 (4) | 7.45 mm | 0.00 mm | Δ IoU 0.000 | 16.29 s | Retain |
| D1 (4) | 6.27 mm | 1.18 mm | Δ IoU 0.012 | 12.52 s | Lab control |
| D2 (4) | 7.15 mm | 0.29 mm | Δ IoU -0.001 | 12.85 s | Lab control |
| D3 (4) | 6.71 mm | 0.74 mm | Δ IoU 0.007 | 14.65 s | Lab control |
| D4 (4) | 7.06 mm | 0.39 mm | Δ IoU 0.008 | 15.44 s | Defer production |
| D5 (4) | 7.37 mm | 0.08 mm | Δ IoU -0.001 | 12.23 s | Defer production |
| D6 (4) | 7.22 mm | 0.22 mm | Δ IoU 0.005 | 12.48 s | Defer production |
| D7 (4) | 6.71 mm | 0.74 mm | Δ IoU 0.007 | 14.92 s | Defer production |
| D8 (4) | 7.22 mm | 0.22 mm | Δ IoU 0.005 | 12.71 s | Defer production |
| D9 (4) | 2.97 mm | 4.48 mm | Δ IoU 0.061 | 2.48 s | Lab control |
| L0 (4) | 7.31 mm | 0.13 mm | Δ IoU 0.002 | 16.56 s | Defer production |

## independent MB-Lab · calibrated

| Configuration | Mean surface error | Improvement vs M7 | Held-out impact | Runtime | Decision |
| --- | --- | --- | --- | --- | --- |
| D0 (3) | 21.73 mm | 0.00 mm | Δ IoU 0.000 | 16.82 s | Retain |
| D1 (3) | 20.28 mm | 1.44 mm | Δ IoU 0.013 | 14.93 s | Lab control |
| D2 (3) | 21.03 mm | 0.69 mm | Δ IoU 0.008 | 15.04 s | Lab control |
| D3 (3) | 20.40 mm | 1.32 mm | Δ IoU 0.016 | 19.29 s | Lab control |
| D4 (3) | 21.90 mm | -0.17 mm | Δ IoU 0.001 | 18.10 s | Defer production |
| D5 (3) | 21.00 mm | 0.72 mm | Δ IoU 0.008 | 36.90 s | Defer production |
| D6 (3) | 21.39 mm | 0.34 mm | Δ IoU 0.009 | 44.42 s | Defer production |
| D7 (3) | 19.04 mm | 2.69 mm | Δ IoU 0.032 | 19.67 s | Defer production |
| D8 (3) | 21.39 mm | 0.34 mm | Δ IoU 0.009 | 44.84 s | Defer production |
| D9 (3) | 19.41 mm | 2.32 mm | Δ IoU 0.015 | 24.83 s | Lab control |
| L0 (3) | 21.73 mm | 0.00 mm | Δ IoU 0.000 | 17.10 s | Defer production |

## MakeHuman · estimated

| Configuration | Mean surface error | Improvement vs M7 | Held-out impact | Runtime | Decision |
| --- | --- | --- | --- | --- | --- |
| D0 (4) | 20.67 mm | 0.00 mm | Δ IoU 0.000 | 12.02 s | Retain |
| D1 (4) | 20.79 mm | -0.12 mm | Δ IoU 0.007 | 8.33 s | Lab control |
| D2 (4) | 20.46 mm | 0.21 mm | Δ IoU 0.001 | 10.48 s | Lab control |
| D3 (4) | 20.23 mm | 0.43 mm | Δ IoU 0.005 | 5.61 s | Lab control |
| D4 (4) | 21.97 mm | -1.31 mm | Δ IoU -0.007 | 5.74 s | Defer production |
| D5 (4) | 20.52 mm | 0.15 mm | Δ IoU 0.003 | 4.28 s | Defer production |
| D6 (4) | 19.85 mm | 0.81 mm | Δ IoU 0.009 | 4.31 s | Defer production |
| D9 (4) | 3.22 mm | 17.45 mm | Δ IoU 0.225 | 3.42 s | Lab control |

## independent MB-Lab · estimated

| Configuration | Mean surface error | Improvement vs M7 | Held-out impact | Runtime | Decision |
| --- | --- | --- | --- | --- | --- |
| D0 (3) | 26.14 mm | 0.00 mm | Δ IoU 0.000 | 11.23 s | Retain |
| D1 (3) | 27.70 mm | -1.56 mm | Δ IoU -0.014 | 4.32 s | Lab control |
| D2 (3) | 27.54 mm | -1.40 mm | Δ IoU -0.009 | 4.46 s | Lab control |
| D3 (3) | 27.48 mm | -1.35 mm | Δ IoU -0.010 | 4.48 s | Lab control |
| D4 (3) | 27.57 mm | -1.43 mm | Δ IoU -0.010 | 4.86 s | Defer production |
| D5 (3) | 27.23 mm | -1.10 mm | Δ IoU -0.008 | 4.27 s | Defer production |
| D6 (3) | 28.43 mm | -2.30 mm | Δ IoU -0.021 | 4.18 s | Defer production |
| D9 (3) | 20.94 mm | 5.19 mm | Δ IoU 0.039 | 4.07 s | Lab control |


## Findings

1. Exact depth had +0.82 mm median, best +3.14 mm (A_slim). Exact normals had +0.54 mm median, best +1.26 mm (B_female_expanded). Combining exact channels had +1.08 mm median, best +2.29 mm (B_female_expanded). The best observed gain represents a single subject under the frozen configuration.
2. Predicted depth had +0.11 mm median, best +2.72 mm (A_slim). Directly predicted normals had +0.68 mm median, best +1.24 mm (B_female_expanded). Predicted fusion had +0.25 mm median, best +1.42 mm (A_heldout_2). Compare held-out IoU and depth against the paired geometry result. D3 and D6 show joint performance, and D1 and D2 separate individual effects.
3. Both models executed offline on Linux CPU with pinned assets. Both models also ran on Windows Server 2022 CI. The physical Windows 11 i7-1355U workstation remains unmeasured.

## Remaining qualification

1. The ten authored fixtures cover two asset families and a small held-out cohort. Real photographs, consented scans, independent metric scale, and a broader set of camera and body poses remain open.
2. Camera registration and pose attribution can change the result materially. The supplied camera and pose controls isolate error sources. They leave automatic onboarding from arbitrary photos unresolved.
3. D7 and D8 examine a single restricted displacement family. Retained local candidates and rejected proposals are separated. Representative USD and Blender rig save/reopen checks passed. A full textured desktop export regression and broader human-specific normal-model evidence remain open.

See the anatomical region, multiview, registration and local-refinement reports for gains, regressions and exact coverage. Positive gain means lower error than D0. Runtime covers the measured fit, including registration for D0, and excludes predictor inference. Concurrent workload timings include contention.

- Paired depth retention over 7 calibrated held-out bodies. Exact mean gain +1.29 mm, predicted mean gain +0.15 mm. The ratio of the two mean gains is +12%.
- Paired normals retention over 7 calibrated held-out bodies. Exact mean gain +0.46 mm, predicted mean gain +0.36 mm. The ratio of the two mean gains is +77%.
- Paired combined retention over 7 calibrated held-out bodies. Exact mean gain +0.99 mm, predicted mean gain +0.27 mm. The ratio of the two mean gains is +27%.
- Exact fusion versus the best single oracle channel per body averages -0.44 mm over 7 paired bodies.
- Exact fusion regions with the greatest gains are upper back (+5.09 mm), gluteal (+4.32 mm), pelvis (+3.40 mm). The largest adverse regional changes are neck (-0.42 mm), calves (-0.48 mm), forearms (-1.05 mm).
- Oracle local refinement added +0.58 mm on average after the guards. 5/7 proposals were rejected. The tested local field has conditional value and does not establish necessity.
- Largest D3 penalty versus matched perturbed D0 was +0.50 mm under perspective-0/A_high_mass.
- Worst calibrated held-out predicted regression was 1.93 mm (A_adult_asymmetric, D5).

- Maximum calibrated gain for D1, including development cases, was +3.14 mm on A_slim.
- Maximum calibrated gain for D2, including development cases, was +1.54 mm on A_high_mass.
- Maximum calibrated gain for D3, including development cases, was +2.29 mm on B_female_expanded.
- Maximum calibrated gain for D7, including development cases, was +3.20 mm on B_male.
- Worst predicted result in the main estimated-camera matrix regressed 7.12 mm on A_adult_asymmetric (D4).
- Treating the loose shell as anatomy increased error from 4.51 to 8.53 mm. Excluding covered dense observations reduced it to 3.62 mm.

## Descriptive 95% mean-gain intervals

| Arm | Lower mm | Upper mm |
| --- | --- | --- |
| D1 | 0.64 | 2.07 |
| D2 | 0.00 | 0.91 |
| D3 | 0.47 | 1.51 |
| D4 | -0.66 | 1.12 |
| D5 | -0.45 | 0.89 |
| D6 | -0.35 | 0.81 |
| D7 | 0.79 | 2.35 |
| D8 | -0.33 | 0.83 |

The bootstrap resamples subjects and describes this small authored cohort. Population-level inference remains open.
