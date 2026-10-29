#!/usr/bin/env bash
# Drive the iPhone Duo simulator through the pose set, run DuoProbe in each pose,
# pull metrics.jsonl and screenshots into raw/.
#
# FACT (2026-10-24): there is no public `xcrun simctl` or XCTest API that folds the simulator.
# Poses are set either by Device Hub's buttons (Closed / Book / Open / Rotate Right) or by the
# community driver `duo.py` from github.com/WhitenWhiten/iphone-duo-simulator-skill, which this
# script uses when DUO_PY is set. Without it the script pauses and asks you to set each pose by hand.
#
# Usage:
#   DUO_UDID=<udid> [DUO_PY=/path/to/duo.py] scripts/run-probe.sh
# Requires: Xcode 27.1, the DuoProbe app built and installed on the simulator (see Probe/README.md).
set -euo pipefail

BUNDLE=dev.enchiridion.duopatterns.probe
UDID="${DUO_UDID:?set DUO_UDID to the iPhone Duo simulator UDID (xcrun simctl list devices | grep -i duo)}"
OUT="$(cd "$(dirname "$0")/.." && pwd)/raw"
SHOTS="$OUT/apple-apps/_probe"
mkdir -p "$SHOTS"
SETTLE="${SETTLE:-4}"   # seconds; the crease activates ~1 s after the hinge stops (community measurement)

# label | fold | orientation, in duo.py's terms: "sideways" has the crease running top to bottom
# (the open phone's native pose, a book; the cover held normally), "upright" has it running across
# (laptop; the cover turned). Measured in duo.py's SKILL.md: shut 466x678, open sideways 951x669.
POSES=(
  "closed|close|sideways"
  "closed-sideways|close|upright"
  "book|book|sideways"
  "laptop|laptop|upright"
  "tent|laptop|landscape-right"   # standing on its edges, hinge up: laptop's fold turned 180° (inferred; check the shot)
  "flat-sideways|open|sideways"
  "flat-upright|open|upright"
)

set_pose() { # fold orient
  if [ -n "${DUO_PY:-}" ]; then
    python3 "$DUO_PY" fold "$1"
    sleep 2   # an orientation posted while the hinge still moves can be dropped
    python3 "$DUO_PY" orient "$2"
  else
    echo ">>> Set the simulator to fold=$1 orient=$2 in Device Hub (Xcode 27.1: Contents/Applications/DeviceHub.app), then press Enter"; read -r
  fi
}

xcrun simctl boot "$UDID" 2>/dev/null || true
xcrun simctl terminate "$UDID" "$BUNDLE" 2>/dev/null || true

for entry in "${POSES[@]}"; do
  IFS='|' read -r label fold orient <<<"$entry"
  # ONLY="tent flat-upright" re-runs just those poses; samples from earlier runs stay in the app's log.
  if [ -n "${ONLY:-}" ] && [[ " $ONLY " != *" $label "* ]]; then continue; fi
  echo "== pose $label"
  set_pose "$fold" "$orient"
  sleep "$SETTLE"
  # Relaunch per pose so each label gets a clean first-frame sample.
  xcrun simctl terminate "$UDID" "$BUNDLE" 2>/dev/null || true
  xcrun simctl launch "$UDID" "$BUNDLE" -label "$label" -overlay 1 >/dev/null
  sleep "$SETTLE"
  # Screenshot. On the Duo, `simctl io screenshot` may capture the display that is switched off;
  # prefer duo.py shot (captures whichever display is drawing) when available.
  if [ -n "${DUO_PY:-}" ]; then
    # Writes $label-cover.png or $label-inner.png, naming the display that was drawing.
    python3 "$DUO_PY" shot --out "$SHOTS" --name "$label" || true
  else
    xcrun simctl io "$UDID" screenshot "$SHOTS/$label.png" || true
  fi
  # Fold transition within the same launch: go flat and back so sinceLastChange captures settle timing.
  if [ -n "${DUO_PY:-}" ] && [ "$fold" != "open" ]; then
    python3 "$DUO_PY" fold open; sleep "$SETTLE"; python3 "$DUO_PY" fold "$fold"; sleep "$SETTLE"
  fi
done

CONTAINER=$(xcrun simctl get_app_container "$UDID" "$BUNDLE" data)
cp "$CONTAINER/Documents/metrics.jsonl" "$OUT/metrics.jsonl"
echo "wrote $OUT/metrics.jsonl ($(wc -l < "$OUT/metrics.jsonl") samples) and $SHOTS/*.png"
