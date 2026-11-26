"""Audit pinned Python dependencies against PyPI advisory metadata."""
import json
import tomllib
from pathlib import Path
from urllib.request import urlopen
ROOT = Path(__file__).resolve().parents[1]

def main():
    pins = set()
    for path in ROOT.glob("requirements-*.lock"):
        if ".candidate." in path.name:
            continue
        for line in path.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                pins.add(tuple(line.split()[0].split("==")))
    for requirement in tomllib.loads((ROOT/"pyproject.toml").read_text())["build-system"]["requires"]:
        pins.add(tuple(requirement.split("==")))
    findings = []
    for name,version in sorted(pins):
        with urlopen(f"https://pypi.org/pypi/{name}/{version}/json",timeout=45) as response:
            data = json.load(response)
        if "vulnerabilities" not in data:
            raise RuntimeError("Missing advisory metadata")
        active = [v["id"] for v in data["vulnerabilities"] if not v.get("withdrawn")]
        print(json.dumps({"package":name,"version":version,"license":data["info"].get("license_expression") or (data["info"].get("license") or "")[:240],"advisories":active}),flush=True)
        findings.extend((name,version,v) for v in active)
    print(f"Reviewed {len(pins)} version pins; active advisories: {len(findings)}",flush=True)
    if findings:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
