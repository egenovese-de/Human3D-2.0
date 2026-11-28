# G6 · Weighted architecture decision

Scores use a 1–5 engineering judgment scale with 5 favorable. Weights reflect the deployment objective. Independent accuracy and structural reliability dominate. Photographic transfer and registration follow. Runtime, rig compatibility and implementation complexity retain material weight. An untested high-capacity redesign receives low evidence-based readiness.

| Criterion | Weight | A Native | B FFD | C Graph | D Registration | E Hybrid | F Redesign |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Independent and regional accuracy | 25% | 2 | 5 | 3 | 3 | 4 | 1 |
| Reliability, rig and UV | 25% | 4 | 4 | 2 | 2 | 2 | 1 |
| Photo transfer and registration robustness | 20% | 3 | 3 | 2 | 1 | 1 | 1 |
| CPU runtime and memory | 15% | 5 | 4 | 4 | 3 | 2 | 1 |
| Effort and maintainability | 10% | 5 | 3 | 3 | 2 | 1 | 1 |
| Extensibility and anatomy detail | 5% | 2 | 3 | 4 | 4 | 5 | 5 |
| Weighted score / 5 | 100% | 3.45 | 3.90 | 2.75 | 2.30 | 2.35 | 1.20 |

**Choose B as a gated candidate.** Use a bounded fine FFD field after native initialization. Its 14-step independent held-out result is 13.42 mm. The 28-step result is 13.34 mm. The lower raw hybrid does not survive the guards as often. Use M7 whenever the registration or structure gate fails. Reserve C–E for methods with improved correspondence and collision control. Investigate F only under a separately approved anatomical completeness scope.
