# Changelog

## 0.2.0 — technical baseline

- Consolidates M1–M5 and stabilization: shared anatomy, pose, texture, separate supported garments and editable USDZ export.
- Adds bounded job retention, worker cancellation, evidence invalidation, dependency locks and reproducible wheel checks.
- Prior candidate evidence: 69 regression tests on Linux, Windows Server and Windows 11; synthetic GUI and Blender round-trip. Release revision requires fresh CI.
- Known limitations: external VLM unverified; photographic silhouette IoU 75.669% on the historical synthetic fixture; sampled garment clearance only. Empirical acceptance is separate and not documented as passed.
- Runtime model and upstream assets are provisioned separately. No benchmark Q changes.
