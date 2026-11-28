# G5 CPU runtime and resources

Linux host AMD EPYC 9V74, FP32, two inference threads. Initialization includes import, hash validation and cold session creation. Warm includes image resizing, inference and output resampling; image decoding is outside the timer. Peak RSS is per independently launched predictor process. The archive includes exact timing rows and pipeline stage timings.

| Model | N | Init s | First s | Warm median s | Reduced median s | Weights MiB | Peak RSS MiB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| depth | 100 | 0.64 | 0.48 | 0.43 | 0.21 | 94.47 | 363.26 |
| normal | 100 | 3.05 | 1.23 | 1.31 | 0.80 | 277.80 | 998.25 |

## Windows and Linux CI

| Artifact | System | Init s | First s | Warm median s | RSS MiB after runs |
| --- | --- | --- | --- | --- | --- |
| 15256259800 | Linux-7.0.0-1020-azure-x86_64-with-glibc2.39 | 0.25 | 0.18 | 0.17 | 388.00 |
| 15256298104 | Windows-10-10.0.20348-SP0 | 1.20 | 0.54 | 0.53 | 307.54 |
| 15256829058 | Windows-10-10.0.20348-SP0 | 0.50 | 0.55 | 0.48 | 307.03 |
| 15256968497 | Windows-10-10.0.20348-SP0 | 3.13 | 1.63 | 1.44 | 901.80 |
| 15257147746 | Linux-7.0.0-1018-aws-x86_64-with-glibc2.39 | 0.31 | 0.24 | 0.24 | 381.88 |

Windows CI used a synthetic geometric RGB smoke. The hardware differs from the physical Windows 11 target. Fit timing varies with admitted views and host contention. Full Windows application memory, quantization, host-specific cache throughput and target hardware power modes remain unmeasured. Per-image model inference is cacheable. Cache identity must include oriented RGB digest, checkpoint hash, image transform, calibrated or assumed intrinsics for DSINE, and evidence convention version. D0 depth alignment depends on canonical solve, visibility and calibration, so aligned artifacts need an additional fit-dependent key.
