#!/usr/bin/env bash
# Phase 1: screenshot Apple's own apps in every pose → raw/apple-apps/<app>/<pose>.png
# Same pose-control caveat as run-probe.sh. Only apps present on the simulator can be captured: the iOS 27.1
# simulator runtime (24A94425) ships Settings and Safari only. The other apps below are skipped there ("skip <app>")
# and, like Mail and Music, need a physical Duo; their NOTES.md say so.
set -euo pipefail
UDID="${DUO_UDID:?}"
OUT="$(cd "$(dirname "$0")/.." && pwd)/raw/apple-apps"
APPS=(
  "settings|com.apple.Preferences"
  "notes|com.apple.mobilenotes"
  "photos|com.apple.mobileslideshow"
  "calendar|com.apple.mobilecal"
  "reminders|com.apple.reminders"
  "safari|com.apple.mobilesafari"
  "maps|com.apple.Maps"
  "files|com.apple.DocumentsApp"
  "contacts|com.apple.MobileAddressBook"
)
# duo.py terms: "sideways" = crease top to bottom (book, cover held normally); "upright" = crease across.
POSES=("closed|close|sideways" "closed-sideways|close|upright" "book|book|sideways" "laptop|laptop|upright" "tent|laptop|landscape-right" "flat-sideways|open|sideways" "flat-upright|open|upright")

set_pose() { if [ -n "${DUO_PY:-}" ]; then python3 "$DUO_PY" fold "$1"; sleep 2; python3 "$DUO_PY" orient "$2"; else echo ">>> set fold=$1 orient=$2 in Device Hub, then Enter"; read -r; fi; }
# shot <dir> <label>: duo.py writes <label>-cover.png or <label>-inner.png (the display that was drawing).
shot() { if [ -n "${DUO_PY:-}" ]; then python3 "$DUO_PY" shot --out "$1" --name "$2" >/dev/null || echo "  no shot: $1/$2"; else xcrun simctl io "$UDID" screenshot "$1/$2.png"; fi; }

for entry in "${POSES[@]}"; do
  IFS='|' read -r label fold orient <<<"$entry"
  set_pose "$fold" "$orient"; sleep 3
  for a in "${APPS[@]}"; do
    IFS='|' read -r name bundle <<<"$a"
    mkdir -p "$OUT/$name"
    xcrun simctl launch "$UDID" "$bundle" >/dev/null 2>&1 || { echo "skip $name"; continue; }
    sleep 6   # 3 s caught Settings blank on its first launch
    shot "$OUT/$name" "$label"
    # Record one line per capture: what moved, where the controls went. Fill by hand after looking.
    grep -q "^$label|" "$OUT/$name/NOTES.md" 2>/dev/null || echo "$label| (bars: ) (fold handling: ) (what moved: )" >> "$OUT/$name/NOTES.md"
  done
done
echo "done → $OUT"
