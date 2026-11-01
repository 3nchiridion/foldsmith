#!/usr/bin/env bash
# Mac phase step 4: screenshot a corpus app's deeper screens in every pose.
#
# Taps land only on the shut phone. For every screen: fold shut → launch and tap through the flow once
# (Tap/DuoTapUITests, an XCUITest bundle with no host app) → while that test holds the app in front, every pose in
# turn: shut again, check the shut phone still shows the screen, fold and turn into the pose, shot → release the test.
# Every inner pose is opened from the shut phone, as a person opens it. When the shut phone has lost the screen on the
# way back from a pose (state lost on the fold, EVAL.md R4), the line says so, naming that pose (T7 belongs to its cell),
# and the runner relaunches the app and taps again before the next pose; FRESH=1 does that before every inner pose, as
# a capture of one cell per launch would. Every screen or pose it could not capture gets a line with "skipped" (taps
# that reach nothing, a relaunch that does not, no shot, no snapshot). A snapshot taken while the app was not in front
# (it crashed or quit on the way to the pose) gets a line saying so.
#
# Usage:
#   DUO_UDID=<udid> DUO_TAP_XCTESTRUN=/path/to/DuoTapUITests_*.xctestrun [DUO_PY=/path/to/duo.py] \
#     scripts/capture-corpus-flow.sh <name> <bundle-id> '<screen>=<tap>;<tap>;…' …
# DUO_PY defaults to the bundled driver (driver/duo.py beside the skill's copy, third_party/duo-driver/duo.py from the
# repository's scripts/); `source .duo/env` sets all three. Without them, or with an ONLY that names something other
# than the seven poses, it exits 2 and touches nothing.
# A tap is an accessibility label or identifier (exact, else a case-insensitive substring of a label); "launch="
# is the launch screen with no taps. Other steps: type:<text>, try:<label> (only if present),
# springboard:<alert button> (only if an alert is up), cell:<n> (the n-th hittable cell from the top, 1-based, for
# lists whose rows are other people's content), wait:<seconds>. ONLY="book laptop" limits poses. WAIT (default 6) is
# the settle after launch, TAP_WAIT (default 2) after each tap; TAP_TIMEOUT (default 150) is how long the runner has to
# launch and reach a screen before it is skipped. APP_PATH=<.app> reinstalls the app before every screen,
# for apps that remember their onboarding (Signal). LAUNCH_ARGS="A B" passes launch arguments to the app (an app's own
# UI-test switches, user defaults): the runner splits the value at each space and nowhere else, so a quote or a
# backslash in it reaches the app as a character and no argument holds a space (-Key <false/>, never -Key '<false/>').
# Build the runner once: the skill's references/simulator.md, "Before the first capture" (the preflight prints the
# line), or, in the repository, Tap/README.md.
# Shots → foldsmith-evidence's raw/corpus/evidence/<name>/<screen>-<pose>-<panel>.png (from the skill's copy:
# .duo/captures/<name>/; OUT=<dir>
# puts them elsewhere); xcodebuild logs and the shut-phone snapshots → $XCODE_OUT (scratch). SNAPSHOT=1 also asks the
# runner, once the phone is in the pose and shot, for the app's accessibility tree: <screen>-<pose>.json next to the
# shot, for the detectors (swift run duo-detect <dir>). A screen's shots and snapshots in the poses asked for (those
# RESUME=1 does not keep) are removed first, so a pose this pass skips reads as not captured, not as an earlier pass's
# picture or tree. ON_SHOT='<command>' runs after each pose of each screen that has a shot, with three arguments, the
# screen, the pose and the shot's path (capture-app.sh uses it to keep .duo/migration.json current).
#
# Safe to stop, and it never fills the disk:
# - One capture at a time. It holds a lock while it runs, .duo/.capture.lock under the current folder (CAPTURE_LOCK
#   names another), holding its pid, start time and flow sha256; capture-app.sh takes the lock for its whole capture and
#   this script runs under it, adding a "flow pid" line of its own. Another capture refuses with exit 5 while any pid
#   there is a running capture; a lock whose captures are gone (dead pids, or pids that are no capture now) is
#   replaced. The Foldsmith pane takes no live frame while the lock is there.
# - On INT, TERM or HUP it releases the runner (TERM to xcodebuild when it does not let go within seconds, KILL after),
#   removes its lock, and prints a "stopped:" line naming the screen and pose it was on. So does any other early exit.
#   USR1 stands for INT (capture-app.sh sends it, since a background job ignores INT), so the line names the signal the
#   person sent. Run by capture-app.sh, it also stops this way when capture-app.sh is gone (killed outright, so no trap
#   of its ran): before each screen and pose and while it waits for the runner, it checks that capture-app.sh is
#   still its parent, and on its way out it removes the lock capture-app.sh left.
# - Before each screen, under 3 GB free on the disk of the home folder or of the shots, it prints a "stopped:" line with
#   the space and the largest ~/Library/Caches/duo-* folders, deletes nothing, and exits 4.
# - Each cell captured (its shot, and its snapshot with SNAPSHOT=1) is recorded in <out>/.captured as "<flow sha256>
#   <screen> <pose> <code>": the flow's sha256 (FLOW_SHA, which capture-app.sh sets, else that of these arguments) and
#   the app's code identity (CAPTURE_CODE, which capture-app.sh sets, else what progress.py codeid prints here, once,
#   after the lock, on a "code:" line first; none when progress.py is not beside this script). RESUME=1 keeps the cells
#   recorded there with the same sha256 and the same code whose files are still there and captures the rest, so a
#   capture stopped by a signal, a time limit or the disk carries on where it stopped, and one resumed after a commit or
#   an edit takes its cells again and says so once; a line with no code (written before 0.8.1) is never kept. Without
#   RESUME=1 the lines of the cells it captures are marked "retaking" first, so a later RESUME=1 never keeps a cell from
#   before this capture while progress.py still reads the code a shot not yet taken again came from. A cell's line
#   goes with its shot (before its screen), and its new line is added once the cell is captured.
set -euo pipefail

