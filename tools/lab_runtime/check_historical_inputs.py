import tempfile
from pathlib import Path
from historical_inputs import verify_holdout, verify_rig
from bootstrap import ROOT
import json

inventory=json.loads((ROOT/"DOCS/q/finalization/input-hashes.json").read_text())
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    for group,directory,verify in (("holdout","holdout",verify_holdout),("rig_fixtures","rig-fixtures",verify_rig)):
        fixture,files=next(iter(inventory[group].items()))
        name=next(iter(files))
        target=root/directory/fixture/name
        for corrupt in (False,True):
            if corrupt:
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(b"invalid historical bytes")
            try:
                verify(root)
            except ValueError as exc:
                assert str(exc)=="missing or changed historical input: "+f"{directory}/{fixture}/{name}"
                print("REJECTION PASS",group,"corrupt" if corrupt else "missing")
            else:
                raise AssertionError("invalid input admitted")
