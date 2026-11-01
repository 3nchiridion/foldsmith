#!/usr/bin/env bash
# The skill's capture in one command: every screen of a flow file in every pose, each with its accessibility snapshot,
# then the detectors over all of it.
#
# Usage:
#   source .duo/env && capture-app.sh <flow-file> <out-dir>
# .duo/env (the preflight writes it) sets DUO_UDID, DUO_TAP_XCTESTRUN and DUO_PY; DUO_PY defaults to the bundled
# driver beside this script (driver/duo.py; third_party/duo-driver/duo.py from the repository's scripts/). Without
# them, or with an ONLY or SCREEN that names nothing of the flow's, it exits 2 before it touches anything.
# The flow file is shell: BUNDLE=<bundle id>, optional LAUNCH_ARGS="…" and APP_PATH=<.app>, and
# SCREENS=( "<screen>=<tap>;<tap>" … ) with the taps capture-corpus-flow.sh takes (its header has the syntax).
# The app must already be built and installed on the simulator (xcrun simctl install), or APP_PATH set to its .app,
# which uninstalls it and installs it afresh before every screen (its data and any login go with it). Shots,
# <screen>-<pose>.json snapshots and capture.txt go to <out-dir>;
# the detectors write <out-dir>/detectors.md and their summary line to <out-dir>/findings.txt. ONLY="book laptop"
# limits poses, as for capture-corpus-flow.sh, and SCREEN="settings status" limits screens, by their names in the flow:
# together they probe one screen behind taps in the poses a change touches (into a scratch <out-dir>, so no cell
# changes). TAP_TIMEOUT (default 150 s) is how long a screen's taps may take before it is skipped. When <out-dir> is a
# `before` or `after` folder and the progress file exists (PROGRESS, default .duo/migration.json), each shot's path is
# written to its cell as it lands, so the Foldsmith pane shows the capture as it goes.
# Exit 0 when every screen was captured in every pose asked for; 3 when any cell was not (the lines are repeated at the
# end and in findings.txt), so a missing screen is never read as a clean one. What decides is the record of the cells
# captured, <out-dir>/.captured (a shot and a snapshot both landed): each of this run's screens in each pose asked for
# with no line there is missing, whatever its line said (taps that reach nothing, no shot, no snapshot). A SCREEN=
# recapture into a folder that has a capture adds to its capture.txt under a "recaptured" line instead of replacing it,
# so the first pass's lines (a lost screen, a skip) stay on record; for the flow's other screens each one's latest
# capture in the file decides, so a screen skipped in an earlier pass and not captured since still counts as missing,
# whichever screens this run took. A snapshot taken while the app was not in front (it crashed or quit on the way to a
# pose) is repeated at the end and in findings.txt too: T7 in that cell, never a clean one.
#
# A full capture outlasts a foreground shell call: run it in the background and read the exit code. It is safe to stop
# and never fills the disk (capture-corpus-flow.sh's header has the details):
# - One capture at a time: from before it writes capture.txt until it ends it holds .duo/.capture.lock (beside the
#   progress file; CAPTURE_LOCK names another), with its pid, start time, flow sha256 and <out-dir>, and the pid of
#   the capture-corpus-flow.sh it runs. While a pid there is a running capture, another capture exits 5 and touches
#   nothing; a lock whose capture is gone is replaced. Killed outright (SIGKILL: no trap runs), it leaves the flow
#   script to stop on its own: that one notices, lets the runner go and removes the lock. The Foldsmith pane takes no
#   live frame while the lock is there.
# - Under 3 GB free on the disk of the home folder or of <out-dir>, before the capture, each screen and the detectors'
#   build, it stops with exit 4, naming the space and the largest ~/Library/Caches/duo-* folders. It deletes nothing.
# - INT, TERM or HUP: the runner lets go of the app (xcodebuild is killed if it holds on), the lock goes, capture.txt
#   ends with a "stopped:" line naming the signal, the screen and the pose, and the exit code is 128 + the signal's
#   number.
# - RESUME=1, with the same flow file (same sha256) into the same <out-dir>: the cells already captured there are kept
#   and the rest captured, capture.txt gets a "resumed" line, then the detectors run over the whole folder. A changed
#   flow captures every cell again.
# Exit codes: 0 every cell asked for captured; 2 a wrong call; 3 cells not captured; 4 under 3 GB free; 5 another
# capture running; 128 + n stopped by signal n; anything else, the "stopped:" line says where.
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
# The environment and the poses, checked before anything is touched (the same lines as in capture-corpus-flow.sh).
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
export DUO_PY
ASKED=()   # the poses this run takes, in capture order
for p in $POSE_NAMES; do
  if [ ${#ONLY_WORDS[@]} -eq 0 ] || [[ " ${ONLY_WORDS[*]} " == *" $p "* ]]; then ASKED+=("$p"); fi
done
SHA="$(shasum -a 256 "$FLOW" | cut -d' ' -f1)"
PROGRESS="${PROGRESS:-.duo/migration.json}"
LOCK="${CAPTURE_LOCK:-$(dirname "$PROGRESS")/.capture.lock}"
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# --- one capture at a time, and never a full disk (the same four functions as in capture-corpus-flow.sh)
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

mkdir -p "$OUT"
LOCK_HELD=
take_lock "$LOCK" "$SHA" "$OUT"
# Whatever ends it early: the capture and the detectors are stopped (the capture lets its runner go), the lock goes,
# and capture.txt ends saying where it stopped.
STAGE="the capture"; WROTE=; SIGNAL=
on_exit() {
  local rc=$?
  trap '' INT TERM HUP PIPE
  set +e
  if [ "$rc" -ne 0 ] && [ "$rc" -ne 3 ]; then
    # The signal passed on, so the capture's "stopped:" line names the one the person sent. A background job ignores
    # INT, so USR1 stands for it (capture-corpus-flow.sh traps it as INT; the copy into capture.txt ignores it).
    local sig=TERM; case "$SIGNAL" in INT) sig=USR1;; HUP) sig=HUP;; esac
    pkill -"$sig" -P $$ 2>/dev/null; wait 2>/dev/null
    if [ -n "$WROTE" ] && ! tail -n 1 "$OUT/capture.txt" 2>/dev/null | grep -q '^stopped:'; then
      local why="exit $rc"; [ -z "$SIGNAL" ] || why="interrupted (SIG$SIGNAL)"
      echo "stopped: $why during $STAGE, $(now). The cells captured are kept: the same command with RESUME=1 carries on from there." \
        >> "$OUT/capture.txt"
    fi
  fi
  drop_lock
  exit "$rc"
}
trap 'SIGNAL=INT; exit 130' INT
trap 'SIGNAL=TERM; exit 143' TERM
trap 'SIGNAL=HUP; exit 129' HUP
trap on_exit EXIT