NAME="${1:?app name}"; BUNDLE="${2:?bundle id}"; shift 2
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
# The environment and the poses, checked before anything is touched (the same lines as in capture-app.sh).
POSE_NAMES="closed closed-sideways book laptop tent flat-sideways flat-upright"
ENV_HINT="source .duo/env first (the preflight writes it: bash <skill>/tools/preflight.sh <app folder>)"
if [ -z "${DUO_PY:-}" ]; then
  for d in "$HERE/driver/duo.py" "$HERE/../third_party/duo-driver/duo.py"; do [ -f "$d" ] && { DUO_PY="$d"; break; }; done
fi
[ -n "${DUO_UDID:-}" ] || { echo "DUO_UDID is not set: $ENV_HINT" >&2; exit 2; }
[ -f "${DUO_PY:-}" ] || { echo "DUO_PY (${DUO_PY:-not set}) is not a file: $ENV_HINT" >&2; exit 2; }
[ -f "${DUO_TAP_XCTESTRUN:-}" ] || { echo "DUO_TAP_XCTESTRUN (${DUO_TAP_XCTESTRUN:-not set}) is not a file: build the tap runner (the preflight prints the line), run the preflight again, then $ENV_HINT" >&2; exit 2; }
read -ra ONLY_WORDS <<< "${ONLY:-}"
for p in ${ONLY_WORDS[@]+"${ONLY_WORDS[@]}"}; do
  [[ " $POSE_NAMES " == *" $p "* ]] || { echo "ONLY=\"$ONLY\": $p is not a pose; the poses are $POSE_NAMES" >&2; exit 2; }
