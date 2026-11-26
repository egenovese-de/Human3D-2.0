# Q face, pose, texture and garment evidence

The [held-out follow-up](Q_HOLDOUT_FOLLOWUP.md) adds four preset identities, articulated fixtures and changed reference inputs. This report records the original pilot.

- Face: the independent surface measurements include a cranial band. The controlled jaw invariant yielded {'jaw_moved_vertices': 848, 'jaw_max_displacement_mm': 3.163499999999997, 'canonical_topology_uv_rig_unchanged': True, 'neutral_support_plane': -8.1676} at input control 0.5. This local-deformation test cannot establish facial landmark accuracy.
- Pose: 6 variants with 12 rig endpoint/direction proxies each. Pose intervention effect +6.61 across 6 variants (range +4.37 to +8.71) percentage points. Endpoint and direction errors are in the JSON. Different rig definitions limit positional interpretation, and no joint rotation truth was recorded.
- Skinning: 6 reports with per-case maximum absolute bone-length change and calibrated units. Measurements check mechanical consistency and do not establish contact or torsion accuracy.
- Texture: UV fractions use the same release coverage definition. Coverage is a count of observed UV texels, without a color, seam, or contamination accuracy claim.
- Garments: three native close-fitted shell prototypes per completed component case. Reports retain signed minimum sampled clearances, violations, changed sample counts and maximum pose motion. Sampled signed distances do not bound all geometric triangle intersections.
- Export: OpenUSD parsed the native USDZ packages and reported mesh and skeleton counts. It verified separate body and top meshes, UVs, skin indices and one inherited skeleton in each AI-input garment export. The host Blender build has no USD import operator. Official LTS archive fetch returned HTTP 403. No Blender edit/save/reopen verification is claimed.

## Follow-up component evidence

- Face. A 5×5 grid over head-width and jaw-width controls on 13 human-source subjects reduced cranial symmetric sampled error from mean 10.98 mm to 10.32 mm when selecting the best control pair with ground truth. Measurements are absolute height-aligned cranial and facial bands. Independent feature landmarks and expression controls remain open.
- Pose. Two independently skinned MB-Lab rigs yielded 14 cases and 224 mapped bone instances. Mean world rest-to-posed rotation change error was 27.82°, with near-zero numerical change in release bone lengths. The benchmark includes conventional correspondence caveats around the split native pelvis, spine chain and parent differences. Global and parent-relative errors distinguish axial orientation from segment direction.
- Evidence. Sampled geometric visibility reproduced the independent Blender alpha with mean IoU 99.10% and minimum 98.50% across 56 camera pairs. The visibility substitution removed some profile observations without changing mean tested bootstrap IoU. Yaw substitution raised mean IoU from 53.82% to 54.33% across 16 profile/frontal/seated configurations.
- Texture. Visible frontal RGB MAE was 1.80 levels/channel at baseline, 9.43 with an unmasked magenta occluder and 32.66 under a three-pixel shift. Masking the occluder removed the 341 sampled occluder-color assignments and left visible RGB MAE at 1.82. Observed chart-pair seam discontinuity increased from 0.66 levels/channel to 5.46 after the shift. Single-view hidden observations, coverage padding and unobserved defaults are reported separately.
- Garments. Eighteen native shell controls span top, shorts and trousers with variation in ease and hem. Four cases with zero sampled violation counts still had triangle overlap. Independent-pattern distances include underlying body and design mismatch. Hem-open meshes have no defensible enclosed volume in this protocol.
- Blender. Six release USDZ files passed direct import and edit/save/reopen. Four contain inner and outer top meshes with the body and separate bindings to one rig. In-scene pose editing moved garment vertices. Mesh digests verified that edits persisted and that garment removal did not change the body geometry. These layered controls use canonical native shells. Independent registration into their skin/UV contract remains open.

[Measurements and visual comparisons](Q_FOLLOWUP_COMPLETION.md)

## Contact and torsion detail

The calibrated raised-foot conditions had independent inter-foot clearances of 88.3 and 107.7 mm. The release estimates were 35.3 and 13.8 mm. For the seated control the independent left/right height difference was effectively zero, compared with 54.9 and 93.7 mm estimates. The ground-plane height is a release asset-placement convention. The articulated fixture records absolute calibrated sole elevations and separates geometric floor proximity from physical load or furniture contact.

Frontal controlled left-hand world rotation-change error was 112.0° and 114.5° in the torsion conditions. The corresponding lateral cases retained 24/33 observed landmarks each and reported 128.3° and 118.9° error. Forearm axial orientation and hand segment direction have distinct reference targets. Release wrists can apply bounded roll with observed finger anchors. The release forearm swing transform has no independent axial-roll parameter, so that component is an unsupported degree of freedom.

[Frontal contact and rotation](q/followup/rig-contact.json) · [Lateral contact and rotation](q/followup/rig-profile.json)

## Independent layered export and volume validation

A separate procedural two-layer input retained 576 vertices per layer after registration into the release's attachment contract. The female control exported after a repair with a peak 86.23 mm mesh displacement. The OpenUSD export preflight measured seven millimeters of sampled layer separation. Blender exposed the layers as separate editable objects with individually recorded weights and deformation responses. No exact collision-free guarantee follows from the sampled check. The male transfer remained blocked at four sampled penetrations in the inner layer. These results bound editability separately from fidelity of independent garment registration.

Volume requires a watertight, non-self-intersecting surface. The native shell test added triangle fans to directed hem loops, verified closed edge multiplicity and checked non-neighbor triangle self-intersection. All 18 native proxies failed the checked closure due to self-intersections. The two independent top patterns gave virtual envelope volumes of 32.66 L and 43.11 L. The silhouette garment's occupied material volume and the native cap volumes remain unresolved.

[Independent layer attempts](q/followup/independent-layer-export.json) · [Blender import measurements](q/followup/independent-blender-roundtrip.json) · [Direct import visual comparison](q/followup/layered-atlas.png)

## Controlled facial profile and expressions

Two independently generated identity meshes were evaluated in seven states each. Pinned MB-Lab expression targets supplied wide jaw opening, smile and unilateral cheek changes. Additional profiles used two paired cranial-width/depth perturbations and a localized 18 mm nominal forward displacement centered on the independent nostril-morph support. Peak achieved shape displacement was 40.9 mm at wide opening and 17.3–17.5 mm for the nasal target. The oracle grid reused the same 25 released head-width/jaw-width pairs in every state. Best sample averages ranged from 6.81 to 8.56 mm under the head-band metric. Whole-head symmetric distance can improve when a changed target happens to approach the release base, including a larger jaw opening. The results do not establish expression accuracy. There are no released independent depth, nose, cheek or articulation controls in this diagnostic.

[Controlled facial profile measurements](q/followup/face-variations.json)
