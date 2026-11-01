#!/usr/bin/env bash
# Mac phase step 4: screenshot one corpus app in every pose → foldsmith-evidence's
# raw/corpus/evidence/<name>/<screen>-<pose>-<panel>.png
#
# Usage:
#   DUO_UDID=<udid> [DUO_PY=/path/to/duo.py] scripts/capture-corpus-app.sh <name> <bundle-id> [<screen>=<url> ...]
# DUO_PY defaults to the bundled driver (driver/duo.py beside the skill's copy, third_party/duo-driver/duo.py from the
# repository's scripts/); `source .duo/env` sets both.
# Without screens it captures the launch screen as "launch". Each <screen>=<url> is opened with `simctl openurl`
# after launch; a screen whose URL fails is noted and skipped. A custom URL scheme raises an "Open in <app>?" system
# alert that nothing headless can answer on the open phone, so prefer launch screens and universal links.
# Each shot is checked against the pose's shape (tall or wide); on a mismatch the orientation is posted again and
# the shot retaken once. A mismatch that remains is printed: the app did not rotate (a finding, not a capture error).
# The app must already be built and installed on the simulator. Same pose set and duo.py terms as run-probe.sh.
# Like capture-corpus-flow.sh, it holds .duo/.capture.lock under the current folder while it runs (CAPTURE_LOCK names
# another; exit 5 while another capture holds it), stops with exit 4 under 3 GB free before each pose, and on INT, TERM
# or HUP removes the lock and prints a "stopped:" line naming the pose.
set -euo pipefail

NAME="${1:?app name}"; BUNDLE="${2:?bundle id}"; shift 2
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
ENV_HINT="source .duo/env first (the preflight writes it: bash <skill>/tools/preflight.sh <app folder>)"
if [ -z "${DUO_PY:-}" ]; then
  for d in "$HERE/driver/duo.py" "$HERE/../third_party/duo-driver/duo.py"; do [ -f "$d" ] && { DUO_PY="$d"; break; }; done
fi
[ -n "${DUO_UDID:-}" ] || { echo "DUO_UDID is not set: $ENV_HINT" >&2; exit 2; }
[ -f "${DUO_PY:-}" ] || { echo "DUO_PY (${DUO_PY:-not set}) is not a file: $ENV_HINT" >&2; exit 2; }
UDID="$DUO_UDID"
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
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

SCREENS=("launch=")
for s in "$@"; do SCREENS+=("$s"); done

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

LOCK="${CAPTURE_LOCK:-$PWD/.duo/.capture.lock}"; LOCK_HELD=
take_lock "$LOCK" "$(printf '%s\n' "$NAME" "$BUNDLE" "${SCREENS[@]}" | shasum -a 256 | cut -d' ' -f1)" "$OUT"
SIGNAL=; STOP_NOTE=; AT="the first pose"
on_exit() {
  local rc=$?
  trap '' INT TERM HUP PIPE
  set +e
  drop_lock
  if [ "$rc" -ne 0 ] && [ -z "$STOP_NOTE" ]; then
    local why="exit $rc"; [ -z "$SIGNAL" ] || why="interrupted (SIG$SIGNAL)"
    echo "stopped: $why at $AT, $(now)."
  fi
  exit "$rc"
}
trap 'SIGNAL=INT; exit 130' INT USR1
trap 'SIGNAL=TERM; exit 143' TERM
trap 'SIGNAL=HUP; exit 129' HUP
trap on_exit EXIT

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
  AT="$label"
  if note="$(low_disk "$label")"; then echo "$note"; STOP_NOTE=1; exit 4; fi
  echo "== pose $label"
  python3 "$DUO_PY" fold "$fold" >/dev/null
  sleep 2   # an orientation posted while the hinge still moves can be dropped
  python3 "$DUO_PY" orient "$orient" >/dev/null
  sleep 3
  for s in "${SCREENS[@]}"; do
    screen="${s%%=*}"; url="${s#*=}"
    AT="$screen in $label"
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
AT="the end"
echo "done → $OUT"
