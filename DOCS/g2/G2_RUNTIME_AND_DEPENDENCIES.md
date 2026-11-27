# Runtime, licensing and dependency feasibility

Local CPU host AMD EPYC 9V74, Linux x86_64, 9 visible CPUs, approximately 10 GB RAM. Python 3.11.9; NumPy 1.26.4, SciPy 1.15.3, Pillow 13.0.0, MediaPipe 0.10.33 and OpenCV contrib 4.11.0.86. Local Workbench and BVH used Blender 4.3.2. The matched lab reproduction [Actions run 46065432601](https://github.com/egenovese-de/Human3D-2.0/actions/runs/46065432601) passed permanent Lab Runtime provisioning and verification with Blender 4.5.3 on Ubuntu. Verified artifact SHA-256 is `9dd9afe5f9a0a7ffc33274877ba1c4e7afce460c806b0998f7d9ee3168c60fd2`. The local bootstrap failed at the relocatable interpreter loader. Local Python packages reused the prior Lab dependency versions. The actual Windows i7-1355U was unavailable.

Local photographic benchmark peak RSS 770 MiB, including the G1 evaluator and model. Depth worker peak RSS 848 MiB. Benchmarked native G1 silhouette fitting generally takes a few seconds for four 144 px views. Actual M6 product fitting takes a median 81.4 s across the completed product runs. Wall timings depend on workload and artifact creation, and are not production throughput promises.

| Item | License and admission | Runtime disposition |
| --- | --- | --- |
| MakeHuman v1.3.0 `1f508f6` | Core assets CC0, upstream code AGPL. Assets verified against the G1 pinned intake. Upstream program source and binaries are absent from the evidence ZIP. | G1 evaluator in Lab. |
| Pose Lite float16 v1 / MediaPipe 0.10.33 | Apache-2.0 SDK. 5,777,746-byte official model, SHA-256 `59929e1d…`. The product's separate weight clearance remains open. | Existing CPU dependency. |
| OpenCV contrib 4.11.0.86 | OpenCV Apache-2.0; bundled components retain separate licenses. Lock and wheel digests in permanent Lab. | Existing CPU dependency. |
| NumPy/SciPy/Pillow | BSD-3-Clause/BSD-3-Clause/HPND and related notices. See the permanent Lab dependency lock. | Existing numeric runtime. |
| Depth Anything V2 Small ONNX / ONNX Runtime 1.24.1 | Upstream Small and conversion mark Apache-2.0. ONNX runtime MIT. Weights 99,060,839 bytes, SHA-256 `afb6a5c28f3b6bf1618c6e43f02073ef9dfdc70e937502d51603e57b0a1df10c`; omitted from publication. Training data contains mixed sources. Project-specific deployment clearance is open. | Optional Lab diagnostic on CPU, no GPU needed in this test. |
| Blender 4.5.3 CI / 4.3.2 local | GPL, GPL-compatible Blender-side scripts. No redistribution of application or wheels. | Lab rendering and scoring only. |
| MB-Lab `063bff04e60f3e7c651fda628c30f5d83f3f3078` | GPL code and AGPL database. Restricted source assets, recreatable maps and comparison scenes retained locally, with numeric results permitted by the previous Lab disposition. | Local holdout only. |
| FAUST and THuman | FAUST benchmark lists the MPI PS:License 1.0. THuman dataset is non-commercial research only. Consent, photo rights, scale and alignment not verified for project admission. | Family C unadmitted. |

Primary sources [Depth Anything V2](https://github.com/DepthAnything/Depth-Anything-V2), [ONNX model card](https://huggingface.co/onnx-community/depth-anything-v2-small), [Pose Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker), [MB-Lab license](https://mb-lab-docs.readthedocs.io/en/latest/license.html), [FAUST](https://is.mpg.de/code/faust-dataset), [THuman](https://github.com/ytrock/THUman2.0-Dataset).
