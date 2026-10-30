#!/usr/bin/env bash
# The skill's capture in one command: every screen of a flow file in every pose, each with its accessibility snapshot,
# then the detectors over all of it.
#
# Usage:
#   DUO_UDID=<udid> DUO_PY=/path/to/duo.py DUO_TAP_XCTESTRUN=/path/to/DuoTapUITests_*.xctestrun \
#     capture-app.sh <flow-file> <out-dir>
# The flow file is shell: BUNDLE=<bundle id>, optional LAUNCH_ARGS="…" and APP_PATH=<.app>, and
# SCREENS=( "<screen>=<tap>;<tap>" … ) with the taps capture-corpus-flow.sh takes (its header has the syntax).
# The app must already be built and installed. Shots, <screen>-<pose>.json snapshots and capture.txt go to <out-dir>;
# the detectors write <out-dir>/detectors.md and their summary line to <out-dir>/findings.txt. ONLY="book laptop"
# limits poses, as for capture-corpus-flow.sh, and SCREEN="settings status" limits screens, by their names in the flow:
# together they probe one screen behind taps in the poses a change touches (into a scratch <out-dir>, so no cell
# changes). TAP_TIMEOUT (default 150 s) is how long a screen's taps may take before it is skipped. When <out-dir> is a
# `before` or `after` folder and the progress file exists (PROGRESS, default .duo/migration.json), each shot's path is
# written to its cell as it lands, so the Foldsmith pane shows the capture as it goes.
# Exit 0 when every screen was captured in every pose asked for; 3 when any was skipped (the lines are repeated at the
# end and in findings.txt), so a missing screen is never read as a clean one. A SCREEN= recapture into a folder that
# has a capture adds to its capture.txt under a "recaptured" line instead of replacing it, so the first pass's lines (a
# lost screen, a skip) stay on record. Each screen's latest capture in the file decides: a screen skipped in an earlier
# pass and not captured since still counts as missing, whichever screens this run took.
set -euo pipefail

FLOW="${1:?flow file}"; OUT="${2:?output directory}"
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$FLOW" ] || { echo "no flow file $FLOW" >&2; exit 2; }
BUNDLE=; LAUNCH_ARGS=; APP_PATH=; SCREENS=()
# shellcheck source=/dev/null
source "$FLOW"
[ -n "$BUNDLE" ] && [ ${#SCREENS[@]} -gt 0 ] || { echo "$FLOW sets no BUNDLE or SCREENS" >&2; exit 2; }
NAME="$(basename "$FLOW" .flow)"
if [ -n "${SCREEN:-}" ]; then
  PICKED=()
  for s in "${SCREENS[@]}"; do [[ " $SCREEN " == *" ${s%%=*} "* ]] && PICKED+=("$s"); done
  [ ${#PICKED[@]} -gt 0 ] || { echo "SCREEN=\"$SCREEN\" names none of the flow's screens" >&2; exit 2; }
  SCREENS=("${PICKED[@]}")
fi

mkdir -p "$OUT"
if [ -n "${SCREEN:-}" ] && [ -f "$OUT/capture.txt" ]; then
  echo "recaptured: $SCREEN, $(date -u +%Y-%m-%dT%H:%M:%SZ), flow sha256 $(shasum -a 256 "$FLOW" | cut -d' ' -f1)" \
    >> "$OUT/capture.txt"
else
  {
    echo "app: $NAME ($BUNDLE)"
    echo "flow: $FLOW sha256 $(shasum -a 256 "$FLOW" | cut -d' ' -f1)"
    echo "captured: $(date -u +%Y-%m-%dT%H:%M:%SZ) on $(xcrun simctl list devices | grep -F "$DUO_UDID" | sed 's/^ *//')"
  } > "$OUT/capture.txt"
fi

PROGRESS="${PROGRESS:-.duo/migration.json}"; ON_SHOT=
KIND="$(basename "$OUT")"
if [ -f "$PROGRESS" ] && { [ "$KIND" = before ] || [ "$KIND" = after ]; }; then
  ON_SHOT="python3 '$HERE/progress.py' --file '$PROGRESS' shot $KIND"
fi

OUT="$OUT" SNAPSHOT=1 WAIT="${WAIT:-6}" TAP_WAIT="${TAP_WAIT:-2}" LAUNCH_ARGS="$LAUNCH_ARGS" APP_PATH="$APP_PATH" \
  ONLY="${ONLY:-}" ON_SHOT="$ON_SHOT" bash "$HERE/capture-corpus-flow.sh" "$NAME" "$BUNDLE" "${SCREENS[@]}" | tee -a "$OUT/capture.txt"

# The detectors: the skill's own package (tools/detect), built outside the skill's folder, or this repository's.
PKG="$HERE/detect"; BUILD=(--scratch-path "$HOME/Library/Caches/duo-detect")
[ -f "$PKG/Package.swift" ] || { PKG="$HERE/.."; BUILD=(); }
swift run -c release --package-path "$PKG" ${BUILD[@]+"${BUILD[@]}"} duo-detect "$OUT" --markdown "$OUT/detectors.md" \
  | grep -v '^\[' > "$OUT/findings.txt"
tail -1 "$OUT/findings.txt"
# The skip lines of each screen's latest capture ("== <screen>" starts one).
SKIPPED="$(awk '/^== / { cur = substr($0, 4); lines[cur] = ""; next }
                /skipped/ && cur != "" { lines[cur] = lines[cur] $0 "\n" }
                END { for (s in lines) printf "%s", lines[s] }' "$OUT/capture.txt")"
if [ -n "$SKIPPED" ]; then
  echo "$SKIPPED" | tee -a "$OUT/findings.txt" >&2
  echo "not captured: $(echo "$SKIPPED" | wc -l | tr -d ' ') line(s) above; those cells are not clean, they are missing" >&2
  exit 3
fi