done
UDID="$DUO_UDID"
XCTESTRUN="$DUO_TAP_XCTESTRUN"
# Run from Foldsmith's scripts/, shots go to raw/corpus/evidence/<name>/ in the evidence repository (foldsmith-evidence
# beside this one, or at $FOLDSMITH_EVIDENCE); the skill's copy (skills/foldsmith-duo/tools) has no evidence repository
# and writes under the app being migrated instead.
EV="${FOLDSMITH_EVIDENCE:-$ROOT/../foldsmith-evidence}"
if [ "$(basename "$HERE")" = scripts ]; then
  [ -n "${OUT:-}" ] || [ -d "$EV/raw/corpus" ] || { echo "no foldsmith-evidence checkout at $EV (clone it beside this repository, set FOLDSMITH_EVIDENCE, or pass OUT)" >&2; exit 2; }
  OUT="${OUT:-$EV/raw/corpus/evidence/$NAME}"
else
  OUT="${OUT:-$PWD/.duo/captures/$NAME}"
fi
XOUT="${XCODE_OUT:-$(mktemp -d -t duo-tap)}"
mkdir -p "$OUT" "$XOUT"
WAIT="${WAIT:-6}"; TAP_WAIT="${TAP_WAIT:-2}"; TAP_TIMEOUT="${TAP_TIMEOUT:-150}"
bounded() { perl -e 'alarm shift; exec @ARGV' "$@"; }   # a hung app can hang simctl with it: give up after N seconds
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# --- one capture at a time, and never a full disk (the same four functions as in capture-app.sh)
lock_field() { sed -n "s/^$1 //p" "$2" 2>/dev/null | head -1; }
# Takes the lock file $1 for this capture (flow sha256 $2, into $3), or exits 5 while a running capture holds it.
take_lock() {
  local body pid fpid p
  body="$(printf 'pid %s\nstarted %s\nflow sha256 %s\nout %s' "$$" "$(now)" "$2" "$3")"
  mkdir -p "$(dirname "$1")"
  if ! ( set -o noclobber; printf '%s\n' "$body" > "$1" ) 2>/dev/null; then
    pid="$(lock_field pid "$1")"; fpid="$(lock_field 'flow pid' "$1")"
    for p in $pid $fpid; do   # capture-app.sh, and the flow script it runs (alive on its own if capture-app.sh was killed)
      case "$p" in *[!0-9]*) continue;; esac
      if ps -p "$p" -o command= 2>/dev/null | grep -Eq 'capture-(app|corpus-flow|corpus-app)\.sh'; then
        echo "another capture is running: pid $p since $(lock_field started "$1"), into $(lock_field out "$1") ($1). Wait for it to end; never start a second capture or a build beside one." >&2
        exit 5
      fi
    done
    echo "replacing a stale capture lock: $1 names pid ${pid:-?}${fpid:+ (and flow pid $fpid)}, which is no running capture" >&2
    rm -f "$1"
    ( set -o noclobber; printf '%s\n' "$body" > "$1" ) 2>/dev/null || { echo "another capture took $1 just now" >&2; exit 5; }
  fi
  LOCK_HELD="$1"
}
drop_lock() {
  if [ -n "${LOCK_HELD:-}" ] && [ "$(lock_field pid "$LOCK_HELD")" = "$$" ]; then rm -f "$LOCK_HELD"; fi
  LOCK_HELD=
}
# Prints why the capture stops before $1 when the disk of the home folder or of the shots has under 3 GB free; else
# fails. Names the largest ~/Library/Caches/duo-* folders for the person to judge; deletes nothing.
low_disk() {
  local kb big
  kb="$(df -Pk "${HOME:-$OUT}" "$OUT" 2>/dev/null | awk 'NR > 1 { for (i = 2; i <= NF; i++) if ($i ~ /%$/) { print $(i - 1); break } }' | sort -n | head -1)"
  case "$kb" in ''|*[!0-9]*) return 1;; esac
  [ "$kb" -lt 3145728 ] || return 1
  big="$(du -sk "${HOME:-}"/Library/Caches/duo-* 2>/dev/null | sort -rn | head -3 | awk -v home="${HOME:-}" '
    { kb = $1; sub(/^[0-9]+[ \t]+/, ""); if (index($0, home "/") == 1) $0 = "~" substr($0, length(home) + 1)
      printf "%s%s %s", (NR > 1 ? ", " : ""), (kb >= 1048576 ? sprintf("%.1f GB", kb / 1048576) : sprintf("%d MB", kb / 1024)), $0 }')"
  printf 'stopped: only %s free on the disk (a capture needs 3 GB), before %s, %s. The largest ~/Library/Caches/duo-* folders: %s. Nothing was deleted: free some space, then run the same command with RESUME=1 to carry on.\n' \
    "$(awk -v kb="$kb" 'BEGIN { printf "%.1f GB", kb / 1048576 }')" "$1" "$(now)" "${big:-none}"
}

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