if note="$(low_disk "the capture")"; then echo "$note" >&2; exit 4; fi

RESUMING=0
if [ "${RESUME:-0}" = 1 ]; then
  if [ -f "$OUT/capture.txt" ] && grep -q "sha256 $SHA" "$OUT/capture.txt"; then RESUMING=1
  else echo "RESUME=1: $OUT holds no capture of this flow (sha256 $SHA), so every cell is captured" >&2; fi
fi
if [ "$RESUMING" = 1 ]; then
  echo "resumed: ${SCREEN:-every screen}, $(now), flow sha256 $SHA" >> "$OUT/capture.txt"
elif [ -n "${SCREEN:-}" ] && [ -f "$OUT/capture.txt" ]; then
  echo "recaptured: $SCREEN, $(now), flow sha256 $SHA" >> "$OUT/capture.txt"
else
  {
    echo "app: $NAME ($BUNDLE)"
    echo "flow: $FLOW sha256 $SHA"
    echo "captured: $(now) on $(xcrun simctl list devices | grep -F "$DUO_UDID" | sed 's/^ *//')"
  } > "$OUT/capture.txt"
fi
WROTE=1

ON_SHOT=
KIND="$(basename "$OUT")"
if [ -f "$PROGRESS" ] && { [ "$KIND" = before ] || [ "$KIND" = after ]; }; then
  ON_SHOT="python3 '$HERE/progress.py' --file '$PROGRESS' shot $KIND"
fi

