"""Build a local JavaFoil compatibility copy; preserve the official JAR."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import zipfile
ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "runtime/vendor"
TARGETS = ["MH/JavaFoil/OptionsCard.class", "MH/JavaFoil/GlobalSettings.class"]

def main():
    javac = shutil.which("javac")
    java = shutil.which("java")
    if not javac or not java:
        raise RuntimeError("Java 17 JDK (including javac) must be on PATH for the compatibility fix.")
    build = VENDOR / "compat-build"
    build.mkdir(exist_ok=True)
    source = VENDOR / "javafoil.jar"
    with zipfile.ZipFile(source) as jar:
        for target in TARGETS:
            (build / (Path(target).stem + "-original.class")).write_bytes(jar.read(target))
    subprocess.run([javac, "-cp", str(VENDOR / "asm-7.3.1.jar"), "-d", str(build),
        str(ROOT / "tools/compat/PatchJavaFoil.java"), str(ROOT / "tools/compat/JavaFoilVersionCompat.java")], check=True)
    for target in TARGETS:
        stem = Path(target).stem
        subprocess.run([java, "-cp", str(build) + os.pathsep + str(VENDOR / "asm-7.3.1.jar"),
            "PatchJavaFoil", str(build / (stem + "-original.class")), str(build / (stem + ".class"))], check=True)
    subprocess.run([java, "-cp", str(build), "JavaFoilVersionCompat"], check=True)
    destination = VENDOR / "javafoil-compatible-v2.jar"
    temporary = VENDOR / "javafoil-compatible.tmp"
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as patched:
        for item in original.infolist():
            upper = item.filename.upper()
            # Only the modified local copy is unsigned; Java security settings stay unchanged.
            if upper.startswith("META-INF/") and (upper.endswith((".SF", ".RSA", ".DSA")) or upper == "META-INF/MANIFEST.MF"):
                continue
            data = ((build / Path(item.filename).name).read_bytes()
                    if item.filename in TARGETS else original.read(item.filename))
            patched.writestr(item, data)
        patched.writestr("JavaFoilVersionCompat.class", (build / "JavaFoilVersionCompat.class").read_bytes())
        patched.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\nMain-Class: MH.JavaFoil.JavaFoil\n\n")
    temporary.replace(destination)
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(destination) as fixed:
        changed = [name for name in original.namelist()
                   if name.endswith(".class") and original.read(name) != fixed.read(name)]
        assert set(changed) == set(TARGETS), changed
    (VENDOR / "compatibility.json").write_text(json.dumps(dict(
        original_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        compatible_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
        changed_classes=changed,
        reason="Correct modern Java version detection and disable only the startup age reminder."
    ), indent=2))
    print("Local compatibility copy ready:", destination)

if __name__ == "__main__":
    main()