# The cells captured, for RESUME=1 and progress.py check: "<flow sha256> <screen> <pose> <code>" per line.
SHA="${FLOW_SHA:-$(printf '%s\n' "$NAME" "$BUNDLE" "${LAUNCH_ARGS:-}" "${SCREENS[@]}" | shasum -a 256 | cut -d' ' -f1)}"
RECORD="$OUT/.captured"
captured() { # whether RESUME=1 keeps the cell of screen $1 in pose $2: a line with this flow and this code, its files
  [ "${RESUME:-0}" = 1 ] && [ -f "$RECORD" ] && grep -qxF "$SHA $1 $2 $CODE" "$RECORD" \
    && [ -e "$OUT/$1-$2-$(expected_panel "$2").png" ] && { [ "${SNAPSHOT:-0}" != 1 ] || [ -e "$OUT/$1-$2.json" ]; }
}
# How the record has the cell $1 ("<screen> <pose>") from this flow: same (this code), other (other code), none (a line
# with no code, written before 0.8.1), or nothing.
earlier() {
  local line rest how=
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      "$SHA $1 $CODE") how=same;;
      "$SHA $1") [ -n "$how" ] || how=none;;
      "$SHA $1 "*) rest="${line#"$SHA $1 "}"; case "$rest" in *" "*) ;; *) [ "$how" = same ] || how=other;; esac;;
    esac
  done < "$RECORD"
  echo "$how"
}
# Rewrites the record for the cells in $2 ("<screen> <pose>" per line, whatever their flow or code): with $1 = drop
# their lines go; with $1 = retake their flow sha256 becomes "retaking", so RESUME=1 keeps none of them while
# progress.py still reads the code each shot came from.
edit_record() {
  [ -f "$RECORD" ] || return 0
  CELLS="$2" awk -v how="$1" -v poses=" $POSE_NAMES " '
    BEGIN { n = split(ENVIRON["CELLS"], c, "\n"); for (i = 1; i <= n; i++) if (c[i] != "") cell[c[i]] = 1 }
    NF < 3 { print; next }
    { at = index(poses, " " $NF " ") ? NF : NF - 1; name = $2; for (i = 3; i < at; i++) name = name " " $i }
    !((name " " $at) in cell) { print; next }
    how == "retake" { $1 = "retaking"; print }' "$RECORD" > "$RECORD.new"
  mv "$RECORD.new" "$RECORD"
}

# The lock: capture-app.sh's when it runs this script (it names itself in the lock and in CAPTURE_LOCK_PID), with a
# "flow pid" line of ours added, so the lock stays live while this runs even if capture-app.sh is killed; else ours.
LOCK="${CAPTURE_LOCK:-$PWD/.duo/.capture.lock}"; LOCK_HELD=; PARENT=
if [ "${CAPTURE_LOCK_PID:-}" = "$PPID" ] && [ "$(lock_field pid "$LOCK")" = "$PPID" ]; then
  PARENT=$PPID
  printf 'flow pid %s\n' "$$" >> "$LOCK"
else
  take_lock "$LOCK" "$SHA" "$OUT"
fi
# Whether capture-app.sh, whose capture this is, is gone (killed outright, so no trap of its ran): this script is no
# longer its child. Then it stops as on a signal, and nothing drives the simulator beside the next capture.
ORPHANED=
orphaned() { [ -n "$PARENT" ] && [ "$(ps -o ppid= -p $$ 2>/dev/null | tr -d ' ')" != "$PARENT" ]; }
stop_if_orphaned() { if orphaned; then ORPHANED=1; exit 1; fi; }

