# G5 evidence quality

Results are medians over per-image measurements. Ground-truth inverse alignment for quality uses one third of valid pixels per view and scores the remaining pixels. This pixel split is spatially interleaved and is an optimistic scale-ambiguity control. The fit uses a different alignment with zero reference geometry input to prediction. Positive larger disparity means closer. Exact Z is in centimeters; Euclidean ray length differs away from the principal point.

| View | N | Affine depth MAE mm | Scale-only MAE mm | Rank ρ | Exact depth-derived ° | Predicted depth-derived ° | DSINE vs derived ° | DSINE median ° | DSINE boundary ° |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Front | 10 | 25.46 | 202.76 | 0.52 | 2.21 | 20.17 | 15.21 | 12.80 | 14.42 |
| Left lateral | 10 | 83.77 | 284.60 | 0.26 | 2.55 | 21.39 | 20.00 | 12.40 | 12.29 |
| Rear | 10 | 20.87 | 261.77 | 0.56 | 2.13 | 18.48 | 15.29 | 11.22 | 10.73 |
| Right lateral | 10 | 82.83 | 232.59 | 0.29 | 2.58 | 19.62 | 21.09 | 12.16 | 12.53 |
| Oblique | 40 | 42.15 | 301.91 | 0.84 | 2.31 | 16.27 | 14.64 | 13.35 | 13.53 |
| Alternate | 20 | 49.20 | 237.10 | 0.40 | 2.49 | 20.26 | 15.63 | 13.69 | 14.12 |

Reduced input resolution, appearance variation and RGB-to-raster agreement are in the quality JSON. The exact depth-derived residual quantifies the screen-space finite-difference floor.

## Blender appearance perturbations

An independent high-mass RGB series uses a close patterned torso shell, a loose shell, an occluding panel and striped background props. Separate masks score the visible altered surface and underlying body. The affine depth transform is estimated against the visible surface. This isolates appearance and surface-attribution errors without estimating real-world metric scale.

| Condition | Yaw ° | Evaluation support | Pixels | Depth MAE mm | Median normal error ° |
| --- | --- | --- | --- | --- | --- |
| close_garment | 0 | visible_surface | 8700 | 30.68 | 13.85 |
| close_garment | 0 | covered_visible | 4027 | 29.07 | 16.30 |
| close_garment | 0 | covered_body | 3925 | 24.61 | 12.75 |
| close_garment | 0 | exposed_body | 4673 | 32.08 | 11.95 |
| close_garment | 90 | visible_surface | 5678 | 69.96 | 12.59 |
| close_garment | 90 | covered_visible | 2127 | 53.69 | 10.47 |
| close_garment | 90 | covered_body | 1882 | 60.36 | 10.91 |
| close_garment | 90 | exposed_body | 3544 | 79.36 | 13.81 |
| control_studio | 0 | visible_surface | 8611 | 26.01 | 12.21 |
| control_studio | 0 | exposed_body | 8611 | 26.01 | 12.21 |
| control_studio | 90 | visible_surface | 5427 | 72.99 | 13.68 |
| control_studio | 90 | exposed_body | 5427 | 72.99 | 13.68 |
| external_panel | 0 | visible_surface | 11079 | 167.16 | 8.70 |
| external_panel | 0 | covered_visible | 4992 | 154.04 | 7.37 |
| external_panel | 0 | covered_body | 2524 | 322.71 | 35.10 |
| external_panel | 0 | exposed_body | 6087 | 177.92 | 11.61 |
| external_panel | 90 | visible_surface | 5427 | 73.48 | 13.98 |
| external_panel | 90 | exposed_body | 5427 | 73.48 | 13.98 |
| loose_garment | 0 | visible_surface | 8947 | 42.95 | 13.74 |
| loose_garment | 0 | covered_visible | 4311 | 40.24 | 16.84 |
| loose_garment | 0 | covered_body | 3917 | 27.90 | 14.50 |
| loose_garment | 0 | exposed_body | 4636 | 45.46 | 11.47 |
| loose_garment | 90 | visible_surface | 6358 | 61.05 | 13.73 |
| loose_garment | 90 | covered_visible | 2890 | 51.22 | 13.62 |
| loose_garment | 90 | covered_body | 1971 | 80.65 | 19.92 |
| loose_garment | 90 | exposed_body | 3453 | 68.54 | 13.76 |
| striped_background | 0 | visible_surface | 8611 | 25.24 | 11.99 |
| striped_background | 0 | exposed_body | 8611 | 25.24 | 11.99 |
| striped_background | 90 | visible_surface | 5427 | 73.66 | 13.59 |
| striped_background | 90 | exposed_body | 5427 | 73.66 | 13.59 |

## Reduced-resolution development controls

| Model | Reduced input px | Paired images | Mean full input error | Mean reduced input error | Metric |
| --- | --- | --- | --- | --- | --- |
| depth | 280 | 6 | 56.25 | 64.11 | affine_inverse_pixel_mae_mm |
| normal | 256 | 6 | 13.30 | 14.41 | median_deg |
