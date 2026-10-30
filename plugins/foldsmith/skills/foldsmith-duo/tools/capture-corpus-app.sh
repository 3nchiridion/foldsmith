#!/usr/bin/env bash
# Mac phase step 4: screenshot one corpus app in every pose → foldsmith-evidence's
# raw/corpus/evidence/<name>/<screen>-<pose>-<panel>.png
#
# Usage:
#   DUO_UDID=<udid> DUO_PY=/path/to/duo.py scripts/capture-corpus-app.sh <name> <bundle-id> [<screen>=<url> ...]
# Without screens it captures the launch screen as "launch". Each <screen>=<url> is opened with `simctl openurl`
# after launch; a screen whose URL fails is noted and skipped. A custom URL scheme raises an "Open in <app>?" system
# alert that nothing headless can answer on the open phone, so prefer launch screens and universal links.
# Each shot is checked against the pose's shape (tall or wide); on a mismatch the orientation is posted again and
# the shot retaken once. A mismatch that remains is printed: the app did not rotate (a finding, not a capture error).
# The app must already be built and installed on the simulator. Same pose set and duo.py terms as run-probe.sh.
set -euo pipefail

NAME="${1:?app name}"; BUNDLE="${2:?bundle id}"; shift 2
UDID="${DUO_UDID:?set DUO_UDID}"
DUO_PY="${DUO_PY:?set DUO_PY to duo.py}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
# Run from Foldsmith's scripts/, shots go to raw/corpus/evidence/<name>/ in the evidence repository (foldsmith-evidence
# beside this one, or at $FOLDSMITH_EVIDENCE); the skill's copy (skills/foldsmith-duo/tools) has no evidence repository
# and writes under the app being migrated instead. OUT=<dir> puts them elsewhere.
EV="${FOLDSMITH_EVIDENCE:-$ROOT/../foldsmith-evidence}"
if [ "$(basename "$HERE")" = scripts ]; then
  [ -n "${OUT:-}" ] || [ -d "$EV/raw/corpus" ] || { echo "no foldsmith-evidence checkout at $EV (clone it beside this repository, set FOLDSMITH_EVIDENCE, or pass OUT)" >&2; exit 2; }
  OUT="${OUT:-$EV/raw/corpus/evidence/$NAME}"
else
  OUT="${OUT:-$PWD/.duo/captures/$NAME}"
fi
mkdir -p "$OUT"
WAIT="${WAIT:-6}"   # seconds after launch or openurl before the shot

SCREENS=("launch=")
for s in "$@"; do SCREENS+=("$s"); done

# label | fold | orientation (duo.py: "sideways" = crease top to bottom, "upright" = crease across)
POSES=(
  "closed|close|sideways"
  "closed-sideways|close|upright"
  "book|book|sideways"
  "laptop|laptop|upright"
  "tent|laptop|landscape-right"
  "flat-sideways|open|sideways"
  "flat-upright|open|upright"
)

expected_shape() { case "$1" in closed-sideways|book|flat-sideways) echo wide;; *) echo tall;; esac; }
expected_panel() { case "$1" in closed|closed-sideways) echo cover;; *) echo inner;; esac; }
keep_panel() { # duo.py saves both panels when it cannot tell which one is drawing (a dark screen): keep the pose's
  local other; other=$([ "$(expected_panel "$2")" = cover ] && echo inner || echo cover)
  [ -e "$OUT/$1-$2-$(expected_panel "$2").png" ] && rm -f "$OUT/$1-$2-$other.png"
}
shot_shape() { # the pose's panel for this screen → wide | tall | none
  keep_panel "$1" "$2"
  local f="$OUT/$1-$2-$(expected_panel "$2").png"; [ -e "$f" ] || { echo none; return; }
  local w h; w=$(sips -g pixelWidth "$f" | awk '/pixelWidth/{print $2}'); h=$(sips -g pixelHeight "$f" | awk '/pixelHeight/{print $2}')
  if [ "$w" -gt "$h" ]; then echo wide; else echo tall; fi
}

for entry in "${POSES[@]}"; do
  IFS='|' read -r label fold orient <<<"$entry"
  if [ -n "${ONLY:-}" ] && [[ " $ONLY " != *" $label "* ]]; then continue; fi
  echo "== pose $label"
  python3 "$DUO_PY" fold "$fold" >/dev/null
  sleep 2   # an orientation posted while the hinge still moves can be dropped
  python3 "$DUO_PY" orient "$orient" >/dev/null
  sleep 3
  for s in "${SCREENS[@]}"; do
    screen="${s%%=*}"; url="${s#*=}"
    xcrun simctl terminate "$UDID" "$BUNDLE" 2>/dev/null || true
    xcrun simctl launch "$UDID" "$BUNDLE" >/dev/null
    sleep "$WAIT"
    if [ -n "$url" ]; then
      xcrun simctl openurl "$UDID" "$url" 2>/dev/null || { echo "  $screen: openurl failed ($url)"; continue; }
      sleep "$WAIT"
    fi
    python3 "$DUO_PY" shot --out "$OUT" --name "$screen-$label" >/dev/null || echo "  $screen: no shot"
    if [ "$(shot_shape "$screen" "$label")" != "$(expected_shape "$label")" ]; then
      # a repeat of the same orientation can be a no-op for the app: post the other one first, then this one
      other=$([ "$orient" = sideways ] && echo upright || echo sideways)
      python3 "$DUO_PY" orient "$other" >/dev/null; sleep 3
      python3 "$DUO_PY" orient "$orient" >/dev/null; sleep "$WAIT"
      python3 "$DUO_PY" shot --out "$OUT" --name "$screen-$label" >/dev/null || true
      [ "$(shot_shape "$screen" "$label")" = "$(expected_shape "$label")" ] \
        || echo "  $screen: still $(shot_shape "$screen" "$label") in $label (expected $(expected_shape "$label")): app did not rotate"
    fi
    echo "  $screen"
  done
done
echo "done → $OUT"