# Whatever ends the capture early, the runner lets go of the app, the lock goes, and the output says where it stopped.
XB=; FLAGS=; AWAITED=; SIGNAL=; STOP_NOTE=; AT="the first screen"
# Lets the runner go: the release flag, then TERM to xcodebuild after $1 seconds and KILL ten seconds after that.
release() {
  if [ -n "$XB" ]; then
    [ -z "$FLAGS" ] || touch "$FLAGS/release" 2>/dev/null || true
    local t=0
    while kill -0 "$XB" 2>/dev/null && [ "$t" -lt "$(( $1 * 2 ))" ]; do sleep 0.5; t=$((t+1)); done
    if kill -0 "$XB" 2>/dev/null; then
      kill -TERM "$XB" 2>/dev/null || true; t=0
      while kill -0 "$XB" 2>/dev/null && [ "$t" -lt 20 ]; do sleep 0.5; t=$((t+1)); done
      kill -KILL "$XB" 2>/dev/null || true
    fi
    wait "$XB" 2>/dev/null || true
  fi
  XB=; [ -z "$FLAGS" ] || rm -rf "$FLAGS"; FLAGS=
}
on_exit() {
  local rc=$?
  trap '' INT TERM HUP PIPE
  set +e
  release 10
  drop_lock
  # capture-app.sh killed outright left its lock: it names that dead pid and ours, so it goes with us.
  if [ -n "$ORPHANED" ] && [ "$(lock_field pid "$LOCK")" = "$PARENT" ]; then rm -f "$LOCK"; fi
  if [ "$rc" -ne 0 ] && [ -z "$STOP_NOTE" ]; then
    local why="exit $rc"; [ -z "$SIGNAL" ] || why="interrupted (SIG$SIGNAL)"
    [ -z "$ORPHANED" ] || why="capture-app.sh (pid $PARENT) was killed without stopping the capture"
    echo "stopped: $why at $AT, $(now). The cells captured before it are kept: the same command with RESUME=1 carries on from there."
  fi
  exit "$rc"
}
trap 'SIGNAL=INT; exit 130' INT USR1
trap 'SIGNAL=TERM; exit 143' TERM
trap 'SIGNAL=HUP; exit 129' HUP
trap on_exit EXIT

# The code this capture is of, on each line it adds to the record: capture-app.sh's (CAPTURE_CODE), else what
# progress.py codeid prints (HEAD, then + and a hash when anything outside .duo/ is uncommitted; none outside git).
CODE_RE='^[0-9a-f]{40}(\+[0-9a-f]{16})?$'
if [ -n "${CAPTURE_CODE:-}" ]; then
  CODE="$CAPTURE_CODE"; [[ "$CODE" =~ $CODE_RE ]] || CODE=none
else
  CODE=none
  [ ! -f "$HERE/progress.py" ] || CODE="$(python3 "$HERE/progress.py" codeid 2>/dev/null)" || CODE=none
  [[ "$CODE" =~ $CODE_RE ]] || CODE=none
  echo "code: $CODE"
fi

# A capture that does not resume marks the cells it is about to take, so a later RESUME=1 keeps only its own. One that
# resumes says once when cells of this flow were captured from other code: it takes those again.
if [ "${RESUME:-0}" != 1 ]; then
  cells=
  for s in "${SCREENS[@]}"; do for entry in "${SELECTED[@]}"; do cells+="${s%%=*} ${entry%%|*}"$'\n'; done; done
  edit_record retake "$cells"
elif [ -f "$RECORD" ]; then
  kept=0; other=0; bare=0
  for s in "${SCREENS[@]}"; do
    for entry in "${SELECTED[@]}"; do
      if captured "${s%%=*}" "${entry%%|*}"; then kept=$((kept+1)); continue; fi
      case "$(earlier "${s%%=*} ${entry%%|*}")" in other) other=$((other+1));; none) bare=$((bare+1));; esac
    done
  done
  if [ $((other + bare)) -gt 0 ]; then
    why="code changed since the earlier capture"
    [ "$other" -gt 0 ] || why="the earlier capture recorded no code (it was taken before 0.8.1)"
    if [ "$kept" -eq 0 ]; then echo "$why: taking every cell again"
    else echo "$why, for $((other + bare)) cells: taking those again ($kept kept)"; fi
  fi
