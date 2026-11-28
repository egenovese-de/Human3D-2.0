# M7 known limitations

- The supplied qualification data are synthetic. Resemblance, camera robustness and throughput on the Project Lead's Windows laptop remain empirical questions.
- The uncalibrated route estimates weak-perspective framing and pose. Rear and side orientation are ambiguous. Engine B can exclude these views from anatomy fitting. Blender assets carry nominal units with unknown real-world scale.
- Automatic rear registration remains unqualified. Engine B can fit with an independently calibrated square image or an advanced manifest with a verified G3 camera sector. The externally anchored perspective path remains experimental. The target pose and viewport overlay still use an estimated M6 camera.
- The CPU viewport approximates texture at mesh-face resolution. The USDZ contains the baked texture when available. Clothing pixels may be projected onto the body.
- Independent garments require the optional supported template category. Segmentation cannot reliably classify clothing from arbitrary photographs. Failed appearance or rejected optional layers leave a structurally validated body when available.
- Canonical and target results plus logs are retained per attempt. A project with large originals or many attempts uses additional local disk space. Move or archive the project as a folder.