# Long steps run in the background and are waited for, so a signal is handled at once, not when they end. The copy
# into capture.txt ignores the signals and ends with the capture, so the capture's last line ("stopped: …") lands, even
# when this script was killed and its own output is gone (PIPE ignored: tee goes on writing the file).
keep_writing() { trap '' INT TERM HUP USR1 PIPE; exec tee -a "$1"; }
CAPTURE_LOCK="$LOCK" CAPTURE_LOCK_PID=$$ FLOW_SHA="$SHA" RESUME="$RESUMING" \
OUT="$OUT" SNAPSHOT=1 WAIT="${WAIT:-6}" TAP_WAIT="${TAP_WAIT:-2}" LAUNCH_ARGS="$LAUNCH_ARGS" APP_PATH="$APP_PATH" \
  ONLY="${ONLY:-}" ON_SHOT="$ON_SHOT" bash "$HERE/capture-corpus-flow.sh" "$NAME" "$BUNDLE" "${SCREENS[@]}" \
  | keep_writing "$OUT/capture.txt" &
rc=0; wait $! || rc=$?
[ "$rc" -eq 0 ] || exit "$rc"

# The detectors: the skill's own package (tools/detect), built outside the skill's folder, or this repository's.
STAGE="the detectors"
if note="$(low_disk "the detectors' build")"; then echo "$note" | tee -a "$OUT/capture.txt" >&2; exit 4; fi
PKG="$HERE/detect"; BUILD=(--scratch-path "$HOME/Library/Caches/duo-detect")
[ -f "$PKG/Package.swift" ] || { PKG="$HERE/.."; BUILD=(); }
swift run -c release --package-path "$PKG" ${BUILD[@]+"${BUILD[@]}"} duo-detect "$OUT" --markdown "$OUT/detectors.md" \
  | grep -v '^\[' > "$OUT/findings.txt" &
rc=0; wait $! || rc=$?
[ "$rc" -eq 0 ] || exit "$rc"
STAGE="the end"
tail -1 "$OUT/findings.txt"
# Snapshots taken while the app was not in front: a crash or a quit on the way to the pose, T7 in that cell.
GONE="$(python3 -c '
import json, pathlib, sys
POSES = ("closed", "closed-sideways", "book", "laptop", "tent", "flat-sideways", "flat-upright")
for f in sorted(pathlib.Path(sys.argv[1]).glob("*.json")):
    try:
        state = json.loads(f.read_text()).get("appState")
    except (OSError, ValueError, AttributeError):
        continue
    pose = next((p for p in POSES if f.stem.endswith("-" + p)), None)
    if state and pose:
        print(f"{f.stem[:-len(pose) - 1]} {pose}: the app was not in front ({state}): it crashed or quit on the way, T7 in that cell, not a clean one")
' "$OUT")"
[ -z "$GONE" ] || echo "$GONE" | tee -a "$OUT/findings.txt" >&2
# What is missing. The record decides for this run's cells: each of its screens in each pose asked for with no
# "<sha256> <screen> <pose>" line in <out>/.captured (a skip, a failed shot or snapshot, whatever its line said). For the
# flow's other screens, the skip lines of each one's latest capture in capture.txt ("== <screen>" starts one) stay.
MISSING=()
for s in "${SCREENS[@]}"; do
  for p in "${ASKED[@]}"; do
    grep -qxF "$SHA ${s%%=*} $p" "$OUT/.captured" 2>/dev/null || MISSING+=("${s%%=*} $p")
  done
done
SKIPPED="$(awk '/^== / { cur = substr($0, 4); lines[cur] = ""; next }
                /skipped/ && cur != "" { lines[cur] = lines[cur] $0 "\n" }
                END { for (s in lines) printf "%s", lines[s] }' "$OUT/capture.txt")"
if [ ${#MISSING[@]} -gt 0 ] || [ -n "$SKIPPED" ]; then
  {
    [ -z "$SKIPPED" ] || printf '%s\n' "$SKIPPED"
    if [ ${#MISSING[@]} -gt 0 ]; then
      printf 'not captured in this run (no line in %s): ' "$OUT/.captured"
      printf '%s\n' "${MISSING[@]}" | paste -sd, - | sed 's/,/, /g'
    fi
  } | tee -a "$OUT/findings.txt" >&2
  echo "those cells are not clean, they are missing: capture them again (SCREEN=<screen> ONLY=<poses>) before reading the table" >&2
  exit 3
fi
