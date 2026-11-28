# G6 · Embedded deformation graph

| Method | A held-out retained mm | B held-out proposal mm | B held-out retained mm | B paired gain mm | B backtracked |
| --- | --- | --- | --- | --- | --- |
| R4_graph48 | 7.29 | 14.85 | 20.41 | 1.32 | 3/3 |
| R4_graph120 | 7.28 | 19.16 | 20.37 | 1.35 | 3/3 |

Nodes use mesh-geodesic farthest-point placement and geodesic neighborhood blending. Edges respect the connected topology instead of direct Euclidean proximity. The tested graph fits local translations with smoothness on the graph. Rotational ARAP and region-specific stiffness remain open. Report both proposal and retained metrics because crossings account for much of the difference.
