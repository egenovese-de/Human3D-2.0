"""Local-only native audit; supplied inventory is not historical authentication."""
import json
import sys
from pathlib import Path
from bootstrap import safe, digest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"m6"))
from audit_bind_frames import native_audit

def verify_projects(root):
    inventory=root/"native-project-inventory.json"
    rows=json.loads(inventory.read_text())
    if set(rows)!={"f_af01","m_la01"}:
        raise ValueError("two named native projects required")
    projects=[]
    for identity,row in sorted(rows.items()):
        project=safe(root,row["project"])
        files=row["files"]
        actual={p.relative_to(project).as_posix():digest(p) for p in project.rglob("*") if p.is_file()}
        if not files or actual!=files:
            raise ValueError("native project inventory mismatch: "+identity)
        projects.append(project)
    return projects,digest(inventory)

def main(root,output):
    projects,sha=verify_projects(root)
    rows=[native_audit(p) for p in projects]
    output.write_text(json.dumps({"scope":"local supplied projects; historical identity unverified","inventory_sha256":sha,"native":rows},indent=2,allow_nan=False)+"\n")

if __name__=="__main__":
    main(*map(Path,sys.argv[1:]))
