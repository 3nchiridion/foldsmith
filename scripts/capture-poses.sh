#!/usr/bin/env bash
# EVAL.md §4 step 2: screenshot one A/B app in every pose, the same way for every condition.
#
# Usage:
#   DUO_UDID=<udid> DUO_PY=/path/to/duo.py DUO_TAP_XCTESTRUN=/path/to/DuoTapUITests_*.xctestrun \
#     scripts/capture-poses.sh <app> <out-dir>
# <app> names a flow file, verification/ab/flows/<app>.flow: the bundle id, launch arguments and the screens with the
# taps that reach them, frozen before the runs. The app must already be built and installed. Every screen is shot in
# every pose with its accessibility snapshot (capture-corpus-flow.sh with SNAPSHOT=1), into <out-dir>/<app>/, then
# the detectors run over it: <out-dir>/<app>/detectors.md.
#
# Settle times are fixed here, not taken from the environment: identical poses, identical settle time (EVAL.md §4).
# A screen a migrated app no longer reaches by the frozen taps is reported as skipped, not re-tapped by hand.
# Screens a flow lists in REDACT (strangers' posts) are pixelated by scripts/redact-shots.py right after the capture,
# the same way in every condition.
set -euo pipefail

APP="${1:?app (a flow in verification/ab/flows)}"; DEST="${2:?output directory}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FLOW="$ROOT/verification/ab/flows/$APP.flow"
[ -f "$FLOW" ] || { echo "no flow file $FLOW" >&2; exit 2; }
BUNDLE=; LAUNCH_ARGS=; APP_PATH=; SCREENS=(); REDACT=()
# shellcheck source=/dev/null
source "$FLOW"
[ -n "$BUNDLE" ] && [ ${#SCREENS[@]} -gt 0 ] || { echo "$FLOW sets no BUNDLE or SCREENS" >&2; exit 2; }

OUT="$DEST/$APP"; mkdir -p "$OUT"
{
  echo "app: $APP ($BUNDLE)"
  echo "flow: verification/ab/flows/$APP.flow sha256 $(shasum -a 256 "$FLOW" | cut -d' ' -f1)"
  echo "captured: $(date -u +%Y-%m-%dT%H:%M:%SZ) on $(xcrun simctl list devices | grep -F "$DUO_UDID" | sed 's/^ *//')"
  echo "settle: WAIT=6 TAP_WAIT=2"
} > "$OUT/capture.txt"

OUT="$OUT" SNAPSHOT=1 WAIT=6 TAP_WAIT=2 LAUNCH_ARGS="$LAUNCH_ARGS" APP_PATH="$APP_PATH" ONLY="${ONLY:-}" \
  "$ROOT/scripts/capture-corpus-flow.sh" "$APP" "$BUNDLE" "${SCREENS[@]}" | tee -a "$OUT/capture.txt"

[ ${#REDACT[@]} -eq 0 ] || python3 "$ROOT/scripts/redact-shots.py" "$OUT" "${REDACT[@]}" | tee -a "$OUT/capture.txt"

(cd "$ROOT" && swift run -c release duo-detect "$OUT" --markdown "$OUT/detectors.md") | grep -v '^\[' > "$OUT/findings.txt"
tail -1 "$OUT/findings.txt"
