#!/usr/bin/env bash
# Mac phase step 4: screenshot a corpus app's deeper screens in every pose.
#
# Taps land only on the shut phone. For every screen: fold shut → launch and tap through the flow once
# (Tap/DuoTapUITests, an XCUITest bundle with no host app) → while that test holds the app in front, every pose in
# turn: shut again, check the shut phone still shows the screen, fold and turn into the pose, shot → release the test.
# Every inner pose is opened from the shut phone, as a person opens it. When the shut phone has lost the screen on the
# way back from a pose (state lost on the fold, EVAL.md R4), the line says so, naming that pose (T7 belongs to its cell),
# and the runner relaunches the app and taps again before the next pose; FRESH=1 does that before every inner pose, as
# a capture of one cell per launch would. Every screen or pose it could not capture gets a line with "skipped".
#
# Usage:
#   DUO_UDID=<udid> DUO_PY=/path/to/duo.py DUO_TAP_XCTESTRUN=/path/to/DuoTapUITests_*.xctestrun \
#     scripts/capture-corpus-flow.sh <name> <bundle-id> '<screen>=<tap>;<tap>;…' …
# A tap is an accessibility label or identifier (exact, else a case-insensitive substring of a label); "launch="
# is the launch screen with no taps. Other steps: type:<text>, try:<label> (only if present),
# springboard:<alert button> (only if an alert is up), cell:<n> (the n-th hittable cell from the top, 1-based, for
# lists whose rows are other people's content), wait:<seconds>. ONLY="book laptop" limits poses. WAIT (default 6) is
# the settle after launch, TAP_WAIT (default 2) after each tap; TAP_TIMEOUT (default 150) is how long the runner has to
# launch and reach a screen before it is skipped. APP_PATH=<.app> reinstalls the app before every screen,
# for apps that remember their onboarding (Signal). LAUNCH_ARGS="A B" passes launch arguments to the app (an app's own
# UI-test switches). Build the runner once: see Tap/README.md.
# Shots → raw/corpus/evidence/<name>/<screen>-<pose>-<panel>.png (from the skill's copy: .duo/captures/<name>/; OUT=<dir>
# puts them elsewhere); xcodebuild logs and the shut-phone snapshots → $XCODE_OUT (scratch). SNAPSHOT=1 also asks the
# runner, once the phone is in the pose and shot, for the app's accessibility tree: <screen>-<pose>.json next to the
# shot, for the detectors (swift run duo-detect <dir>); a screen's snapshots in the poses asked for are removed first,
# so a pose this pass skips reads as not captured, not as an earlier pass's tree. ON_SHOT='<command>' runs after each
# pose of each screen with three arguments, the screen, the pose and the shot's path (capture-app.sh uses it to keep
# .duo/migration.json current).
set -euo pipefail

NAME="${1:?app name}"; BUNDLE="${2:?bundle id}"; shift 2
UDID="${DUO_UDID:?set DUO_UDID}"
DUO_PY="${DUO_PY:?set DUO_PY to duo.py}"
XCTESTRUN="${DUO_TAP_XCTESTRUN:?set DUO_TAP_XCTESTRUN to the DuoTapUITests .xctestrun}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
# In this repository shots go to raw/corpus/evidence; the skill's copy (skills/foldsmith-duo/tools) has no raw/
# and writes under the app being migrated instead.
if [ -d "$ROOT/raw/corpus" ]; then OUT="${OUT:-$ROOT/raw/corpus/evidence/$NAME}"; else OUT="${OUT:-$PWD/.duo/captures/$NAME}"; fi
XOUT="${XCODE_OUT:-$(mktemp -d -t duo-tap)}"
mkdir -p "$OUT" "$XOUT"
WAIT="${WAIT:-6}"; TAP_WAIT="${TAP_WAIT:-2}"; TAP_TIMEOUT="${TAP_TIMEOUT:-150}"
bounded() { perl -e 'alarm shift; exec @ARGV' "$@"; }   # a hung app can hang simctl with it: give up after N seconds

[ "$#" -gt 0 ] || set -- "launch="
SCREENS=("$@")

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

SELECTED=()
for entry in "${POSES[@]}"; do
  label="${entry%%|*}"
  if [ -z "${ONLY:-}" ] || [[ " $ONLY " == *" $label "* ]]; then SELECTED+=("$entry"); fi
done
[ "${#SELECTED[@]}" -gt 0 ] || { echo "ONLY=\"$ONLY\" names none of the poses" >&2; exit 2; }

