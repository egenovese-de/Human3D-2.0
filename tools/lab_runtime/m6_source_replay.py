"""Replay original source audit only; native project replay requires separate verified inputs."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"m6"))
from audit_bind_frames import source_audit

root,output=map(Path,sys.argv[1:])
rows=[source_audit(p) for identity in ("f_af01","m_la01")
      for p in sorted(root.glob(f"{identity}_*/manifest.json"))
      if not json.loads(p.read_text())["morphology_asymmetry"]]
if not rows:
    raise ValueError("no_source_rig_fixtures")
output.write_text(json.dumps({"scope":"historical source rig only","source":rows},indent=2,allow_nan=False)+"\n")
