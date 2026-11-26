# Lateral review and degradation

Four preset identities yielded 132 detector evaluations. The frontal baseline passed review in 4/4. The eight clean profiles each had one detection and review reason `insufficient_full_body_evidence`. The release tests candidate anchor observations at 0.8 for visibility and presence. Far-side knees and ankles account for the recorded profile gate. Mask IoU remained approximately 98%. A missing full-body review anchor can coexist with enough torso points for an alignment and with accurate segmentation. The release can score its posed bootstrap on these cases even though review is required.

| Treatment | First tested decrease in single-candidate yield | First tested complete candidate loss | Other observation |
|---|---|---|---|
| Gaussian blur | radius 4 px, 2/4 | 6 px, 0/4 | Radius 2 passed 4/4 |
| JPEG quality | quality 3, 0/4 | quality 3 | Quality 8 passed 4/4 |
| RGB Gaussian noise | σ40 levels, 1/4 | σ64 | The remaining candidate at σ40 still required review |
| Vertical crop from each edge | None through 64 px | None through 64 px | 64 px gave 4/4 candidates and 0/4 clean reviews |
| Compound blur, noise, JPEG | radius 6 px, 0/4 | 6 px | At radius 4, all masks/detections were still available and 2/4 required review |

Compound levels use blur radius r, noise σ=3r and JPEG quality max(5, 80−6r). Detector and alignment errors, posture silhouette IoU, mask IoU and elapsed time are recorded per observation. The thresholds bracket transitions at 384 px under these fixtures. The design covers two human topology families and does not support population failure estimates.

[Per-case records](q/followup/detector.json)
