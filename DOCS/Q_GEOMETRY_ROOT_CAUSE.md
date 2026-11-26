# Geometry root-cause isolation

The four prior neutral holdout identities retain a fixed floor and height mapping. Region summaries use head, torso/arms and lower-body height bands. For the stance intervention, release skinning maps independently known segment directions onto native bootstrap joint locations, then freezes the transforms across morph conditions. This controls a large part of rest-stance mismatch while retaining residual joint correspondence and roll error.

| Condition | Mean symmetric sampled surface error, four identities |
|---|---:|
| Original bootstrap | 29.76 mm |
| Stance-registered bootstrap | 23.40 mm |
| Native photographic four-view fit | 30.30 mm |
| Native fit with the same stance registration | 23.48 mm |
| Registered, one-sided 3D objective | 22.98 mm |
| Registered, symmetric 3D objective | 22.82 mm |
| Registered, symmetric 3D objective from native seed | 23.10 mm |

The largest measured intervention is stance registration at 6.36 mm. From the registered bootstrap, the symmetric objective improved the mean by 0.58 mm. Initialization changed the mean by 0.28 mm under the schedules tested. The remaining surface gap includes representation, unmodeled correspondence, morph bounds and sampling. These experiments cannot isolate a numerical representation floor.

The direct objectives used fixed seeds, 2,200 area samples and the release ±0.5 bound and regularizer. Evaluation uses a different seed and 12,000 samples per surface. Per-step objective curves, p95 and regional directional means are published. The calibrated photographic comparison uses four untouched raster training silhouettes and two held-out azimuths. Its four-view scores retain the original rest stance. The bounded independent geometry transfer uses a separate topology registration diagnostic and does not change the release basis.

[Direct-fit records](q/followup/geometry.json) · [Calibrated photographic fit](q/followup/calibrated.json) · [Geometry transfer](q/followup/transfer.json)

The calibrated four-view variant averaged 28.22 mm symmetric sampled surface error and 74.26% held-out silhouette IoU across the four identities. Its observations replace both camera and silhouette and therefore measure the joint input intervention. Native and calibrated errors use the same 12,000-sample evaluation.

Two upstream MakeHuman adult targets were applied to the existing canonical vertex order, checked with release rebinding and evaluated with a separate height-aligned comparison. On the two male holdout identities, the tested male adult target reduced error from 32.66 to 27.83 mm and from 35.00 to 29.91 mm. On both female holdout identities, the corresponding female adult target increased error. This result motivates a broader matched base-shape experiment with sex and shape assignment fixed independently of evaluation.

[Alternate canonical bases and asset digests](q/followup/alternate-base.json)
