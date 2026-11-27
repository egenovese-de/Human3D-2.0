# M6 geometry and texture checkpoint

## Geometry

The alternative-base replay measured a symmetric mean residual of 29.76 mm on the height-aligned bootstrap over four Q identities. The tested female MakeHuman target raised that mean to 30.95 mm. The male target lowered the mean to 27.81 mm, with gains on the two male presets and regressions on both female presets. These are development controls from one source family. The mixed result leaves automatic base selection unqualified.

The target-switch replay copied four stored Q projects with four views each, visited every target, and returned to the initial target. All 20 observations retained identical frozen-body, shared-fit, shared-evidence and neutral-vertex hashes within each project. Target camera yaw varied.

## Texture

Body atlas results now expose per-view silhouette IoU, projected area outside the observed mask, unprojected mask area, symmetric p95 contour distance in source pixels, and observed UV coverage. The enlarged diagnostics leave texture sampling and view weights as before.

On one independently ray-rendered analytic texture fixture, shifting RGB alone by 0, 1 and 3 px gave visible RGB MAE of 1.80, 13.14 and 32.66 respectively while coverage stayed at 44.46%. The contour diagnostic stayed at 0 px for these color-only shifts. Shifting the camera instead gave 1 and 3 px contour residuals and reduced coverage to 41.18% and 36.14%. Masking the synthetic occluder removed all 341 contaminant-colored samples and reduced coverage from 44.46% to 39.55%. The per-case file includes the seam and hidden-surface measurements. These controls support diagnosis with both contour and photometric evidence. No automatic exclusion threshold is qualified by this fixture.

The [pinned Lab replay files](https://github.com/egenovese-de/Human3D-2.0/tree/53f825cc86c202541a9addb80bbbe17c0a8c00ea/DOCS/m6) contain per-identity geometry results, target revision hashes and texture diagnostics.
