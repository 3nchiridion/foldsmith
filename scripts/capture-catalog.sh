#!/usr/bin/env bash
# Phase 3: capture the pattern catalog in every pose → verification/matrices/<pattern>/<config>-<pose>.{png,json}
#
# Usage:
#   DUO_UDID=<udid> DUO_PY=/path/to/duo.py scripts/capture-catalog.sh [<config> ...]
# A config is pattern:variant[:sheet]; without arguments every config below is captured. The catalog
# (Examples/Catalog) must already be built and installed on the simulator.
#
# Each shot is saved at point resolution (1 px = 1 pt, so pixel positions read as layout points) next to the
# catalog's own record of the same moment: frames-latest.json, the window frame of every tracked view plus the
# reserved regions and size classes the app saw. The detectors (swift run duo-detect) read the JSON; the PNGs are
# for people. Same pose set, duo.py terms and orientation retry as capture-corpus-app.sh.
# OUT=<dir> captures somewhere else (scripts/diff-matrix.py compares that against the committed goldens, gate G2);
# ONLY="book laptop" limits the poses.
set -euo pipefail

UDID="${DUO_UDID:?set DUO_UDID}"
DUO_PY="${DUO_PY:?set DUO_PY to duo.py}"
BUNDLE=dev.enchiridion.duopatterns.catalog
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${OUT:-$ROOT/verification/matrices}"
WAIT="${WAIT:-6}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

CONFIGS=("$@")
[ ${#CONFIGS[@]} -gt 0 ] || CONFIGS=(
  split:system split:fixed split:aligned
  split:system:sheet split:aligned:sheet
  split:three split:three-list
  split:tiled split:tiled-three split:tiled-three-list
  grid:naive grid:aligned
  columns:single columns:aligned
  arrangement:inline arrangement:aligned arrangement:overlay
)
# The catalog falls back to the reference for an unknown variant, which would file a wrong shot under a right name.
for config in "${CONFIGS[@]}"; do
  case "$config" in
    split:system|split:fixed|split:aligned|split:system:sheet|split:fixed:sheet|split:aligned:sheet) ;;
    split:three|split:three-list|split:tiled|split:tiled-three|split:tiled-three-list) ;;
    grid:naive|grid:aligned|columns:single|columns:aligned) ;;
    arrangement:inline|arrangement:aligned|arrangement:overlay) ;;
    *) echo "unknown config '$config' (pattern:variant[:sheet], e.g. split:aligned:sheet)" >&2; exit 2;;
  esac
done

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

frames() { echo "$(xcrun simctl get_app_container "$UDID" "$BUNDLE" data)/Documents/frames-latest.json"; }

# shoot <name> <pose>: duo.py shot into $TMP, keep the pose's panel, echo wide | tall | none
shoot() {
  rm -f "$TMP"/*.png
  python3 "$DUO_PY" shot --out "$TMP" --name "$1" >/dev/null || true
  local f="$TMP/$1-$(expected_panel "$2").png"; [ -e "$f" ] || { echo none; return; }
  local w h; w=$(sips -g pixelWidth "$f" | awk '/pixelWidth/{print $2}'); h=$(sips -g pixelHeight "$f" | awk '/pixelHeight/{print $2}')
  if [ "$w" -gt "$h" ]; then echo wide; else echo tall; fi
}

# keep <name> <pose> <dest-stem>: the shot at point scale (a third of the simulator's 3x pixels) and the frames
keep() {
  local f="$TMP/$1-$(expected_panel "$2").png" w
  w=$(sips -g pixelWidth "$f" | awk '/pixelWidth/{print $2}')
  sips --resampleWidth $(( (w + 1) / 3 )) "$f" --out "$3.png" >/dev/null
  cp "$(frames)" "$3.json" 2>/dev/null || echo "  no frames for $(basename "$3")"
}

for entry in "${POSES[@]}"; do
  IFS='|' read -r pose fold orient <<<"$entry"
  if [ -n "${ONLY:-}" ] && [[ " $ONLY " != *" $pose "* ]]; then continue; fi
  echo "== pose $pose"
  python3 "$DUO_PY" fold "$fold" >/dev/null
  sleep 2   # an orientation posted while the hinge still moves can be dropped
  python3 "$DUO_PY" orient "$orient" >/dev/null
  sleep 3
  for config in "${CONFIGS[@]}"; do
    IFS=':' read -r pattern variant sheet <<<"$config"
    name="$variant${sheet:+-sheet}"
    mkdir -p "$OUT/$pattern"
    args=(-pattern "$pattern" -variant "$variant"); [ -n "$sheet" ] && args+=(-sheet 1)
    xcrun simctl terminate "$UDID" "$BUNDLE" 2>/dev/null || true
    rm -f "$(frames)"
    xcrun simctl launch "$UDID" "$BUNDLE" "${args[@]}" >/dev/null
    sleep "$WAIT"
    shape=$(shoot "$name" "$pose")
    if [ "$shape" != "$(expected_shape "$pose")" ]; then
      other=$([ "$orient" = sideways ] && echo upright || echo sideways)
      python3 "$DUO_PY" orient "$other" >/dev/null; sleep 3
      python3 "$DUO_PY" orient "$orient" >/dev/null; sleep "$WAIT"
      shape=$(shoot "$name" "$pose")
      [ "$shape" = "$(expected_shape "$pose")" ] || echo "  $name: $shape in $pose (expected $(expected_shape "$pose"))"
    fi
    [ "$shape" = none ] && { echo "  $pattern/$name: no shot"; continue; }
    keep "$name" "$pose" "$OUT/$pattern/$name-$pose"
    echo "  $pattern/$name"
  done
done
xcrun simctl terminate "$UDID" "$BUNDLE" 2>/dev/null || true
echo "done → $OUT"
