"""Install pinned official SU2/Gmsh Windows binaries into the local runtime."""
import hashlib
import io
from pathlib import Path
import sys
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def download(url,sha):
    data=urllib.request.urlopen(url,timeout=120).read()
    if hashlib.sha256(data).hexdigest()!=sha:raise RuntimeError("Download checksum mismatch")
    return data

def extract(archive,target):
    target=target.resolve();target.mkdir(parents=True,exist_ok=True)
    for entry in archive.infolist():
        destination=(target/entry.filename).resolve()
        if not destination.is_relative_to(target):raise ValueError("Unsafe archive path")
    archive.extractall(target)

def main():
    if sys.platform!="win32":raise SystemExit("This installer targets Windows. Install SU2 and Gmsh separately on other systems.")
    vendor=ROOT/"runtime/vendor";target=vendor/"su2"
    print("Downloading official SU2 8.5.0…",flush=True)
    data=download("https://github.com/su2code/SU2/releases/download/v8.5.0/SU2-v8.5.0-win64-omp.zip","4466fe21aedb5e0bad57afd45f829acbdec6ec79fe8c3f8954ddea06a4b4bc11")
    outer=zipfile.ZipFile(io.BytesIO(data))
    extract(zipfile.ZipFile(io.BytesIO(outer.read("win64-omp.zip"))),target)
    license_url="https://raw.githubusercontent.com/su2code/SU2/v8.5.0/LICENSE.md"
    (target/"LICENSE.md").write_bytes(urllib.request.urlopen(license_url,timeout=30).read())
    print("Downloading Gmsh 4.15.0…",flush=True)
    data=download("https://files.pythonhosted.org/packages/23/51/21175eb9c6a592431a5c87f288ce447af1cea68a6ad4169765dc7ab7a9e7/gmsh-4.15.0-py2.py3-none-win_amd64.whl","a5b9867f88af59aff269a93abbd009551fbc263eb94a165a25a0c8072bae13db")
    wheel=zipfile.ZipFile(io.BytesIO(data));package=vendor/"python";package.mkdir(parents=True,exist_ok=True)
    for name in wheel.namelist():
        if name=="gmsh.py" or name.endswith("gmsh-4.15.dll"):
            (package/Path(name).name).write_bytes(wheel.read(name))
        elif name.endswith("share/doc/gmsh/LICENSE.txt"):
            (package/"GMSH_LICENSE.txt").write_bytes(wheel.read(name))
        elif "dist-info" in name and not name.endswith("/"):
            path=package/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(wheel.read(name))
    print("CFD tools installed. Restart the app.")

if __name__=="__main__":main()
