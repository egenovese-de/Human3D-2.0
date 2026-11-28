# Empirical testing on Windows

Open Human3D and choose **Import Photos**, click the target thumbnail, then choose **Generate 3D**. A single photo becomes the target automatically. The first import can create a project under Documents/Human3D. **New Project** and **Open Project** control the project folder explicitly.

Use the inspection controls to switch Canonical and Target Pose, choose Standard views or orbit by dragging, zoom with the wheel and pan with a right or middle drag. Use **Compare Photo** to inspect the selected result's target beside its viewport. Green is overlap, coral is projected-only, blue is observed-only, and gold shows observed landmarks. Compare reproducible shape changes and camera framing separately. Estimated silhouettes can overlap despite incorrect depth or anatomy.

Under **Diagnostics & Settings**, note the requested and executed engine, camera source, unknown scale, omitted layers and fit warnings. Choose Engine B and Generate 3D again to compare with A using the same references. The result selector retains each attempt. Select a Canonical or Target Pose representation and choose **Export 3D**. In Blender 4.5, choose **File → Import → Universal Scene Description**, inspect the Body and Skeleton, then save a Blender project. Use **Export Evidence** when reporting a result. Original photographs are optional and excluded by default.

| Input | What to observe |
| --- | --- |
| Single frontal, then single lateral | Body publication, pose coverage and orientation warnings |
| Front and side | Waist and torso depth across orbit views |
| Front, side and rear | Rear orientation and which views contribute |
| Four complementary views | Coverage, stage times and resource use |
| Same set, different targets | Canonical identity remains constant and pose changes |
| Tight then loose clothing | Boundary bias, texture coverage and explicit garment omissions |
| Partial occlusion | Ambiguity, missed regions and previous-result retention |
| Additional photos in an existing project | New generation with the previous result still available |
