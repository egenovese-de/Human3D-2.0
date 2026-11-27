"""Offline provenance control, not actual GPT inference."""
import hashlib
import json
import sys
from pathlib import Path

def normalize(record, image):
    if record["image_sha256"]!=hashlib.sha256(image).hexdigest():
        raise ValueError("image mismatch")
    if record["origin"] not in ("oracle","simulated_vlm"):
        raise ValueError("unverified inference origin")
    if record["model"] is not None:
        raise ValueError("no actual model inference")
    if record["schema_version"]!=1 or record["prompt_version"]!="control-v1":
        raise ValueError("version mismatch")
    raw=json.loads(record["raw_response"])
    if set(raw)!={"hips"} or type(raw["hips"]) not in (float,int) or not -1<=raw["hips"]<=1:
        raise ValueError("invalid evidence")
    return {"origin":record["origin"],"controls":raw,"actual_inference":False}

def main(root):
    image=(root/"0/oracle_mask.png").read_bytes()
    base={"image_sha256":hashlib.sha256(image).hexdigest(),"schema_version":1,"prompt_version":"control-v1","model":None}
    records=[dict(base,origin="oracle",raw_response='{"hips":0.5}'),dict(base,origin="simulated_vlm",raw_response='{"hips":0.4}')]
    results=[normalize(r,image) for r in records]
    assert results==[normalize(r,image) for r in records]
    for bad in [dict(records[0],origin="gpt"),dict(records[0],image_sha256="0"*64),dict(records[0],raw_response='{"hips":2}')]:
        try: normalize(bad,image)
        except ValueError: continue
        raise AssertionError("invalid evidence accepted")
    report={"status":"PASS","scope":"offline replay; no actual VLM inference","records":records,"normalized":results,"negative_controls":3}
    print("EVIDENCE_REPLAY="+json.dumps(report))
    (root/"evidence_replay.json").write_text(json.dumps(report,indent=2))
if __name__=="__main__": main(Path(sys.argv[1]))