fi

# Fold and turn the phone, skipping what is already so; a fold always posts the orientation after it.
FOLD_NOW=; ORIENT_NOW=
pose_to() {
  if [ "$1" != "$FOLD_NOW" ]; then python3 "$DUO_PY" fold "$1" >/dev/null; sleep 2; FOLD_NOW=$1; ORIENT_NOW=; fi
  if [ "$2" != "$ORIENT_NOW" ]; then python3 "$DUO_PY" orient "$2" >/dev/null; sleep 3; ORIENT_NOW=$2; fi
}
# Waits for the runner to write $1 (or failed, or to exit), at most $2 seconds; AWAITED says what happened. It waits in
# this shell, not in a $(…) subshell, so a signal stops the capture at once rather than when the wait ends.
await() {
  local waited=0
  AWAITED=timeout
  while [ "$waited" -lt "$(( $2 * 2 ))" ]; do
    if [ -e "$FLAGS/$1" ]; then AWAITED=$1; return 0; fi
    if [ -e "$FLAGS/failed" ]; then AWAITED=failed; return 0; fi
    if ! kill -0 "$XB" 2>/dev/null; then AWAITED=exited; return 0; fi
    stop_if_orphaned
    sleep 0.5; waited=$((waited+1))
  done
}
# The app's accessibility tree as the runner sees it now, copied to $1.
snapshot_to() {
  rm -f "$FLAGS/snapped" "$FLAGS/snapshot.json"; touch "$FLAGS/posed"
  await snapped 60
  [ "$AWAITED" = snapped ] && [ -s "$FLAGS/snapshot.json" ] && cp "$FLAGS/snapshot.json" "$1"
}
# The runner relaunches the app and taps through the flow again.
retap() {
  rm -f "$FLAGS/tapped" "$FLAGS/failed"; touch "$FLAGS/again"
  await tapped "$TAP_TIMEOUT"
  [ "$AWAITED" = tapped ]
}
# Whether a snapshot's window is taller than wide (the cover upright).
tall() { python3 -c 'import json, sys; w, h = json.load(open(sys.argv[1]))["window"]; sys.exit(0 if h > w else 1)' "$1"; }
# The app's state in a snapshot taken while it was not in front (crashed or quit), else nothing.
not_in_front() { python3 -c 'import json, sys; print(json.load(open(sys.argv[1])).get("appState") or "")' "$1" 2>/dev/null || true; }

