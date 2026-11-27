# Human3D 2.0 visual evidence distillation specification

Keep the geometry-oriented response as the primary experimental teacher contract. Use an orthographic or calibrated front/side view classifier before interpreting any projected axis. The intake retains the original response, prompt and schema versions, associated subject, viewpoint and exact image hash. Store normalized values separately from teacher text.

| Field | Type and allowed values | Visibility and missing data | Geometry consumer |
|---|---|---|---|
| Subject and view | Associated subject key, front/side/three-quarter view label | A missing or conflicting association prevents fusion | Selects profile and projection axis |
| Upper and hip extent | Real number in [0.05, 0.50], normalized by head-to-sole image height | Front gives width, side gives depth. Occlusion or an oblique axis gives null. Full rendered height must be available. | Bounded linearized regional fitter consumes the corresponding projected cross-section |
| Lower/upper interval | Finite bracket containing the estimate | Null accompanies absent estimate. Large intervals reduce the observation weight. | Half-width with a 0.005 floor provides residual scaling |
| Categorical fallback | Tapered, moderate, straight, or ordinal 1–5 | Retain only when the projected ratio is visible. Null has no geometric penalty. | Ratio prior, with reduced weight and separate categorical confidence |
| Provenance | Image SHA-256, prompt/schema version, provider label and original response | Reject mismatched hashes and malformed or unexpected fields | Reproducibility, audits and deduplication |

P3 fusion joins complementary axes and suppresses exact repeats. Multiple measurements of the same field from distinct views need calibration, a robust weighted center and explicit conflict handling in production. Do not treat the pilot's intervals as probabilistically calibrated.

Split by subject, source and rendering family before training. Include natural-image consent or appropriate licenses, crop and focal-length variation, occlusions, hidden regions, mismatched identities and adversarial view labels. Keep independent labels and analytic geometric projections out of the inference request. Measure strict schema compliance, abstention on hidden axes, numerical error and interval coverage, then test how errors propagate to geometry and compare against a silhouette-only baseline. Evaluate aggregate versus specialist heads and resource use on an isolated holdout. Training and deployment remain outside P3/P4.
