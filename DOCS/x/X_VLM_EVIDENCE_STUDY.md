# Human3D 2.0 — P3 visual evidence study

## Protocol

Four synthetic subjects were rendered in Blender Cycles from front, side and three-quarter camera positions. The exact [front](../../lab/fixtures/x-vlm/front.jpg), [side](../../lab/fixtures/x-vlm/side.jpg) and [three-quarter](../../lab/fixtures/x-vlm/threequarter.jpg) sheets and their hashes are retained. The anatomy uses the independently parameterized P1 spatial warps on the shared MakeHuman mesh topology. Subject identifiers hide the deformation coefficients from the visual prompt. Inputs to the prompts consist of rendered sheets and field definitions. An isolated inference process with no previous conversation context was unavailable.

The ChatGPT model executed two interactive visual passes and recorded the outputs as JSON before scoring. CI validates and replays these records offline. The [unified prompt](../../lab/fixtures/x-vlm/prompt-unified.txt), [specialized prompt](../../lab/fixtures/x-vlm/prompt-specialized.txt), [strict structural schema](../../lab/fixtures/x-vlm/evidence.schema.json), [unified raw rows](../../lab/fixtures/x-vlm/unified.raw.json) and [specialized raw rows](../../lab/fixtures/x-vlm/specialized.raw.json) are checked into the repository. The A–E observations share one unified visual pass. The separate specialized pass was executed in the same conversation. This design measures contract sensitivity under fixed visual evidence and gives only an exploratory comparison of prompt specialization.

| Mode | Evidence | Geometry mapping |
|---|---|---|
| A | Three-class waist-to-hip ratio | Maps to a representative ratio with coarse confidence weighting |
| B | Five-step ratio ordinal | Maps to an ordinal bin representative |
| C | Quantitative waist-to-hip ratio and interval | Fits the ratio constraint with interval half-width scaling |
| D | Quantitative ratio with ordinal fallback | Prefers available quantitative evidence and falls back to the ordinal ratio |
| E | Two projected cross-sections with intervals | Fits direct normalized widths and depths |
| S | E fields from the separate specialist prompt | Same geometry consumer and weights as E |

All observations use anatomically fixed fractional heights. The front sheet provides widths. Side upper depth is occluded by the arm in all four subjects in this set. The side sheet contributes hip depth under E or S. The three-quarter view produces no direct orthogonal constraints in this protocol. Fused evidence is keyed by subject and axis, with a null supplying no residual. Observations map into a regularized bounded fit over the same seven admitted MakeHuman fields. The oracle geometry is used for scoring after recording the observations. Absolute error is averaged within each configuration, with each configuration measuring its own ratio or extent fields.

## Numerical results

Mean canonical error is paired by vertex on the synthetic topology, in millimetres. Interval hits are compared with geometry-derived values. This sample does not support probabilistic calibration.

| Mode | Selection, fused mm | Held-out front mm | Held-out fused mm | Held-out fields | Field MAE | Interval hits |
|---|---:|---:|---:|---:|---:|---:|
| A | 18.62 | 30.11 | 30.11 | 2 | 0.078 | — |
| B | 18.31 | 29.36 | 29.36 | 2 | 0.071 | — |
| C | 17.74 | 28.53 | 28.53 | 2 | 0.081 | 1/2 |
| D | 18.68 | 28.52 | 28.52 | 2 | 0.081 | 1/2 |
| E | 15.86 | 25.72 | 25.70 | 6 | 0.015 | 4/6 |
| S | 16.44 | 25.60 | 25.58 | 6 | 0.012 | 5/6 |

E was selected on subjects 01 and 02 before ranking on 03 and 04. S scored slightly better on the held-out pair, so the result does not establish whether a unified or specialist prompt generalizes better. The additional usable side depth improved E by about 0.02 mm on the pair. Duplicate replay counts of 1, 2, 4, 8, 15 and 30 test whether repeating exact observations changes anatomy. With the same usable evidence, it did not. The benchmark contains three distinct views per subject. Convergence with 4–30 distinct, diverse references and conflict resolution across competing observations remain open.

Recommend E as the initial experimental contract. Its geometry carries more usable constraints than scalar ratios in this set, and the fitted results can be audited against region and visibility. The pilot does not show that the measurements are reliable enough to replace the native silhouette fitter. See the [distillation specification](X_VLM_DISTILLATION_SPEC.md) and [P4 results](X_P4_QUALIFICATION.md).

## Separate reference-count and quality control

A local deterministic experiment rendered 30 distinct rasterized silhouettes per subject and condition. The 360 observations cover same-axis views, complementary orthogonal views, and complementary views with injected segmentation bleed. The sweep varies camera scale and screen translation and alternates the projection direction within each axis. It aggregates section measures with a per-field median. This experiment measures the reconstruction effect of reference count under a calibrated geometric extractor. It is separate from the GPT replay.

| Distinct references | Same axis | Complementary clean | Complementary degraded |
|---:|---:|---:|---:|
| 1 | 25.46 | 25.46 | 25.46 |
| 2 | 25.47 | 25.51 | 25.53 |
| 4 | 25.40 | 25.45 | 25.18 |
| 8 | 25.43 | 25.48 | 25.18 |
| 15 | 25.53 | 25.44 | 25.01 |
| 30 | 25.40 | 25.40 | 24.97 |

Numbers are held-out mean canonical error in millimetres. Error stays near a plateau despite additional views. The degraded series happens to have the lowest canonical mean at 30 inputs on this pair. A segmentation bias can offset model or projection bias on individual cases. This limited result gives no basis to prefer degraded masks. The [raw sweep](p3-reference-sweep.json) preserves each input projection hash and observation.

The [qualified P3/P4 execution](https://github.com/egenovese-de/Human3D-2.0/actions/runs/46013006743) verified all 24 original response records, 72 normalized subject/view/method records and 48 fit results. [Raw measurements and provenance](p3-p4-evidence.json) preserve the source hashes, interval outcomes, regional distances and verification inventory.