# Fold and turn the phone, skipping what is already so; a fold always posts the orientation after it.
FOLD_NOW=; ORIENT_NOW=
pose_to() {
  if [ "$1" != "$FOLD_NOW" ]; then python3 "$DUO_PY" fold "$1" >/dev/null; sleep 2; FOLD_NOW=$1; ORIENT_NOW=; fi
  if [ "$2" != "$ORIENT_NOW" ]; then python3 "$DUO_PY" orient "$2" >/dev/null; sleep 3; ORIENT_NOW=$2; fi
}
# Waits for the runner to write $1 (or failed, or to exit), at most $2 seconds; prints what happened.
await() {
  local waited=0
  while [ "$waited" -lt "$(( $2 * 2 ))" ]; do
    if [ -e "$FLAGS/$1" ]; then echo "$1"; return; fi
    if [ -e "$FLAGS/failed" ]; then echo failed; return; fi
    if ! kill -0 "$XB" 2>/dev/null; then echo exited; return; fi
    sleep 0.5; waited=$((waited+1))
  done
  echo timeout
}
# The app's accessibility tree as the runner sees it now, copied to $1.
snapshot_to() {
  rm -f "$FLAGS/snapped" "$FLAGS/snapshot.json"; touch "$FLAGS/posed"
  [ "$(await snapped 60)" = snapped ] && [ -s "$FLAGS/snapshot.json" ] && cp "$FLAGS/snapshot.json" "$1"
}
# The runner relaunches the app and taps through the flow again.
retap() {
  rm -f "$FLAGS/tapped" "$FLAGS/failed"; touch "$FLAGS/again"
  [ "$(await tapped "$TAP_TIMEOUT")" = tapped ]
}
release() { touch "$FLAGS/release"; wait "$XB" 2>/dev/null || true; rm -rf "$FLAGS"; }
# Whether a snapshot's window is taller than wide (the cover upright).
tall() { python3 -c 'import json, sys; w, h = json.load(open(sys.argv[1]))["window"]; sys.exit(0 if h > w else 1)' "$1"; }

