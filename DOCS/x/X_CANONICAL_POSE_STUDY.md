# Human3D 2.0 — P2 canonical pose study

## Recommendation

Keep anatomical morphs and their joint rebind in native space. Use A-pose as the first posed editing candidate when a canonical view is required. Keep X-pose as a comparison candidate for tasks that specifically need greater limb separation. On the tested MakeHuman meshes, A-pose introduces less neutral-surface area distortion than X or T. This study does not establish that A offers the best access for detailed anatomical editing.

The native-first path remains the reference for reproducing native anatomy under articulation. A fixed-transform morph field can be transported exactly under linear blend skinning. If anatomy changes the joint locations, a canonical editor must also update pose transforms to reproduce the native-first result.

## Experiment design

The benchmark uses the checked-in P1 asset manifests, the pinned application rig and the same MakeHuman topology, weights and UVs across routes. Three bounded edits exercise upper-body, lower-body and combined shape changes. There are four neutral controls and 36 edited states. The pose labels use measured upper-arm and upper-leg angles from vertical in the frontal plane.

| Pose | Upper arm | Upper leg |
|---|---:|---:|
| Native | 38.46° | 1.55° |
| A | 35° | 12° |
| T | 90° | 12° |
| X | 50° | 23° |

| Route | Operation | Implementation implications |
|---|---|---|
| A | Apply morphology natively, rebind joints, solve the target pose and skin. | Reuses native rebind and skinning. A pose-space editor needs a mapping back to native controls if it uses this route. |
| B | Pose the neutral mesh, then directly add regional offsets expressed in each vertex's dominant-bone frame. | One rotation per displacement. The control may change discontinuously at dominant-bone boundaries. This is a controlled direct-edit proxy using common offsets, with no fitted pose-space sculpt. |
| C | Pose the neutral mesh, then transport the native displacement with the full weighted rotations. | Shares the existing weights and avoids a hard dominant-bone change. Exact for the original pose transforms. Matching an updated rig requires tracking the joint and transform changes as well. |

Route A defines the synthetic comparison reference for numerical equivalence. Its zero reference distance follows from that definition. Regional metrics use overlapping native-coordinate masks for axilla, shoulder, upper arm, lateral chest, breast, pelvis, inguinal region, inner thigh and gluteal region. The same vertex sets follow the deformation in each pose. Pose-local distortion is candidate triangle area divided by neutral area in that pose. Neutral-pose distortion compares the posed neutral triangles to the native neutral triangles, excluding triangles with reference double-area at or below 1e-6. Because face UV indices and coordinates are identical, the surface-area change also indicates UV area stretch relative to the reference. Isotropic area ratios do not capture anisotropic UV distortion.

The Blender BVH counts unique intersecting triangle pairs after removing any pair with a shared vertex. Crossing and separated triangle controls run before analysis. The metric excludes contacts between faces with shared vertices and does not establish robustness at other poses or larger shape changes. Locator comparisons use re-bound vertex locators versus A in the same pose. No motion capture or photographic ground truth enters the benchmark.

## Results

The global mean averages the three edits per route. P95, maximum error and maximum joint-locator error show the worst edit per route. All distances are millimetres.

| Pose | Route | Mean | P95 | Max | Joint max | Intersection pairs, max |
|---|---|---:|---:|---:|---:|---:|
| Native | A/B/C | 0.00 | 0.00 | 0.00 | 0.00 | 0 |
| A | A | 0.00 | 0.00 | 0.00 | 0.00 | 0 |
| A | B | 5.11 | 23.19 | 23.25 | 23.24 | 0 |
| A | C | 5.11 | 23.19 | 23.25 | 23.24 | 0 |
| T | A | 0.00 | 0.00 | 0.00 | 0.00 | 0 |
| T | B | 5.39 | 23.95 | 24.28 | 24.05 | 0 |
| T | C | 5.38 | 23.94 | 24.28 | 24.05 | 0 |
| X | A | 0.00 | 0.00 | 0.00 | 0.00 | 0 |
| X | B | 5.28 | 23.28 | 23.41 | 23.29 | 0 |
| X | C | 5.28 | 23.28 | 23.30 | 23.29 | 0 |

| Neutral pose vs native | Triangle area ratio P01 | Triangle area ratio P99 | Stable triangles outside 0.5–2× |
|---|---:|---:|---:|
| Native | 1.000 | 1.000 | 0 |
| A | 0.910 | 1.225 | 18 |
| T | 0.833 | 1.396 | 54 |
| X | 0.887 | 1.364 | 44 |

All 36 edits pass native rebind and pose validation. The 40 meshes share 13,380 body vertices, 26,756 triangles and 53,512 UV corners. No nonadjacent triangle intersections were detected. Fixed-transform C agrees with native-first fixed-transform LBS within floating-point precision. Under dynamic rebind, the 23–24 mm maximum error persists in both B and C. This is sufficient to reject treating transported fields with a frozen rig as equivalent to the native-first pipeline for these cases.

The trial covers additive MakeHuman controls on one base anatomy. It does not establish performance on independently authored pose-space sculpts, human subjects, clothing, strong articulation, or photographic evidence. Runtime fields describe route evaluation with precomputed asset and route setup. They do not measure end-to-end editing latency.

In the combined X-pose edit with C, mean regional error was 1.50 mm in the axilla, 5.51 mm at the upper arm and 3.67 mm at the inner thigh. The maximum skin-weight normalization error was 3.33e-16. The fixed-transform identity had a worst error of 3.56e-13 mm.

## Qualification

[Run 46011201520, job 140546859715](https://github.com/egenovese-de/Human3D-2.0/actions/runs/46011201520/job/140546859715) completed the benchmark, Blender intersection controls and default-deny artifact admission on Lab revision `657a09d5bbb682ac0d395ab5c02e49c46e95366b`, with application source `e0ae4eae57347466b5757bbcdaaa7194bdd31c94`. The [qualified artifact](https://github.com/egenovese-de/Human3D-2.0/actions/runs/46011201520/artifacts/15203842500) contains actual meshes, UV mappings, raw measurements and logs-derived provenance. The downloaded ZIP digest matched GitHub's SHA-256, and all nine staged files passed offline inventory verification. The log records the unauthorized-file rejection control. [Machine-readable evidence](p2-canonical-evidence.json) preserves the numerical results and file digests beyond artifact expiry. X-011 and X-012 are complete within the experimental scope.
