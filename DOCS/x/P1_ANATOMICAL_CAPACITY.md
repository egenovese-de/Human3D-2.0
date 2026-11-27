# P1 MakeHuman anatomical capacity inventory

Pinned [MakeHuman source](https://github.com/makehumancommunity/makehuman/tree/1f508f6083b2f823dab15de924b3bde72e08d77c). The checkout contains 1280 target files. Counts are asset files. Modifier dependencies and opposite directions can map multiple files to one user control.

| Family | Files |
|---|---:|
| armslegs | 140 |
| asym | 62 |
| bodyshapes | 22 |
| breast | 228 |
| buttocks | 2 |
| cheek | 16 |
| chin | 15 |
| ears | 44 |
| expression | 102 |
| eyebrows | 6 |
| eyes | 68 |
| forehead | 8 |
| genitals | 6 |
| head | 27 |
| hip | 14 |
| macrodetails | 348 |
| measure | 40 |
| mouth | 44 |
| neck | 16 |
| nose | 42 |
| pelvis | 4 |
| stomach | 8 |
| torso | 18 |

## Semantics and dependencies

| Region or control | Upstream mapping |
|---|---|
| Sex-related morphology and age | Macrodetails combines sex, age and population bases. Adult controls and child controls have different geometry. Head age provides a separate local adjustment. |
| Mass and muscle | Universal macrodetails endpoints combine sex, age, weight and muscle. Use endpoint differences against the matching average as an explicitly additive approximation. |
| Skeletal proportions | Macrodetails height and proportions plus local limb, torso, head and neck scales. Rebind skeletal joints after changing proportions. |
| Shoulder and pelvis | Torso and upper-arm fields overlap at the shoulder. Hip scale and translation plus pelvis tone affect the pelvic transition. |
| Breast and lateral chest | Breast cup and firmness are conditioned on age, sex, weight and muscle. Breast spacing and torso width or depth overlap spatially. |
| Abdomen and gluteal regions | Stomach tone and navel displacement plus buttocks volume and hip depth. Pregnancy is a distinct shape control. |
| Arms and legs | Side-specific scales and translations for proximal and distal limbs, hands and feet. Mirror pairs are related controls. |
| Head and face | Head shape and local eyes, ears, nose, mouth, chin, cheek, forehead and brow fields. Expression assets are tracked separately from identity. |
| Measurements | Measurement modifiers overlap local modeling controls. Circumference-driven controls can couple adjacent regions. |

The modifier definitions under upstream `makehuman/data/modifiers` define dependencies and pairings. Sparse displacement targets preserve base vertex indices, connectivity and UV indexing. Overlapping fields can be redundant or distort a region when combined. Rig compatibility requires rebinding and validation.

The Lab manifest admits 26 additional targets with byte lengths and SHA-256 digests computed from the pinned checkout. The data assets are credited to MakeHuman Community under CC0-1.0.