for s in "${SCREENS[@]}"; do
  screen="${s%%=*}"; taps="${s#*=}"
  echo "== $screen"
  if [ "${SNAPSHOT:-0}" = 1 ]; then
    for entry in "${SELECTED[@]}"; do rm -f "${OUT:?}/$screen-${entry%%|*}.json"; done
  fi
  # 1. shut, cover upright: the only state a tap reaches. Some apps (Wikipedia) take an orientation only while
  #    they run, so a change posted with nothing in front leaves the next launch landscape: launch the app, turn
  #    the cover away and back while it is up, and the runner's relaunch then comes up upright. PRIME=0 skips it.
  pose_to close sideways
  if [ -n "${APP_PATH:-}" ]; then   # an app that remembers its onboarding: start every screen from a fresh install
    xcrun simctl terminate "$UDID" "$BUNDLE" 2>/dev/null || true
    xcrun simctl uninstall "$UDID" "$BUNDLE" 2>/dev/null || true
    xcrun simctl privacy "$UDID" reset all "$BUNDLE" 2>/dev/null || true   # a prompt left unanswered is re-raised at every launch
    xcrun simctl install "$UDID" "$APP_PATH" >/dev/null
  fi
  if [ "${PRIME:-1}" = 1 ]; then
    bounded 30 xcrun simctl terminate "$UDID" "$BUNDLE" 2>/dev/null || true
    bounded 60 xcrun simctl launch "$UDID" "$BUNDLE" >/dev/null 2>&1 || true; sleep 4
    python3 "$DUO_PY" orient upright >/dev/null; sleep 3
    python3 "$DUO_PY" orient sideways >/dev/null; sleep 4
  fi
  # 2. launch, tap, hold (the test runner); hand-off through flag files in a scratch dir
  FLAGS=$(mktemp -d -t duo-flags)
  TEST_RUNNER_DUO_BUNDLE="$BUNDLE" TEST_RUNNER_DUO_TAPS="$taps" TEST_RUNNER_DUO_FLAGS="$FLAGS" TEST_RUNNER_DUO_ARGS="${LAUNCH_ARGS:-}" \
  TEST_RUNNER_DUO_WAIT="$WAIT" TEST_RUNNER_DUO_TAP_WAIT="$TAP_WAIT" TEST_RUNNER_DUO_HOLD="$TAP_TIMEOUT" \
    xcodebuild test-without-building -xctestrun "$XCTESTRUN" -derivedDataPath "$XOUT/DerivedData" \
      -destination "platform=iOS Simulator,id=$UDID" > "$XOUT/$screen.log" 2>&1 &
  XB=$!
  state=$(await tapped "$TAP_TIMEOUT")
  cp "$FLAGS/hierarchy.txt" "$XOUT/$screen.hierarchy.txt" 2>/dev/null || true
  cp "$FLAGS/hierarchy-after.txt" "$XOUT/$screen.hierarchy-after.txt" 2>/dev/null || true
  if [ "$state" != tapped ]; then
    case "$state" in
      failed) echo "  $screen: skipped in every pose: $(cat "$FLAGS/failed")";;
      exited) echo "  $screen: skipped in every pose: test runner exited early (see $XOUT/$screen.log)";;
      *) echo "  $screen: skipped in every pose: no tap within ${TAP_TIMEOUT}s";;
    esac
    cp "$FLAGS/screen.png" "$XOUT/$screen.screen.png" 2>/dev/null || true
    release; continue
  fi
  # The screen as the shut phone shows it after the taps: what the shut phone must show again before each inner pose.
  ref="$XOUT/$screen.shut.json"; rm -f "$ref"; snapshot_to "$ref" || true
  # 3. every pose in turn while the runner holds the app
  prev=
  for entry in "${SELECTED[@]}"; do
    IFS='|' read -r label fold orient <<<"$entry"
    if [ "$fold" != close ]; then
      pose_to close sideways
      if [ "${FRESH:-0}" = 1 ]; then
        retap || { echo "  $screen: skipped in $label: the relaunch did not reach the screen: $(cat "$FLAGS/failed" 2>/dev/null)"; continue; }
      elif [ -s "$ref" ] && snapshot_to "$XOUT/$screen-$label.shut.json"; then
        if ! tall "$XOUT/$screen-$label.shut.json"; then
          # back from laptop or tent the cover can stay landscape: turn it away and back, as for a shot of the wrong shape
          python3 "$DUO_PY" orient upright >/dev/null; sleep 3
          python3 "$DUO_PY" orient sideways >/dev/null; sleep 3
          snapshot_to "$XOUT/$screen-$label.shut.json" || true
        fi
        if ! score=$(python3 "$HERE/same-screen.py" "$ref" "$XOUT/$screen-$label.shut.json"); then
          since="after $prev"; [ -n "$prev" ] || since="since the taps"
          echo "  $screen: the shut phone lost the screen $since (similarity $score): relaunched before $label"
          retap || { echo "  $screen: skipped in $label: the relaunch did not reach the screen: $(cat "$FLAGS/failed" 2>/dev/null)"; continue; }
        fi
      fi
    fi
    pose_to "$fold" "$orient"
    python3 "$DUO_PY" shot --out "$OUT" --name "$screen-$label" >/dev/null || echo "  $screen: no shot in $label"
    if [ "$(shot_shape "$screen" "$label")" != "$(expected_shape "$label")" ]; then
      # a repeat of the same orientation can be a no-op for the app: post the other one first, then this one
      other=$([ "$orient" = sideways ] && echo upright || echo sideways)
      python3 "$DUO_PY" orient "$other" >/dev/null; sleep 3
      python3 "$DUO_PY" orient "$orient" >/dev/null; sleep "$WAIT"
      python3 "$DUO_PY" shot --out "$OUT" --name "$screen-$label" >/dev/null || true
      [ "$(shot_shape "$screen" "$label")" = "$(expected_shape "$label")" ] \
        || echo "  $screen: still $(shot_shape "$screen" "$label") in $label (expected $(expected_shape "$label")): app did not rotate"
    fi
    if [ "${SNAPSHOT:-0}" = 1 ]; then   # the tree as XCTest sees it in this pose, same moment as the shot
      snapshot_to "$OUT/$screen-$label.json" || echo "  $screen: no snapshot in $label $(cat "$FLAGS/snapped" 2>/dev/null)"
    fi
    shot="$OUT/$screen-$label-$(expected_panel "$label").png"
    [ -z "${ON_SHOT:-}" ] || [ ! -e "$shot" ] || bash -c "$ON_SHOT"' "$@"' _ "$screen" "$label" "$shot" || true
    echo "  $label"
    prev=$label
  done
  release
done
echo "done → $OUT"
