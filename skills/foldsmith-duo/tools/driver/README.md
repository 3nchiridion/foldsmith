# duo-driver

The simulator driver Foldsmith's capture tools use to fold, turn and shoot the iPhone Duo simulator: `duo.py` and the
helper it compiles, `duo_fold.c`. It is bundled so the skill downloads nothing when it runs: the skill's copy is
`tools/driver/` (made by `scripts/sync-skill-references.py`), and `tools/preflight.sh` writes its path to `.duo/env` as
`DUO_PY`. A `DUO_PY` you set yourself still wins.

| | |
|---|---|
| Upstream | https://github.com/WhitenWhiten/iphone-duo-simulator-skill |
| Commit | `60cdda2f487434c9c3cd4dad9431e12a48ec1d04` (2026-10-16, "Xcode 27.1 is released: drop the RC wording") |
| License | MIT, `LICENSE` here (the upstream file, unchanged) |
| Changes | None. Upstream `scripts/duo.py` → `duo.py` and `scripts/duo_fold.c` → `duo_fold.c`, byte for byte |

```
00fdbb32eb707a72abddd9103b4b7e1876f29e4e985f74f9a87e86c6fc445822  duo.py
ab2654871703e47eedc00ac2c32282a8e9946e2fbc0d45ffcf45fc4f3295c55c  duo_fold.c
7aa37053a7179baaac130c0f999fc1c7817b9ccacc596eeff8bbf457fdb0f741  LICENSE
```

`duo.py` imports only the Python standard library and finds `duo_fold.c` next to itself, so the two travel together.
Not copied: the upstream `SKILL.md` (agent instructions, never reviewed here), `duo3d.py`, `duo_mockup.py` and
`xcode_device.py`, which Foldsmith's tools do not use.

## What it does on the Mac
- Lists simulators (`xcrun simctl list devices available -j`) and drives only those whose name contains "duo" (any
  case). A Duo simulator renamed without it is invisible to it: `tools/preflight.sh` says so and prints the rename.
- Boots the Duo simulator it is given when it is shut down (`simctl boot`, `simctl bootstatus`).
- Compiles `duo_fold.c` once with `xcrun -sdk iphonesimulator clang`, signs it ad hoc (`codesign -s -`) and caches it in
  `~/.cache/duo-kit` (`DUO_KIT_CACHE`), keyed by the source's hash, with the pose it last set. It runs the helper inside
  the simulator (`simctl spawn`) to post the hinge and orientation events Xcode's Device Hub posts.
- Reads which panel is lit (`xcrun devicectl device info displays`), captures and films it (`simctl io screenshot`,
  `simctl io recordVideo`), and launches and terminates apps (`simctl launch`, `simctl terminate`).

It never creates, clones, erases or shuts down a simulator, never runs `simctl io … screenConfig` (on a Duo that leaves
SpringBoard crash-looping), and makes no network request.

## Updating it
Copy the two files from a newer upstream commit unchanged, update the table and the hashes above, run
`python3 scripts/sync-skill-references.py`, and run G2 (`EVAL.md`) before release: the goldens were captured with this
commit.
