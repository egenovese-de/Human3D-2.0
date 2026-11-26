# S3-004 — Pipeline resource profiling

2026-11-26

## Baseline and correction

AUD-06 reproduced 1,000 retained jobs for 1,000 completed submissions and one current artifact. Commit `e407b01` introduced a 128-record terminal history limit and rejected late results from evicted jobs. Commit `d25892f` enforced the limit on every terminal transition while preserving in-flight jobs. The regression suite verifies eviction, rejected late publication and duplicate import deduplication.

| Probe | Ubuntu 24.04 | Windows Server 2022 |
|---|---:|---:|
| Terminal records after 1,000 jobs | 128 | 128 |
| Reduction in retained records | 87.2% | 87.2% |
| Peak Python allocations before → after (bytes) | 271,667 → 44,653 | 271,651 → 44,469 |
| Duplicate-import project size before → after (bytes, 100 repeats) | 2,290 → 2,290 | 2,290 → 2,290 |

The baseline is recorded in [findings reconciliation](FINDINGS_RECONCILIATION.md). Post-fix metrics are from [Required checks 45858646732](https://github.com/egenovese-de/Human3D-2.0/actions/runs/45858646732) at `d25892f`. The allocation comparison uses the same 1,000-job probe and measures Python allocations with tracemalloc.

## Canonical synthetic pipeline

Reproduce with `python tools/verify_runtime_assets.py` from a checkout with the platform lock installed. The verifier provisions pinned assets, verifies them, and runs the reconstruction benchmark with networking disabled. The benchmark uses the frozen MakeHuman body, a generated frontal silhouette, constant RGB, a single view, two 256 px atlases and a single top with garment parameter optimization disabled. The frozen-body digest was `1915bb8ea49b8a79471fa03817b16962cf0ae649137d1138482566f9df5cd650` on both runners.

Both platform jobs passed in [Required checks 45859948344](https://github.com/egenovese-de/Human3D-2.0/actions/runs/45859948344) at `f76e8a141d8771b949106b01fe7c56e12b00a4fb` with Python 3.11.9 and hashed platform locks.

| Validation | Result |
|---|---|
| [Ubuntu 24.04](https://github.com/egenovese-de/Human3D-2.0/actions/runs/45859948344/job/140048098331) | 68/68 PASS (4.709 s) |
| [Windows Server 2022](https://github.com/egenovese-de/Human3D-2.0/actions/runs/45859948344/job/140048098267) | 68/68 PASS (9.594 s) |
| Clean Windows Server 2022 install | Native smoke PASS, 68/68 PASS (5.928 s) |

| Stage | Ubuntu seconds | Windows seconds | Ubuntu peak RSS (bytes) | Windows peak RSS (bytes) |
|---|---:|---:|---:|---:|
| `freeze` | 0.283 | 0.419 | 314,818,560 | 219,893,760 |
| `synthetic_view` | 0.059 | 0.089 | 314,818,560 | 219,893,760 |
| `fit_body` | 5.067 | 6.914 | 314,818,560 | 219,893,760 |
| `deform_rebind_pose` | 0.081 | 0.173 | 314,818,560 | 219,893,760 |
| `body_atlas_256` | 2.693 | 3.911 | 314,818,560 | 219,893,760 |
| `garment_top` | 0.856 | 1.246 | 326,717,440 | 227,078,144 |
| `garment_atlas_256` | 1.581 | 2.282 | 326,717,440 | 227,078,144 |
| `usdz` | 1.018 | 1.509 | 326,717,440 | 227,442,688 |

| Run summary | Ubuntu 24.04 | Windows Server 2022 |
|---|---:|---:|
| Total wall time (s) | 11.643 | 16.563 |
| Peak RSS before first stage (bytes) | 265,969,664 | 171,032,576 |
| Peak RSS at completion (bytes) | 326,717,440 | 227,442,688 |
| Initial workspace (bytes) | 13,433,429 | 13,433,429 |
| Workspace from freeze through garment atlas (bytes) | 17,865,622 | 17,865,622 |
| Final workspace (bytes) | 19,015,654 | 19,015,343 |
| Generated workspace bytes | 5,582,225 | 5,581,914 |
| USDZ package (bytes) | 1,150,032 | 1,149,721 |

Stage times are wall-clock operation durations. Total wall time includes measurement overhead and excludes asset provisioning and preflight. RSS is the process high-water mark through each stage, measured via Linux `getrusage` and Windows `PeakWorkingSetSize`. It includes the verifier's prior work, imported libraries and loaded assets. Disk figures are logical file bytes at stage boundaries in the temporary verifier workspace, including the pinned inputs and initial frozen body. Transient export staging and allocated filesystem blocks are outside this measurement.

The fitting and body atlas stages accounted for the largest shares of elapsed time. The benchmark covers canonical reconstruction components under synthetic inputs. Full GUI timing, real photographs, multi-view and stacked-garment workloads, repeated target switching, reopen and resource cleanup are outside this profile. Empirical test gate remains `NOT_RUN`.
