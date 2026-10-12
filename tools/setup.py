"""Download official JavaFoil and Java 17 scripting dependencies locally."""
from pathlib import Path
import subprocess
import sys
import urllib.request
import hashlib

ROOT=Path(__file__).resolve().parent.parent
VENDOR=ROOT/"runtime/vendor"
FILES={
    "javafoil.jar":"https://www.mh-aerotools.de/airfoils/java/javafoil.jar",
    "mhclasses.jar":"https://www.mh-aerotools.de/airfoils/java/mhclasses.jar",
    "nashorn-core-15.4.jar":"https://repo.maven.apache.org/maven2/org/openjdk/nashorn/nashorn-core/15.4/nashorn-core-15.4.jar",
}
for artifact in ("asm","asm-commons","asm-tree","asm-util","asm-analysis"):
    FILES[f"{artifact}-7.3.1.jar"]=f"https://repo.maven.apache.org/maven2/org/ow2/asm/{artifact}/7.3.1/{artifact}-7.3.1.jar"

def main():
    VENDOR.mkdir(parents=True,exist_ok=True)
    for name,url in FILES.items():
        destination=VENDOR/name
        if not destination.exists():
            print("Downloading",name)
            temporary=VENDOR/(name+".download")
            urllib.request.urlretrieve(url,temporary)
            if temporary.read_bytes()[:2]!=b"PK":
                temporary.unlink()
                raise RuntimeError("Download is not a JAR: "+url)
            temporary.replace(destination)
        print(name,hashlib.sha256(destination.read_bytes()).hexdigest())
    subprocess.run([sys.executable,str(ROOT/"tools/fix_javafoil.py")],check=True)
    if "--skip-python" not in sys.argv:
        subprocess.run([sys.executable,"-m","pip","install","--target",str(VENDOR/"python"),
            "-r",str(ROOT/"docs/requirements.txt")],check=True)
    print("Ready. Run Launch.cmd to open the desktop program. Java 17 must be installed.")

if __name__=="__main__":
    main()
