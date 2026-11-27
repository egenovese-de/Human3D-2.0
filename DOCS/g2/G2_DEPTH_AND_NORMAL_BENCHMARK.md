# Relative depth and surface normals

Depth Anything V2 Small ONNX ran on CPU with 392×392 RGB inputs. Evaluation fits a nonnegative affine map in inverse depth on one third of an eroded visible body mask, then tests the remainder. It uses Blender-matched geometric depth in that calibration control only. E6 refits a separate relative scale and shift from candidate geometry at each iteration. It does not receive reference depth. A constant-plane baseline and a metric depth oracle define the extraction baseline and a downstream control.

| Family and case | Front depth MAE mm | Side MAE mm | Front normals median ° | Side normals median ° | Silhouette control mm | Predicted depth fit mm | Oracle depth fit mm |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A_adult_asymmetric | 17.99 | 64.50 | 15.16 | 18.29 | 7.82 | 5.00 | 7.57 |
| A_heldout_1 | 17.17 | 56.45 | 16.71 | 17.50 | 6.59 | 7.02 | 5.51 |
| A_high_mass | 17.21 | 51.10 | 16.20 | 17.40 | 2.93 | 3.92 | 2.49 |
| B_female | 22.04 | 98.37 | 21.13 | 19.15 | 20.61 | 20.72 | 20.62 |

The normal proxy differentiates scale-aligned predicted depth in a calibrated orthographic camera. It uses no specialized normal model. The oracle gradient control quantifies raster/mesh angular error. Regional distributions, depth ordering, runtime, occlusion/background/lighting variants and extracted maps are retained. Side-depth errors are larger than most frontal errors. Depth improves one tested A case and worsens others despite an available pixel-wise signal. Neither relative depth nor derived normals qualify for default fitting. Specialized normal inference and a separate normal fitting ablation remain open.
