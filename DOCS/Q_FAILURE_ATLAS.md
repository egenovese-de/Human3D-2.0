# Q Blender comparative renders and failure atlas

The [held-out follow-up](Q_HOLDOUT_FOLLOWUP.md) adds four preset identities, articulated fixtures and changed reference inputs. This report records the original pilot.

- [MBLab_human_female_asymmetric](q/MBLab_human_female_asymmetric.png)
- [MBLab_human_male_base](q/MBLab_human_male_base.png)
- [Native wireframe, distance colors and baked UV texture](q/diagnostics.png)

Rows use actual Workbench renders with matched orthographic framing, height alignment, studio shading and camera azimuth. Ground truth, native neutral, calibrated four-view neutral and bounded direct 3D fits are followed by a raster overlay. Cyan marks missed truth and orange marks predicted excess. The pilot presentations are neutral meshes; the residual includes stance and rig-family differences. The supplementary male case includes wireframe, native texture and a nearest-reference-vertex distance map. Blue is near zero and red is at or above 120 mm. The map is directional and sensitive to stance and tessellation. Radiometric texture comparison and garment-intersection visuals remain unavailable.

Historical report reproduces a near-basis calibrated control case with 99.6724% held-out IoU. The independent fixture images reveal differences around arms, profile and torso under common alignment. Per-variant JSON permits selection by lowest held-out IoU and largest surface error, including cases outside this visual sample.

## Follow-up visual and measurement evidence

- [Independent pose versus native reconstructed posture](q/followup/articulation-atlas.png) compares matched Blender cameras for spine/pelvis flexion and sitting on two subjects.
- [Lateral review and degradation cases](q/followup/detector.json) retain individual errors and review reasons, including usable segmentation after failed landmark review.
- [Garment triangle checks](q/followup/garment-collision.json) retain sampled-pass cases with geometric surface intersections.
- [UV contamination and registration stress](q/followup/texture.json) separate oracle-gated occlusion, geometric visibility, cross-region colors and texel padding.
