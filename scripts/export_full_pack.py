"""Build, capture a fresh pack snapshot, then create its offline index."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess
import sys
import uuid


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New snapshot directory")
    parser.add_argument("--java-home", type=Path, help="Build JDK required by GTNHGradle")
    parser.add_argument("--python", type=Path, help="Python with gtnh-data installed")
    parser.add_argument("--nei-reference", action="store_true", help="Also capture a separate NEI handler reference for validation")
    parser.add_argument("--native-recipe-callsites", action="store_true", help="Collect bounded native GT recipe registration callsites")
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = (args.output or root / "exports" / f"{stamp}-{uuid.uuid4().hex[:8]}").resolve()
    if output.exists():
        parser.error("Output must be a new directory so an old export cannot count as success")
    interpreter = args.python or root / "python" / ".venv" / (
        "Scripts/python.exe" if os.name == "nt" else "bin/python"
    )
    if not interpreter.is_file():
        parser.error("Install python/ into a virtual environment or provide --python")
    wrapper = root / "exporter" / ("gradlew.bat" if os.name == "nt" else "gradlew")
    if not wrapper.is_file():
        parser.error("The exporter Gradle wrapper is missing")
    command = [str(wrapper), "--console=plain"]
    if args.java_home:
        command.append(f"-Dorg.gradle.java.home={args.java_home.resolve()}")
    command.extend(["runFullPack", "-PdataAutorun=true", f"-PdataOutputDir={output}"])
    if args.nei_reference:
        command.append("-PdataNeiReference=true")
    if args.native_recipe_callsites:
        command.append("-PdataNativeRecipeCallsites=true")
    print(f"Capturing new snapshot at {output}", flush=True)
    result = subprocess.run(command, cwd=root / "exporter", check=False)
    if result.returncode:
        return result.returncode
    if not (output / "manifest.json").is_file():
        print("The game exited without publishing a snapshot manifest", file=sys.stderr)
        return 1
    if args.nei_reference and not (output / "nei-reference" / "summary.json").is_file():
        print("The game exited without publishing the requested NEI reference summary", file=sys.stderr)
        return 1
    result = subprocess.run(
        [str(interpreter), "-m", "gtnh_data", "import", str(output),
         "--database", str(output / "index.sqlite")],
        cwd=root, check=False,
    )
    if result.returncode == 0:
        print(f"Offline dataset ready: {output / 'index.sqlite'}", flush=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
