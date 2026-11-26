# Q follow-up — held-out anatomy and controlled articulation

Release `480195f05fb2d1ed6c71dceabf4ba54b8bed69db`. Q retains its original pilot report. This follow-up adds four author-supplied MB-Lab preset geometries excluded from the pilot, two per topology family. The four geometries are independent of the release MakeHuman basis. They share the two MB-Lab topology families with the pilot, so this is an identity holdout rather than a new asset-source holdout. Each identity has a neutral render and one procedural left forearm bend. No held-out azimuth entered the fits.

12/12 native identity/pose runs completed. 4/4 substitution runs completed. Blender rendered and independently validated 80 camera/mask pairs. The local release suite ran 69/69 tests successfully.

## Neutral geometry and forearm pose

| Identity | Bootstrap held-out IoU | Four-view neutral IoU | Four-view surface distance (mm) | Chest section error (mm) | True bend | Neutral direction error | Articulated direction error | Bend fixture pose substitution |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| f_af01 | 75.24% | 72.09% | 26.4 | -66 | 31.55° | 8.95° | 6.40° | +4.04 pp |
| f_ca01 | 75.12% | 72.46% | 26.5 | -39 | 31.55° | 8.41° | 5.61° | +3.83 pp |
| m_as01 | 70.94% | 70.94% | 32.5 | -90 | 31.51° | 7.66° | 7.24° | +5.16 pp |
| m_la01 | 70.71% | 70.71% | 34.6 | -92 | 31.53° | 9.08° | 8.87° | +3.91 pp |

Four-view neutral shape changed held-out IoU by -1.45 pp on average relative to the height-aligned bootstrap. The chest result is a fixed horizontal section at 71% of body height. It measures perimeter, which can miss a local profile discrepancy. Shape errors mix morphology and residual rig and stance alignment.

The exact direction of the left forearm is derived from transformed joint anchors. The last column substitutes proxy directions for all supported limbs on the articulated fixture with native shape fixed. It measures the difference on the frontal mask with calibrated evaluation. Mean change +4.24 pp, range +3.83 to +5.16 pp. This benchmark covers flexion of one forearm. It leaves joint roll, hands, foot contact and dynamic pose outside the experiment.

## Changed reference photographs

| Identity | Configuration | Views used | Held-out neutral IoU | Change vs matched | Unresolved evidence |
|---|---|---:|---:|---:|---|
| f_af01 | matched | 4 | 72.09% | +0.00 pp | None |
| f_af01 | different-pose | 4 | 75.24% | +3.15 pp | None |
| f_af01 | contradictory | 4 | 75.24% | +3.15 pp | None |
| m_la01 | matched | 4 | 70.71% | +0.00 pp | None |
| m_la01 | different-pose | 4 | 70.45% | -0.27 pp | None |
| m_la01 | contradictory | 4 | 70.25% | -0.46 pp | None |

For each selected identity, only the 90° reference is replaced. The comparators use either the articulated version of the same identity or the neutral version of a different identity from the same topology family. The front target, other two inputs and held-out views are unchanged. This complements the duplicate-front sweep in the original pilot. Results are descriptive on two identities.

## Reproduction and artifacts

1. Use the release dependency lock, verified runtime assets and pinned MB-Lab revision documented by the original Q reproducibility manifest.
2. Run `render.py` with the MB-Lab library, output folder and optional MB-Lab checkout path, then `photographic.py` and `validate.py`. The held-out manifestations record hashes for every source preset, image and geometry.
3. Use the native benchmark with one view on each fixture and four views only on neutral fixtures. Call `mixed_references.py create` to prepare treatments, repeat the native four-view benchmark, then run `mixed_references.py score`.
4. Run `pose.py`, `holdout_report.py`, the Blender comparison script, and `holdout_atlas.py`. The two raw geometry packs stay local.

- [Machine-readable measurements and hashes](q/holdout_measurements.json)
- [Matched Blender render atlas](q/holdout_atlas.png)
