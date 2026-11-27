# M6 geometry and texture checkpoint

## Geometry

The alternative-base replay measured a symmetric mean residual of 29.76 mm on the height-aligned bootstrap over four Q identities. The tested female MakeHuman target raised that mean to 30.95 mm. The male target lowered the mean to 27.81 mm, with gains on the two male presets and regressions on both female presets. These are development controls from one source family. The mixed result leaves automatic base selection unqualified.

The target-switch replay copied four stored Q projects with four views each, visited every target, and returned to the initial target. All 20 observations retained identical frozen-body, shared-fit, shared-evidence and neutral-vertex hashes within each project. Target camera yaw varied.

## Texture

Body atlas results now expose per-view silhouette IoU, projected area outside the observed mask, unprojected mask area, symmetric p95 contour distance in source pixels, and observed UV coverage. The enlarged diagnostics leave texture sampling and view weights as before.

On one independently ray-rendered analytic texture fixture, shifting RGB alone by 0, 1 and 3 px gave visible RGB MAE of 1.80, 13.14 and 32.66 respectively while coverage stayed at 44.46%. The contour diagnostic stayed at 0 px for these color-only shifts. Shifting the camera instead gave 1 and 3 px contour residuals and reduced coverage to 41.18% and 36.14%. Masking the synthetic occluder removed all 341 contaminant-colored samples and reduced coverage from 44.46% to 39.55%. The per-case file includes the seam and hidden-surface measurements. These controls support diagnosis with both contour and photometric evidence. No automatic exclusion threshold is qualified by this fixture.

The [pinned Lab replay files](https://github.com/egenovese-de/Human3D-2.0/tree/53f825cc86c202541a9addb80bbbe17c0a8c00ea/DOCS/m6) contain per-identity geometry results, target revision hashes and texture diagnostics.

## Registered residual and fit acceptance

The registered bootstrap reproduced 23.40 mm mean symmetric residual over four identities. The four-view stored fit measured 23.48 mm. The mean of the per-identity p95 changed from 62.73 to 63.32 mm, and mean held-out silhouette IoU from 69.08% to 68.57%. The fitted torso improved the chest section on two female presets. The fixed chest section remained undersized in all four. The Lab records hip, waist and chest measurements and their signed errors, including fixed section heights and controls at their bounds.

At identical search schedules, the one-sided and symmetric direct-surface objectives gave mean residuals of 22.98 and 22.82 mm. Their mean fitting times were 29.51 and 28.97 s. Both used known synthetic surfaces, and these results do not establish photo-driven gains. No objective or base was promoted.

The frozen fallback rule was replayed without changing its thresholds. It rejected all eight articulated Q fits, including both silhouette-beneficial examples and the one neutral-surface-beneficial example at the recorded labels. Its neutral-surface labels use a 0.1 mm reporting tolerance. The independent source-family acceptance test is still blocked. Production keeps the existing fit acceptance behavior.

## Editable USDZ

The unchanged Q inputs exposed disconnected neckline patches in both native top layers. Applying the connected-shell rule to all prototype categories removed those patches. The four native multi-layer exports then passed direct Blender 4.5.17 import, armature motion, vertex edit and save/reopen, and garment removal with preserved body geometry. The two synthetic clothes-in-photo controls and the historically successful independent ring-layer control were stopped by the body or layer collision gate before import. Parameter attempts within the existing ease and hem bounds did not produce clear shells for the two photo controls. The required seven-case export replay remains blocked at 4/7. The collision validator was kept fail-closed.

See the [registered geometry, acceptance and Blender evidence](https://github.com/egenovese-de/Human3D-2.0/tree/f82d993b5f070348e933fc410e808f4373316c0c/DOCS/m6).
