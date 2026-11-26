# Fit acceptance and bootstrap fallback

The experimental rule uses only recorded training-view gain, minimum per-view score, saturation and control L2. Ground-truth held-out IoU enters the development objective and evaluation labels. A gain or loss must exceed 0.10 percentage points to count as beneficial or harmful.

| Split | Cases | Correct accepts | Correct rejects | Beneficial rejects | Harmful accepts | Ties |
|---|---:|---:|---:|---:|---:|---:|
| Pilot development | 12 nested cases from six variants in two families | 3 | 4 | 0 | 1 | 4 |
| Preset identity evaluation | 8 cases from four identities in the same two families | 0 | 3 | 0 observed | 1 | 4 |

Both splits contain one- and four-photo fits. The 135-rule grid selected minimum 0.06 training gain. Its other cutoffs were saturation ≤20, L2 ≤3 and minimum view score ≥0. In this search they did not act as effective gates. Fit runtime and rule-evaluation overhead are retained per case. A positive training gain can include improvement from camera/pose adjustment even when the neutral controls remain unchanged. Advancing the same rule would require a test set with beneficial fits and scored regional and leave-one-view-out alternatives.

[Cases, cutoffs and raw overhead](q/followup/acceptance.json)

The explicit 90° profile leave-out refit on four identities recomputed each camera from bootstrap and its own photograph. The omitted photo never entered the three-view fit. On the omitted detector mask the matched fitting score improved by 1.48–2.74 pp. On the separately calibrated held-out neutral targets, IoU fell by 0.94–2.54 pp. This observed disagreement makes a single withheld photographic view an insufficient safeguard for these fixtures.

[Profile leave-out results](q/followup/leaveout.json)
