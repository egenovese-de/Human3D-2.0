import json
import struct
from pathlib import Path

for run in ("run-a", "run-b"):
    p = Path("lab-output") / run
    a,b = [json.loads((p/str(i)/"render_report.json").read_text()) for i in (1,2)]
    assert a["center"] == b["center"] and a["span"] == b["span"]
    for i in (1,2):
        files = list((p/str(i)).glob("*.png"))
        assert len(files) == 12
        for f in files:
            data = f.read_bytes()
            assert data[:8] == bytes.fromhex("89504e470d0a1a0a")
            assert struct.unpack(">II",data[16:24]) == (384,480)
    print("FRAMING PASS",run,a["center"],a["span"],"24 PNG PASS")
