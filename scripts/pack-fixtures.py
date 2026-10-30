#!/usr/bin/env python3
"""Pack the evidence the tests read into Tests/Fixtures/, from the evidence repository (3nchiridion/foldsmith-evidence,
checked out beside this one or at $FOLDSMITH_EVIDENCE):

  verification/matrices/<pattern>/<config>-<pose>.json      → Tests/Fixtures/matrices.json              (one object:
  verification/accessibility/catalog/<name>.json             → Tests/Fixtures/accessibility-catalog.json   path → text)
  verification/runs/<app>/{migration.json,detectors-*.md}    → Tests/Fixtures/runs/<app>/                  (copied)

Two packed files instead of 238 small ones keep a clone small on disk; the Swift tests unpack them into a temporary
folder (Tests/DuoPoseTestingTests/Fixtures.swift). scripts/capture-catalog.sh runs this after a capture.

    python3 scripts/pack-fixtures.py          # write
    python3 scripts/pack-fixtures.py --check  # exit 1 if Tests/Fixtures differs from the evidence repository
"""
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
EVIDENCE = pathlib.Path(os.environ.get("FOLDSMITH_EVIDENCE", ROOT.parent / "foldsmith-evidence"))
FIXTURES = ROOT / "Tests" / "Fixtures"
RUN_FILES = ("migration.json", "detectors-before.md", "detectors-after.md")


def packed(folder, pattern):
    files = {p.relative_to(folder).as_posix(): p.read_text() for p in sorted(folder.glob(pattern))}
    return json.dumps(files, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def plan():
    out = {
        "matrices.json": packed(EVIDENCE / "verification/matrices", "*/*.json"),
        "accessibility-catalog.json": packed(EVIDENCE / "verification/accessibility/catalog", "*.json"),
    }
    for app in sorted(p for p in (EVIDENCE / "verification/runs").iterdir() if p.is_dir()):
        for name in RUN_FILES:
            if (app / name).exists():
                out[f"runs/{app.name}/{name}"] = (app / name).read_text()
    return out


def main():
    check = "--check" in sys.argv
    if not (EVIDENCE / "verification").is_dir():
        sys.exit(f"no evidence repository at {EVIDENCE}: check out 3nchiridion/foldsmith-evidence beside this one, "
                 "or set FOLDSMITH_EVIDENCE")
    stale = []
    for rel, text in plan().items():
        target = FIXTURES / rel
        if target.exists() and target.read_text() == text:
            continue
        stale.append(rel)
        if not check:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
    if check and stale:
        sys.exit("out of date: " + ", ".join(stale) + "\nrun: python3 scripts/pack-fixtures.py")
    print("up to date" if not stale else ("would update " if check else "updated ") + ", ".join(stale))


if __name__ == "__main__":
    main()
