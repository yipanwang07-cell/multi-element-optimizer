"""Offline catalog and name resolution for the built-in airfoil coordinates."""
from pathlib import Path
import hashlib
import json
import re
import shutil
from app_paths import ROOT,AIRFOILS
LIB=AIRFOILS
MANIFEST=LIB/"library.json"

def airfoils(include_unavailable=False):
    if not MANIFEST.exists(): return []
    result=json.loads(MANIFEST.read_text(encoding="utf-8"))["airfoils"]
    return result if include_unavailable else [e for e in result if e["status"]=="available"]

def key(value):
    return re.sub(r"[^a-z0-9]","",value.lower())

def find(source):
    wanted=key(source)
    for entry in airfoils(True):
        aliases=[entry["id"],entry["name"],entry["family"]+" "+entry["name"],*entry.get("aliases",[])]
        if wanted in {key(x) for x in aliases}: return entry
    return None

def resolve_profile(source,base):
    entry=find(source)
    if entry:
        if entry["status"]!="available":
            raise ValueError(entry["name"]+" has no verified coordinates installed. Open Library and import its DAT file.")
        path=(LIB/entry["file"]).resolve()
        if LIB.resolve() not in path.parents:
            raise ValueError("Library coordinate path must stay inside the library")
        if not path.is_file(): raise ValueError("Library coordinate file missing: "+entry["name"])
        return path
    path=Path(source)
    return path if path.is_absolute() else Path(base)/path

def choices():
    return ["NACA 0012","NACA 2412","NACA 4412","NACA 6412","NACA 7412"]+[e["name"] for e in airfoils()]

def register(entry_id,path,source_url=""):
    # Import into an existing catalog slot; validation occurs before mutation.
    import wing_optimizer as engine
    engine.profile(str(Path(path).resolve()),120,ROOT)
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    entry=next(e for e in manifest["airfoils"] if e["id"]==entry_id)
    filename=entry_id+".dat"
    data=Path(path).read_bytes()
    (LIB/filename).write_bytes(data)
    entry.update(file=filename,status="available",source_url=source_url or "User-supplied coordinate file",
        method="Imported coordinates; source authenticity not independently verified",
        sha256=hashlib.sha256(data).hexdigest())
    entry.pop("note",None)
    entry.pop("validation",None)
    entry.pop("source_pdf_sha256",None)
    entry.pop("source_point_count",None)
    MANIFEST.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return entry
