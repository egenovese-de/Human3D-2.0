# M6 CI history boundary

The first M6 CI run passed both locked foundation jobs, including Windows clean installation. The asset scan failed because it classified seven historical Q output PNGs on `lab/render` as release payloads. The development branch and peeled v0.2.0 release history had zero denied paths.

The scanner now recognizes only the seven specific Q output blobs at their original Lab paths, and only while their commits are reachable exclusively from the designated Lab ref. A tag, production ref, or development checkout reaching one of those commits puts it back under the ordinary deny rules. A render replaced in place or published at a different path is also denied. Project photos, models, archives, executable binaries and wheel members remain subject to the existing rules. The credential screen still covers every fetched ref.

Reference: [initial M6 checks](https://github.com/egenovese-de/Human3D-2.0/actions/runs/45905649778).
