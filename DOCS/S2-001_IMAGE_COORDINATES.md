# S2-001 — Image ingestion, orientation and coordinate mapping
Status: DONE within synthetic regression scope.
## Evidence
0939c54: four coordinate concerns covered by three synthetic test methods (EXIF 1–8, padding/resize, mask crop/resize/draft). Run 45800820124 SUCCESS.
152fa393ce3c797ab332a40767d72b7185b1867e: fourth test exercises actual ingestion, byte preservation, duplicate handling, thumbnails, detection coordinate conversion, mask review and appearance across all eight orientations with a mocked native inference result.
Run 45800899092: all five jobs SUCCESS. Ubuntu job 139844802661: 45 tests in 4.349s. Windows job 139844802742: 45 tests in 8.698s and installed suite 45 tests in 4.545s. All four new methods passed. Both actual pinned asset checks PASS. Ubuntu 26 version pins, zero active advisories.
## Disposition
No confirmed functional defects in tested paths; no production changes justified. Pillow getdata deprecation in test code is nonblocking with pinned Pillow 13; future compatibility maintenance needed. Multi-frame import policy not changed; no demonstrated coordinate failure from that policy. Native inference is mocked, not a real MediaPipe accuracy or empirical validation. Windows 11 client remains unverified (S1-002 BLOCKED). No empirical photos or binary fixtures committed. S2-002 not started.
