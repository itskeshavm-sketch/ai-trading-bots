"""Build the Agensi skill package zip from the repo copy.

Keeps the shipped zip in sync with agensi/paper-trading-desk/ - no manual
copying, no drift.

    python tools/build_skill_package.py
    python tools/build_skill_package.py --version 1.1.0
"""
import argparse
import os
import shutil
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(REPO, "agensi", "paper-trading-desk")
DIST = os.path.join(REPO, "dist")
SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache"}
SKIP_FILES = {".DS_Store"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="1.0.0")
    ap.add_argument("--out-dir", default=DIST)
    args = ap.parse_args()

    if not os.path.isdir(SKILL_DIR):
        print(f"Skill folder missing: {SKILL_DIR}", file=sys.stderr)
        return 1

    os.makedirs(args.out_dir, exist_ok=True)
    zip_path = os.path.join(args.out_dir, f"paper-trading-desk-v{args.version}.zip")

    count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(SKILL_DIR):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for name in sorted(files):
                if name in SKIP_FILES or name.endswith(".pyc"):
                    continue
                full = os.path.join(root, name)
                rel = os.path.relpath(full, REPO)
                zf.write(full, rel)
                count += 1

    size = os.path.getsize(zip_path)
    print(f"Wrote {zip_path} ({count} files, {size} bytes)")
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
