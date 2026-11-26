# M6 Evidence v2 checkpoint

The existing content-addressed observation envelope reads both versions. A legacy v1 record can be upgraded explicitly to v2 in memory. Persisting a v1 detection omits the v2 field, preserving its former content hash. Both versions retain photo/candidate checks and detector fallback when the optional provider fails.

The current production allowlist has one quantitative consumer. `regional.landmark_visibility_cap@v1` describes a photo-local upper bound on landmark visibility for a named region. A record must specify its uncertainty. The consumer compares uncertainty-expanded ranges, ignores contradictory bounds and uses the least restrictive upper bound among compatible observations. Duplicate input supplies no extra confidence. It can only reduce the native visibility used by alignment and fitting. Existing v1 hidden-region suppression keeps priority.

Proportions, circumference, asymmetry, morphological descriptors and volume proxies can be validated and stored for later evaluation. Their definitions need known-effect consumers and conflict checks before driving geometry. Metric inputs require a calibration reference and positive uncertainty. The model does not use metric inputs to change shape at this checkpoint.
