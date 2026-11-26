# Q dataset and asset provenance

The [held-out follow-up](Q_HOLDOUT_FOLLOWUP.md) adds four preset identities, articulated fixtures and changed reference inputs. This report records the original pilot.

6 metric fixtures from two independently sourced MB-Lab base meshes, each rendered in base, wider torso and bent/asymmetric torso variants. The meshes are more than independent morph coefficients in the Human3D basis. They come from the MB-Lab [pinned upstream](https://github.com/animate1978/MB-Lab/tree/063bff04e60f3e7c651fda628c30f5d83f3f3078), whose [license](https://github.com/animate1978/MB-Lab/blob/063bff04e60f3e7c651fda628c30f5d83f3f3078/license.txt) specifies AGPL-3.0 for the database and separate terms for non-reverse-engineering 2D renders. No MB-Lab meshes, joint databases, UV data, depth/surface rasters or raw datasets are redistributed here. Floor-normalized source geometry is never inferred from an AI photo. The Blender coordinate system is X lateral, negative Y frontal, Z up. Camera extrinsics are camera-to-world. For the orthographic baseline, the scale spans 2.16 m across 384 pixels.

The controlled set has 60 baseline orthographic renders, 16 supplemental orthographic renders, 24 perspective renders and 84 different stress inputs including the perspective composites. Each base mesh includes eight train and two held-out camera azimuths. The camera check compared independently projected polygon masks to Blender alpha on 60 images. The source material is a documented uniform display color. Joint anchors are calculated from pinned MB-Lab rig vertex groups and offsets. Blender BVH pass records first visible polygon and camera-depth grids locally. Hashes, transformations, seed references and camera records are in [manifest.json](q/manifest.json). Recorded camera distances and axes are metric. No experimental dataset row comes from personal photos.

Two generated photographic fixtures represent separate fictional adults and provide detector and fitting stress cases without calibrated mesh, camera or identity correspondence. Pilot scale was chosen to validate the native and calibrated experiments before larger coverage. There are no independent subject-family test folds, animated-pose series or calibrated garments in this pilot.

## Q follow-up expansion

Expanded the pinned MB-Lab source to 17 preset source geometries. Thirteen use the human male/female topology and four use the stylized male/female topology. Stylized cases are exploratory and excluded from the independent adult face benchmark. The four original holdout presets are included in the 17. Including the two historical base geometries gives 15 human-source bodies and four exploratory stylized sources. Variants and poses are nested within source identity. The approximately 24 independent adult identity goal remains unmet. All four topologies share one mesh source project.

The expanded dataset has 29 rig fixtures and 86 calibrated Blender renders. Two selected presets have an independent FK armature, five articulated states, a neutral reference and a separate anatomical asymmetry control. Rotation inputs, rest/pose matrices, fixed camera projections and per-file SHA-256 were recorded locally. Published hashes and scripted controls permit verification without redistributing surfaces, rig data or raw image collections.

The independent garments are procedurally generated open ring meshes. The separate body-only, garment-only and composite masks share camera and underlying subject. Exact native texture correspondence is a separate Lab control on the released topology with analytic colors and independent Blender ray rendering. No generated case uses personal photographs.

[Fixture provenance and hashes](q/followup/fixture-index.json)