for s in "${SCREENS[@]}"; do
  screen="${s%%=*}"; taps="${s#*=}"
  AT="$screen, before its first pose"
  if [ "${RESUME:-0}" = 1 ]; then
    left=0
    for entry in "${SELECTED[@]}"; do captured "$screen" "${entry%%|*}" || left=$((left+1)); done
    if [ "$left" -eq 0 ]; then echo "== $screen"; echo "  every pose asked for was captured before (RESUME=1)"; continue; fi
  fi
  stop_if_orphaned
  if note="$(low_disk "$screen")"; then echo "$note"; STOP_NOTE=1; exit 4; fi
  echo "== $screen"
  # An earlier pass's shot, snapshot and line in the record of a cell this pass takes go first: a pose this pass misses
  # is missing.
  cells=
  for entry in "${SELECTED[@]}"; do
    label="${entry%%|*}"
    captured "$screen" "$label" && continue
    rm -f "${OUT:?}/$screen-$label-cover.png" "${OUT:?}/$screen-$label-inner.png"
    [ "${SNAPSHOT:-0}" != 1 ] || rm -f "${OUT:?}/$screen-$label.json"
    cells+="$screen $label"$'\n'
  done
  edit_record drop "$cells"
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
  AT="$screen, on its way in (launch and taps)"
  await tapped "$TAP_TIMEOUT"; state=$AWAITED
  cp "$FLAGS/hierarchy.txt" "$XOUT/$screen.hierarchy.txt" 2>/dev/null || true
  cp "$FLAGS/hierarchy-after.txt" "$XOUT/$screen.hierarchy-after.txt" 2>/dev/null || true
  if [ "$state" != tapped ]; then
    case "$state" in
      failed) echo "  $screen: skipped in every pose: $(cat "$FLAGS/failed")";;
      exited) echo "  $screen: skipped in every pose: test runner exited early (see $XOUT/$screen.log)";;
      *) echo "  $screen: skipped in every pose: no tap within ${TAP_TIMEOUT}s";;
    esac
    cp "$FLAGS/screen.png" "$XOUT/$screen.screen.png" 2>/dev/null || true
    release 120; continue
  fi
  # The screen as the shut phone shows it after the taps: what the shut phone must show again before each inner pose.
  ref="$XOUT/$screen.shut.json"; rm -f "$ref"; snapshot_to "$ref" || true
  # 3. every pose in turn while the runner holds the app
  prev=
  for entry in "${SELECTED[@]}"; do
    IFS='|' read -r label fold orient <<<"$entry"
    if captured "$screen" "$label"; then echo "  $label: kept from the earlier capture (RESUME=1)"; continue; fi
    stop_if_orphaned
    AT="$screen in $label"
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
    shot_ok=0; snap_ok=0
    python3 "$DUO_PY" shot --out "$OUT" --name "$screen-$label" >/dev/null && shot_ok=1 || true
    if [ "$(shot_shape "$screen" "$label")" != "$(expected_shape "$label")" ]; then
      # a repeat of the same orientation can be a no-op for the app: post the other one first, then this one (and a
      # shot that failed gets this second try too)
      other=$([ "$orient" = sideways ] && echo upright || echo sideways)
      python3 "$DUO_PY" orient "$other" >/dev/null; sleep 3
      python3 "$DUO_PY" orient "$orient" >/dev/null; sleep "$WAIT"
      python3 "$DUO_PY" shot --out "$OUT" --name "$screen-$label" >/dev/null && shot_ok=1 || true
      shape="$(shot_shape "$screen" "$label")"
      if [ "$shape" = none ]; then
        shot_ok=0
        echo "  $screen: skipped in $label: no shot (duo.py shot failed, or saved no $(expected_panel "$label") panel, twice)"
      elif [ "$shape" != "$(expected_shape "$label")" ]; then
        echo "  $screen: still $shape in $label (expected $(expected_shape "$label")): app did not rotate"
      fi
    fi
    if [ "${SNAPSHOT:-0}" = 1 ]; then   # the tree as XCTest sees it in this pose, same moment as the shot
      if snapshot_to "$OUT/$screen-$label.json"; then
        snap_ok=1
        gone="$(not_in_front "$OUT/$screen-$label.json")"
        [ -z "$gone" ] || echo "  $screen: the app was not in front in $label ($gone): it crashed or quit on the way there, T7 in that cell"
      else
        case "$AWAITED" in
          snapped) why="the runner wrote an empty one";; exited) why="the runner exited (see $XOUT/$screen.log)";;
          failed) why="the runner failed: $(cat "$FLAGS/failed" 2>/dev/null)";; *) why="no answer from the runner in 60 s";;
        esac
        echo "  $screen: skipped in $label: no snapshot ($why)"
      fi
    fi
    shot="$OUT/$screen-$label-$(expected_panel "$label").png"
    [ -z "${ON_SHOT:-}" ] || [ ! -e "$shot" ] || bash -c "$ON_SHOT"' "$@"' _ "$screen" "$label" "$shot" || true
    if [ "$shot_ok" = 1 ] && [ -e "$shot" ] && { [ "${SNAPSHOT:-0}" != 1 ] || [ "$snap_ok" = 1 ]; }; then
      echo "$SHA $screen $label $CODE" >> "$RECORD"
    fi
    echo "  $label"
    prev=$label
  done
  AT="$screen, letting the runner go"
  release 120
done
AT="the end"
echo "done → $OUT"
