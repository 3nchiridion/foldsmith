#!/usr/bin/env bash
# Preflight: what a Foldsmith run needs on this Mac, checked before anything changes. Read-only, except that when
# nothing blocks it writes <app folder>/.duo/env and adds everything in the app's .duo/ to the repository's
# .git/info/exclude (`/<app>/.duo/*`; an old `.duo/env` line stays): the run never commits .duo/, so its commits carry
# only app code and the branch can become a pull request.
#
# Usage:
#   bash preflight.sh <app folder>
# One line per check: `ok`, `warn` (does not block), `note`, or `missing` (blocks); each line that is not ok is followed
# by the exact fix. Nothing here installs, creates, renames or boots anything: a fix is for the person to run.
#   Xcode 27.1 selected (`xcodebuild -version`). When another Xcode is selected (older or newer) and an Xcode 27.1 is
#     in /Applications, .duo/env exports DEVELOPER_DIR for it (xcrun, xcodebuild and swift follow it), so nothing
#     needs sudo. An Xcode whose licence is not accepted gets that fix (`sudo xcodebuild -license accept`).
#   The iOS 27.1 simulator runtime (`xcrun simctl list`).
#   A simulator on that runtime whose name contains "Duo", and whether it is booted. duo.py drives only simulators whose
#     name contains "duo" (any case). None: the `xcrun simctl create` line to run. An iPhone Duo renamed without "Duo":
#     the `xcrun simctl rename` line.
#   python3.
#   rg (ripgrep), which the static scans and routes.sh read code with. In Claude Code `rg` is a shell function, not a
#     program on PATH, so a script cannot call it; where no rg is installed, routes.sh runs Claude Code itself as rg
#     ($CLAUDE_CODE_EXECPATH, as that function does).
#   Free space on the home volume: at least 5 GB; under 10 GB warns.
#   The app folder is a git repository with nothing uncommitted outside .duo/ (the run commits on a branch). The fix
#     it prints leaves .duo/ alone (an audit's progress file and captures are uncommitted): `-- ':/' ':(exclude).duo'`,
#     or no pathspec where the project's own rules ignore the .duo folder itself (git refuses the exclusion there). On
#     duo-migration, the changes are the run's own unfinished change: the fix says so.
#   Files under .duo/ that git already tracks (an earlier run committed them): a warning naming them, with the fix
#     (git rm -r --cached .duo, then a commit); it does not block.
#   A remote-tracking */duo-migration with no local duo-migration: a note that the run makes its own branch with
#     `git switch -c duo-migration --no-track`, so it never tracks another run's.
#   The CI's Xcode: one note with what `sdkguard.py --ci-only` (beside this script) finds in the repository's CI files
#     and what it means for the run, or "no CI Xcode found in the repository".
#   Claude Code 2.1.308 or later, which the plugin's pane needs: this session's ($CLAUDE_CODE_EXECPATH), else `claude`
#     on PATH. Neither is a note: the skill also runs in other agents.
# When nothing blocks it writes <app folder>/.duo/env, shell exports to source before each tool (`source .duo/env`), and
# prints one line per value:
#   DUO_UDID            the Duo simulator: a DUO_UDID you set when it names one of them, else the progress file's
#                       simulator (.duo/migration.json), else the one .duo/env named, else the booted one when exactly
#                       one is, else the first
#   DUO_PY              the bundled driver, <this folder>/driver/duo.py in the skill's tools/ (the repository's
#                       third_party/duo-driver/duo.py from scripts/); a DUO_PY you set wins
#   DUO_TAP_XCTESTRUN   the tap runner, once built into DUO_TAP_BUILD (default ~/Library/Caches/duo-tap/build; a
#                       DUO_TAP_XCTESTRUN you set wins); until then a note gives the build command
#   DEVELOPER_DIR       when the Xcode 27.1 found is not the selected one, or one you set picked it
#   FOLDSMITH_ENV       the path of the file itself
#   FOLDSMITH_ENV_SET   the values above as it set them, NAME=value per line, so a preflight run after
#                       `source .duo/env` knows them for its own
# Paths in it point into the installed skill, which moves when it is updated: run this at every start and resume, in a
# shell that has not sourced .duo/env. A value inherited from .duo/env all the same (equal to what the sourced file set,
# FOLDSMITH_ENV_SET, or to the value in the app's .duo/env) is the preflight's own, not yours: it is derived again.
# Exit 0 when nothing blocks, 1 when something does (nothing is written), 2 for a wrong call.
set -o pipefail

APP_ARG="${1:-}"
[ -n "$APP_ARG" ] || { echo "usage: bash preflight.sh <app folder>" >&2; exit 2; }
[ -d "$APP_ARG" ] || { echo "preflight.sh: no folder $APP_ARG" >&2; exit 2; }
APP="$(cd "$APP_ARG" && pwd)"
HERE="$(cd "$(dirname "$0")" && pwd)"
# The skill's copy (tools/) carries the driver and the tap project beside it; the repository keeps them elsewhere.
if [ -f "$HERE/driver/duo.py" ] || [ -d "$HERE/tap" ]; then
  BUNDLED="$HERE/driver/duo.py"; TAP="$HERE/tap/DuoTap.xcodeproj"
else
  ROOT="$(cd "$HERE/.." && pwd)"; BUNDLED="$ROOT/third_party/duo-driver/duo.py"; TAP="$ROOT/Tap/DuoTap.xcodeproj"
fi
APPS="${PREFLIGHT_APPLICATIONS:-/Applications}"   # where to look for an Xcode 27.1 that is not selected (tests set it)
TAP_BUILD="${DUO_TAP_BUILD:-$HOME/Library/Caches/duo-tap/build}"
MIN_CLAUDE=2.1.308

BLOCKS=0
row() { local tag="$1"; shift; printf '%-8s%s\n' "$tag" "$1"; shift
        local more; for more in "$@"; do printf '%-8s%s\n' "" "$more"; done; }
ok() { row ok "$@"; }
warn() { row warn "$@"; }
note() { row note "$@"; }
missing() { row missing "$@"; BLOCKS=$((BLOCKS + 1)); }
bounded() { perl -e 'alarm shift; exec @ARGV; exit 127' "$@"; }   # a wedged tool gives up instead of hanging this
# vercmp A B: -1, 0 or 1 as dotted version A is below, equal to or above B.
vercmp() {
  local IFS=. i x y; local -a a b; a=($1); b=($2)
  for ((i = 0; i < ${#a[@]} || i < ${#b[@]}; i++)); do
    x="${a[i]:-0}"; y="${b[i]:-0}"; x="${x//[^0-9]/}"; y="${y//[^0-9]/}"; x="${x:-0}"; y="${y:-0}"
    if ((10#$x > 10#$y)); then echo 1; return; fi
    if ((10#$x < 10#$y)); then echo -1; return; fi
  done
  echo 0
}
is_271() { [ "$(vercmp "$1" 27.1)" -ge 0 ] && [ "$(vercmp "$1" 27.2)" -lt 0 ]; }
q() { python3 -c 'import shlex, sys; print(shlex.quote(sys.argv[1]))' "$1" 2>/dev/null || printf "'%s'" "$1"; }
absolute() { local d="${1%/*}"; [ "$d" = "$1" ] && d=.; (cd "${d:-/}" && printf '%s/%s\n' "$(pwd)" "${1##*/}"); }

echo "Foldsmith preflight: $APP"

# --- Values inherited from .duo/env are the preflight's own, not yours
# The skill sources .duo/env before its tools, so a preflight can run with earlier answers in the environment: what the
# sourced file set (FOLDSMITH_ENV_SET, which it exports, whichever app's or skill copy's it was and however long ago),
# or a value equal to the one in the app's .duo/env now. Those were written by a preflight: they are derived again, so
# an updated skill moves DUO_PY and the tap runner to its own copy and a removed one blocks nothing. A value that
# differs is yours and wins. The app's .duo/env is read as text, never sourced.
prior_env() {   # the NAME=value pairs the .duo/env at $1 exports, one per line
  python3 - "$1" 2>/dev/null <<'PY'
import shlex, sys
try:
    words = shlex.split(open(sys.argv[1], encoding="utf-8").read(), comments=True)
except (OSError, UnicodeDecodeError, ValueError):
    sys.exit()
for i, word in enumerate(words[:-1]):
    if word == "export" and "=" in words[i + 1] and "\n" not in words[i + 1]:
        print(words[i + 1])
PY
}
INHERITED=()
drop_inherited() {   # reads NAME=value lines; a variable that holds that value now came from a .duo/env
  local kv k v
  while IFS= read -r kv; do
    k="${kv%%=*}"; v="${kv#*=}"
    case "$k" in DUO_UDID|DUO_PY|DUO_TAP_XCTESTRUN|DEVELOPER_DIR) ;; *) continue ;; esac
    if [ -n "${!k:-}" ] && [ "${!k}" = "$v" ]; then unset "$k"; INHERITED+=("$k"); fi
  done
}
PRIOR="$(prior_env "$APP/.duo/env")"
PRIOR_UDID="$(printf '%s\n' "$PRIOR" | sed -n 's/^DUO_UDID=//p' | head -1)"
drop_inherited <<< "${FOLDSMITH_ENV_SET:-}"
drop_inherited <<< "$PRIOR"
if [ ${#INHERITED[@]} -gt 0 ]; then
  note "${INHERITED[*]}: inherited from .duo/env (sourced before this ran), so derived again here, not taken as" \
       "yours; run the preflight in a shell that has not sourced .duo/env"
fi

# --- Xcode 27.1
DEV=
XV="$(bounded 60 xcodebuild -version 2>&1)"; XRC=$?
XVER="$(printf '%s\n' "$XV" | sed -n 's/^Xcode \([0-9][0-9.]*\).*/\1/p' | head -1)"
XBUILD="$(printf '%s\n' "$XV" | sed -n 's/^Build version //p' | head -1)"
SELECTED="$(xcode-select -p 2>/dev/null || true)"
FOUND=
for app in "$APPS"/Xcode*.app; do   # an Xcode 27.1 in /Applications, for when the selected one is not 27.1
  [ -f "$app/Contents/Info.plist" ] || continue
  v="$(plutil -extract CFBundleShortVersionString raw -o - "$app/Contents/Info.plist" 2>/dev/null)"
  if [ -n "$v" ] && is_271 "$v"; then FOUND="$app"; break; fi
done
NEWER=; [ "$XRC" -eq 0 ] && [ -n "$XVER" ] && [ "$(vercmp "$XVER" 27.2)" -ge 0 ] && NEWER=1
if [ "$XRC" -eq 0 ] && [ -n "$XVER" ] && is_271 "$XVER"; then
  DEV="${DEVELOPER_DIR:-}"   # one you chose for this shell goes into .duo/env too, so every tool call gets it
  ok "Xcode $XVER ($XBUILD)${DEVELOPER_DIR:+ at $DEVELOPER_DIR}"
elif printf '%s\n' "$XV" | grep -qi 'license'; then
  missing "Xcode's licence is not accepted yet${SELECTED:+ ($SELECTED)}: $(printf '%s\n' "$XV" | head -1)" \
          "fix: sudo xcodebuild -license accept   (then run this again)"
elif [ -n "$NEWER" ] && { [ -n "${DEVELOPER_DIR:-}" ] || [ -z "$FOUND" ]; }; then
  DEV="${DEVELOPER_DIR:-}"
  warn "Xcode $XVER ($XBUILD) is selected${DEVELOPER_DIR:+ (your DEVELOPER_DIR)}: the tools and the measured numbers" \
       "are from Xcode 27.1, and no Xcode 27.1 is in $APPS" \
       "fix (to match them): install Xcode 27.1 beside it (developer.apple.com/download/all); this then uses it" \
       "     through DEVELOPER_DIR"
else
  WHY="${XVER:+Xcode $XVER is selected}"
  FIRST="$(printf '%s\n' "$XV" | head -1)"
  [ -n "$WHY" ] || WHY="no Xcode answers: ${FIRST:-xcodebuild not found}"
  if [ -n "$FOUND" ]; then
    export DEVELOPER_DIR="$FOUND/Contents/Developer"
    XV="$(bounded 60 xcodebuild -version 2>&1)"; XRC=$?
    XVER2="$(printf '%s\n' "$XV" | sed -n 's/^Xcode \([0-9][0-9.]*\).*/\1/p' | head -1)"
    XBUILD="$(printf '%s\n' "$XV" | sed -n 's/^Build version //p' | head -1)"
    if [ "$XRC" -eq 0 ] && [ -n "$XVER2" ] && is_271 "$XVER2"; then
      DEV="$DEVELOPER_DIR"
      ok "Xcode $XVER2 ($XBUILD) at $FOUND ($WHY; .duo/env exports DEVELOPER_DIR for 27.1, so no sudo is needed)"
    elif printf '%s\n' "$XV" | grep -qi 'license'; then
      unset DEVELOPER_DIR
      missing "Xcode 27.1 at $FOUND: its licence is not accepted yet ($WHY)" \
              "fix: sudo $(q "$FOUND/Contents/Developer/usr/bin/xcodebuild") -license accept   (then run this again)"
    else
      unset DEVELOPER_DIR
      missing "Xcode 27.1 at $FOUND does not answer: $(printf '%s\n' "$XV" | head -1)" \
              "fix: open it once to finish its setup (or: sudo $(q "$FOUND/Contents/Developer/usr/bin/xcodebuild")" \
              "     -runFirstLaunch), then run this again"
    fi
  else
    missing "Xcode 27.1 ($WHY${SELECTED:+; selected: $SELECTED})" \
            "fix: install Xcode 27.1 (the Mac App Store, or developer.apple.com/xcode), then select it:" \
            "     sudo xcode-select -s /Applications/Xcode.app/Contents/Developer"
  fi
fi

# --- python3 (read early: the simulator list is JSON)
PYV="$(python3 -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null)"
HAVE_PY=; [ -n "$PYV" ] && [ "$(vercmp "$PYV" 3.9)" -ge 0 ] && HAVE_PY=1

# --- The iOS 27.1 runtime and a Duo simulator on it
UDID=; UDID_LINE=
if [ -z "$HAVE_PY" ]; then
  missing "iOS 27.1 simulator runtime: not read (needs python3, below)" "fix: the python3 line below"
  missing "Duo simulator: not read (needs python3, below)" "fix: the python3 line below"
else
  SIMS="$(bounded 120 xcrun simctl list -j 2>/dev/null | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except ValueError:
    print("error"); sys.exit()
def is271(v):
    return v == "27.1" or v.startswith("27.1.")
rt = next((r for r in d.get("runtimes", []) if r.get("platform", "iOS") == "iOS" and is271(r.get("version", ""))
           and r.get("isAvailable", True)), None)
dt = next((t.get("identifier") for t in d.get("devicetypes", []) if "duo" in t.get("name", "").lower()),
          "com.apple.CoreSimulator.SimDeviceType.iPhone-Duo")
print("runtime|%s|%s|%s" % ((rt or {}).get("identifier", ""), (rt or {}).get("version", ""),
                             (rt or {}).get("buildversion", "")))
print("devicetype|%s" % dt)
for runtime, devices in d.get("devices", {}).items():
    for x in devices:
        if not x.get("isAvailable", True):
            continue
        named = "duo" in x.get("name", "").lower()
        duo_type = "duo" in x.get("deviceTypeIdentifier", "").lower()
        here = rt is not None and runtime == rt["identifier"]
        kind = "duo" if named and here else "renamed" if duo_type and here else "elsewhere" if named else ""
        if kind:
            print("%s|%s|%s|%s|%s" % (kind, x["udid"], x.get("state", ""), runtime.rsplit(".", 1)[-1], x["name"]))
')"
  RT_ID=; RT_VER=; RT_BUILD=; DT_ID=com.apple.CoreSimulator.SimDeviceType.iPhone-Duo; DUOS=(); RENAMED=(); ELSEWHERE=()
  while IFS='|' read -r kind a b c rest; do
    case "$kind" in
      runtime) RT_ID="$a"; RT_VER="$b"; RT_BUILD="$c" ;;
      devicetype) DT_ID="$a" ;;
      duo) DUOS+=("$a|$b|$rest") ;;
      renamed) RENAMED+=("$a|$b|$rest") ;;
      elsewhere) ELSEWHERE+=("$a|$b|$c|$rest") ;;
    esac
  done <<< "$SIMS"
  if [ "$SIMS" = error ] || [ -z "$SIMS" ]; then
    missing "iOS 27.1 simulator runtime: xcrun simctl list did not answer" \
            "fix: open Xcode 27.1 once so it finishes installing its components, then run this again"
    missing "Duo simulator: not read (no simulator list)" "fix: the line above"
  elif [ -z "$RT_ID" ]; then
    missing "iOS 27.1 simulator runtime" \
            "fix: xcodebuild -downloadPlatform iOS   (with Xcode 27.1 selected; or Xcode > Settings > Components)"
    missing "Duo simulator: none without the iOS 27.1 runtime" "fix: the line above, then run this again"
  else
    ok "iOS $RT_VER simulator runtime ($RT_BUILD)"
    if [ ${#DUOS[@]} -gt 0 ]; then
      # The run's own simulator first: the one the progress file names (a resume signs in and captures there), then
      # the one .duo/env named.
      RUN_SIM="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1])).get("simulator") or "")' \
                 "$APP/.duo/migration.json" 2>/dev/null)"
      PICK=; TOOK=
      for want in "${DUO_UDID:-}|yours" "$RUN_SIM|the progress file's" "$PRIOR_UDID|the one .duo/env named"; do
        [ -n "${want%%|*}" ] || continue
        for s in "${DUOS[@]}"; do [ "${s%%|*}" = "${want%%|*}" ] && PICK="$s"; done
        if [ -n "$PICK" ]; then TOOK="${want#*|}"; break; fi
      done
      if [ -z "$PICK" ]; then
        BOOTED=()
        for s in "${DUOS[@]}"; do s2="${s#*|}"; [ "${s2%%|*}" = Booted ] && BOOTED+=("$s"); done
        if [ ${#BOOTED[@]} -eq 1 ]; then PICK="${BOOTED[0]}"; TOOK="the booted one"; else PICK="${DUOS[0]}"; TOOK="the first"; fi
      fi
      UDID="${PICK%%|*}"; rest="${PICK#*|}"; STATE="${rest%%|*}"; NAME="${rest#*|}"
      WHEN="booted"
      [ "$STATE" = Booted ] || WHEN="${STATE:-not booted} (duo.py boots it when a tool first uses it)"
      UDID_LINE="$NAME, iOS $RT_VER, $WHEN"
      ok "Duo simulator: $NAME ($UDID), $WHEN; duo.py drives only simulators whose name contains \"duo\""
      if [ -n "${DUO_UDID:-}" ] && [ "$DUO_UDID" != "$UDID" ]; then
        warn "DUO_UDID=$DUO_UDID is not an available Duo simulator on iOS $RT_VER: .duo/env sets $UDID ($TOOK)" \
             "fix (to use another): set DUO_UDID to one of: xcrun simctl list devices available | grep -i duo"
      elif [ -n "$RUN_SIM" ] && [ "$RUN_SIM" != "$UDID" ]; then
        warn "the progress file's simulator $RUN_SIM is not an available Duo on iOS $RT_VER: took $NAME ($UDID)," \
             "so the shots taken there and the ones to come are from two simulators" \
             "fix (if it was renamed or is on another runtime): xcrun simctl list devices | grep $RUN_SIM"
      elif [ ${#DUOS[@]} -gt 1 ] && [ -z "${DUO_UDID:-}" ]; then
        note "${#DUOS[@]} Duo simulators on iOS $RT_VER: took $NAME ($UDID), $TOOK; to take another, run this" \
             "again with DUO_UDID=<udid> set (xcrun simctl list devices available | grep -i duo lists them)"
      fi
    elif [ ${#RENAMED[@]} -gt 0 ]; then
      r="${RENAMED[0]}"; RU="${r%%|*}"; rest="${r#*|}"; RN="${rest#*|}"
      missing "Duo simulator: \"$RN\" ($RU) is an iPhone Duo," \
              "but duo.py drives only simulators whose name contains \"duo\"" \
              "fix: xcrun simctl rename $RU \"iPhone Duo\""
    else
      EXTRA=
      if [ ${#ELSEWHERE[@]} -gt 0 ]; then
        e="${ELSEWHERE[0]}"; rest="${e#*|}"; rest="${rest#*|}"; EXTRA=" (there is one on ${rest%%|*}: ${rest#*|})"
      fi
      missing "Duo simulator: none on iOS $RT_VER whose name contains \"duo\"$EXTRA" \
              "fix: xcrun simctl create \"iPhone Duo\" $DT_ID $RT_ID"
    fi
  fi
fi

if [ -n "$HAVE_PY" ]; then
  ok "python3 $PYV"
elif [ -n "$PYV" ]; then
  missing "python3 3.9 or later (found $PYV)" "fix: xcode-select --install   (or brew install python)"
else
  missing "python3" "fix: xcode-select --install   (Xcode's command line tools include it; or brew install python)"
fi

# --- rg
if command -v rg >/dev/null 2>&1; then
  ok "rg $(rg --version 2>/dev/null </dev/null | head -1 | sed 's/^ripgrep //') at $(command -v rg)"
elif [ -n "${CLAUDE_CODE_EXECPATH:-}" ] && [ -x "$CLAUDE_CODE_EXECPATH" ]; then
  ok "rg: Claude Code's own (none installed). Your commands get it as a shell function; scripts cannot call that," \
     "so routes.sh runs \$CLAUDE_CODE_EXECPATH as rg itself"
else
  missing "rg (ripgrep): the static scans and routes.sh read code with it" "fix: brew install ripgrep"
fi

# --- Free space on the home volume
AVAIL_KB="$(df -Pk "$HOME" 2>/dev/null | awk 'NR == 2 { print $4 }')"
if [ -z "$AVAIL_KB" ] || ! [ "$AVAIL_KB" -ge 0 ] 2>/dev/null; then
  warn "free space on the home volume: df did not answer" \
       "fix: check it yourself (df -h ~): a run needs 5 GB, 10 to be safe"
else
  GB="$(awk -v k="$AVAIL_KB" 'BEGIN { printf "%.1f", k * 1024 / 1e9 }')"
  WHERE1="     the usual places: Xcode's DerivedData (~/Library/Developer/Xcode/DerivedData), simulator runtimes"
  WHERE2="     you no longer use (xcrun simctl runtime list), this skill's build caches (~/Library/Caches/duo-*)"
  if [ "$AVAIL_KB" -lt 4882813 ]; then   # 5 GB
    missing "$GB GB free on the home volume: a run needs at least 5 GB (builds and captures fill it)" \
            "fix: free $(awk -v k="$AVAIL_KB" 'BEGIN { printf "%.1f", 5 - k * 1024 / 1e9 }') GB or more" \
                 "(nothing here deletes anything);" \
            "$WHERE1" "$WHERE2"
  elif [ "$AVAIL_KB" -lt 9765625 ]; then   # 10 GB
    warn "$GB GB free on the home volume: under 10 GB (a full capture with two builds has taken about 10)" \
         "fix (to be safe): free some space;" "$WHERE1" "$WHERE2"
  else
    ok "$GB GB free on the home volume"
  fi
fi

# --- The app folder: a git repository with nothing uncommitted outside .duo/
if ! command -v git >/dev/null 2>&1; then
  missing "git" "fix: xcode-select --install"
else
  INSIDE="$(git -C "$APP" rev-parse --is-inside-work-tree 2>&1)"
  # Every fix below leaves the app's .duo/ alone: an audit's progress file, flows, reports and captures are not
  # committed, and a stash or an `add -A` without this pathspec would take them along. Where the project's own rules
  # ignore the .duo folder itself (a .duo/ line in its .gitignore), git refuses that pathspec in `add` and `stash`
  # ("paths are ignored", exit 1) and leaves .duo/ out by itself: there the fix names no exclusion.
  BUT_DUO="':/' ':(exclude).duo'"
  [ "$INSIDE" = true ] && git -C "$APP" check-ignore -q -- .duo 2>/dev/null && BUT_DUO="':/'"
  if [ "$INSIDE" != true ]; then
    missing "$APP is not a git repository (the run commits each change on a branch):" \
            "$(printf '%s\n' "$INSIDE" | head -1)" \
            "fix: cd $(q "$APP") && git init && git add -A -- . ':(exclude).duo' && git commit -m \"Before the Duo migration\""
  else
    DIRTY="$(git -C "$APP" status --porcelain --untracked-files=all -- ':/' ':(exclude).duo' 2>&1)"; GRC=$?
    BRANCH="$(git -C "$APP" branch --show-current 2>/dev/null)"
    if [ "$GRC" -ne 0 ]; then
      missing "git status failed in $APP: $(printf '%s\n' "$DIRTY" | head -1)" \
              "fix: run git -C $(q "$APP") status and fix what it says"
    elif [ -n "$DIRTY" ]; then
      N="$(printf '%s\n' "$DIRTY" | wc -l | tr -d ' ')"
      SHOWN="$(printf '%s\n' "$DIRTY" | head -5 | sed 's/^ *//' | tr '\n' ';' | sed 's/;$//; s/;/, /g')"
      [ "$N" -gt 5 ] && SHOWN="$SHOWN, …"
      if [ "$BRANCH" = duo-migration ]; then
        missing "$APP has $N uncommitted change(s) outside .duo/ on duo-migration: $SHOWN" \
                "fix: they are the migration's own, a change an earlier session left unfinished (or a build's side" \
                "     effect, such as a rewritten Package.resolved). The run finishes and commits it, or puts it aside" \
                "     (git -C $(q "$APP") stash push --include-untracked -- $BUT_DUO), logs which, then runs this again"
      else
        missing "$APP has $N uncommitted change(s) outside .duo/ (the run commits on a branch): $SHOWN" \
                "fix: commit them, leaving .duo/ out: git -C $(q "$APP") add -A -- $BUT_DUO && git -C $(q "$APP") commit" \
                "     or put them aside, .duo/ kept: git -C $(q "$APP") stash push --include-untracked -- $BUT_DUO"
      fi
    else
      ok "$APP: git repository, nothing uncommitted outside .duo/ (${BRANCH:-detached HEAD})"
    fi
    # .duo/ is the run's working folder, never committed: files an earlier run committed there would ride along in
    # every commit's tree and in a pull request.
    TRACKED="$(git -C "$APP" ls-files -- .duo 2>/dev/null)"
    if [ -n "$TRACKED" ]; then
      N="$(printf '%s\n' "$TRACKED" | wc -l | tr -d ' ')"
      SHOWN="$(printf '%s\n' "$TRACKED" | head -3 | tr '\n' ';' | sed 's/;$//; s/;/, /g')"
      [ "$N" -gt 3 ] && SHOWN="$SHOWN, …"
      warn "$N file(s) under .duo/ are tracked by git, so a pull request would carry them (the run no longer" \
           "commits .duo/): $SHOWN" \
           "fix: git -C $(q "$APP") rm -r --cached -- .duo, then commit that" \
           "     (the files stay on disk, and .git/info/exclude keeps .duo/ out from then on). After that commit," \
           "     never check out an earlier commit, or another run's duo-migration, in the app folder: git overwrites" \
           "     the ignored .duo/ with the old files and deletes it on the way back. Read old code with" \
           "     git show <rev>:<path>, or in a git worktree outside the folder"
    fi
    REMOTE_RUN="$(git -C "$APP" for-each-ref --format='%(refname:short)' 'refs/remotes/*/duo-migration' 2>/dev/null \
                  | head -1)"
    if [ -n "$REMOTE_RUN" ] && ! git -C "$APP" show-ref --verify --quiet refs/heads/duo-migration; then
      note "$REMOTE_RUN exists and there is no local duo-migration: a plain git checkout duo-migration would track" \
           "it (another run's branch), so the run makes its own: git switch -c duo-migration --no-track"
    fi
    # A run never gives duo-migration an upstream (--no-track, never push). One that tracks */duo-migration was made
    # by a plain checkout of another run's branch, whose commits it now holds, or the person pushed this run's branch
    # (git push -u, a pull request): the branch's first reflog entry tells them apart (its start point a remote's
    # branch, or HEAD). With no reflog, the warning says both. The run does not act on it.
    UPSTREAM="$(git -C "$APP" rev-parse --abbrev-ref 'duo-migration@{upstream}' 2>/dev/null)"
    case "$UPSTREAM" in
      */duo-migration)
        FIRST="$(git -C "$APP" reflog show --format=%gs refs/heads/duo-migration -- 2>/dev/null | tail -1)"
        FROM="${FIRST#branch: Created from }"
        if [ "$FROM" = "$FIRST" ]; then
          ORIGIN=unknown
        else
          ORIGIN=local
          case "$FROM" in refs/remotes/*) ORIGIN=remote ;; esac
          for R in $(git -C "$APP" remote 2>/dev/null); do
            case "$FROM" in "$R"/*) ORIGIN=remote ;; esac
          done
        fi
        UNSET="fix: git -C $(q "$APP") branch --unset-upstream duo-migration, and check that"
        LOGGED="     git -C $(q "$APP") log --oneline <base>..duo-migration holds only this run's commits"
        case "$ORIGIN" in
          remote)
            warn "duo-migration tracks $UPSTREAM, another run's branch (made from $FROM, as a plain git checkout" \
                 "duo-migration does)" \
                 "$UNSET" "$LOGGED" ;;
          unknown)
            warn "duo-migration tracks $UPSTREAM: if a plain git checkout of another run's branch made it, it holds" \
                 "that run's commits; if you pushed this run's branch yourself (a pull request), leave it" \
                 "$UNSET" "$LOGGED" ;;
        esac ;;   # made here from HEAD and pushed: this run's own, nothing to say
    esac
  fi
fi

# --- The CI's Xcode (sdkguard.py reads the CI files; a branch must still build with that Xcode)
if [ -n "$HAVE_PY" ]; then
  if [ -f "$HERE/sdkguard.py" ]; then
    CI_OUT="$(SDKGUARD_APPLICATIONS="$APPS" bounded 60 python3 "$HERE/sdkguard.py" --ci-only "$APP" 2>&1 </dev/null)"
    CI_SAY="$(printf '%s\n' "$CI_OUT" | sed -n 's/^verdict: //p' | head -1)"
    [ -n "$CI_SAY" ] || CI_SAY="sdkguard.py --ci-only gave no verdict: $(printf '%s\n' "$CI_OUT" | tail -1)"
  else
    CI_SAY="no CI check: sdkguard.py is missing beside this script ($HERE); reinstall the skill"
  fi
  CI_ROWS=()   # the sentence in rows of at most 110 characters, a path or a flag never split
  while IFS= read -r line; do CI_ROWS+=("$line"); done < <(python3 -c 'import sys, textwrap
print("\n".join(textwrap.wrap(sys.argv[1], 110, break_on_hyphens=False, break_long_words=False)))' "$CI_SAY")
  note "${CI_ROWS[@]}"
fi

# --- Claude Code
CV=; CSRC=
if [ -n "${CLAUDE_CODE_EXECPATH:-}" ] && [ -x "$CLAUDE_CODE_EXECPATH" ]; then
  CV="$(bounded 20 "$CLAUDE_CODE_EXECPATH" --version 2>/dev/null </dev/null | head -1)"; CSRC="this session"
elif command -v claude >/dev/null 2>&1; then
  CV="$(bounded 20 claude --version 2>/dev/null </dev/null | head -1)"; CSRC="claude on PATH"
fi
CNUM="$(printf '%s\n' "$CV" | sed -n 's/^\([0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\).*/\1/p')"
if [ -z "$CSRC" ]; then
  note "Claude Code: not found (no claude on PATH). The skill runs in other agents too; the Foldsmith pane needs" \
       "Claude Code $MIN_CLAUDE or later"
elif [ -z "$CNUM" ]; then
  warn "Claude Code ($CSRC): could not read its version (${CV:-no answer})" "fix: claude update"
elif [ "$(vercmp "$CNUM" "$MIN_CLAUDE")" -lt 0 ]; then
  warn "Claude Code $CNUM ($CSRC): the Foldsmith pane needs $MIN_CLAUDE or later (the skill runs without it)" \
       "fix: claude update"
else
  ok "Claude Code $CNUM ($CSRC)"
fi

# --- The driver and the tap runner (paths for .duo/env)
PY_PATH=
if [ -n "${DUO_PY:-}" ]; then
  if [ -f "$DUO_PY" ]; then
    PY_PATH="$(absolute "$DUO_PY")"; ok "duo.py: DUO_PY=$PY_PATH (yours; the bundled one is $BUNDLED)"
  else
    missing "duo.py: DUO_PY=$DUO_PY does not exist" "fix: unset DUO_PY to use the bundled driver ($BUNDLED)"
  fi
elif [ -f "$BUNDLED" ] && [ -f "$(dirname "$BUNDLED")/duo_fold.c" ]; then
  PY_PATH="$BUNDLED"; ok "duo.py: the bundled driver, $BUNDLED"
else
  missing "duo.py: the bundled driver is missing or incomplete at $(dirname "$BUNDLED")" \
          "fix: reinstall the skill (its tools/driver/ holds duo.py and duo_fold.c)"
fi

XCTESTRUN=
BUILD_CMD="xcodebuild build-for-testing -project $(q "$TAP") -scheme DuoTapUITests"
[ -z "$DEV" ] || BUILD_CMD="DEVELOPER_DIR=$(q "$DEV") $BUILD_CMD"   # the Xcode 27.1 .duo/env names, run as printed
BUILD_CMD="$BUILD_CMD -destination \"platform=iOS Simulator,id=${UDID:-\$DUO_UDID}\""
BUILD_CMD="$BUILD_CMD -derivedDataPath $(q "$TAP_BUILD") -quiet"
if [ -n "${DUO_TAP_XCTESTRUN:-}" ] && [ -f "$DUO_TAP_XCTESTRUN" ]; then
  XCTESTRUN="$(absolute "$DUO_TAP_XCTESTRUN")"; ok "tap runner: DUO_TAP_XCTESTRUN=$XCTESTRUN (yours)"
else
  [ -n "${DUO_TAP_XCTESTRUN:-}" ] && warn "tap runner: DUO_TAP_XCTESTRUN=$DUO_TAP_XCTESTRUN does not exist" \
    "fix: unset it; .duo/env takes the one built below"
  BUILT="$(ls -t "$TAP_BUILD"/Build/Products/DuoTapUITests_*.xctestrun 2>/dev/null | head -1)"
  NEWER=
  [ -n "$BUILT" ] && [ -d "$(dirname "$TAP")" ] && NEWER="$(find -H "$(dirname "$TAP")" -newer "$BUILT" \
    \( -name '*.swift' -o -name project.pbxproj \) 2>/dev/null | head -1)"
  if [ -n "$BUILT" ] && [ -z "$NEWER" ]; then
    XCTESTRUN="$BUILT"; ok "tap runner: built, $BUILT"
  elif [ -n "$BUILT" ]; then
    note "tap runner: built before its source changed ($NEWER);" \
         "rebuild it (about 10 s), then run this again:" "$BUILD_CMD"
  else
    note "tap runner: not built yet; the capture needs it. Build it (about 10 s), then run this again:" "$BUILD_CMD"
  fi
fi

# --- Verdict, and .duo/env
if [ "$BLOCKS" -gt 0 ]; then
  echo "blocked: $BLOCKS item(s) marked missing above; nothing was written. Fix them, then run this again."
  exit 1
fi
EXCLUDE="$(git -C "$APP" rev-parse --git-path info/exclude)"
case "$EXCLUDE" in /*) ;; *) EXCLUDE="$APP/$EXCLUDE" ;; esac
# Everything in the app's .duo/, from the repository's top, as a gitignore pattern: .duo/env holds this Mac's paths, and
# the progress file, flows, reports and captures are the run's working files, never committed. `.duo/*`, not `.duo/`:
# with the folder itself ignored, git refuses `add -A -- . ':(exclude).duo'` and the same stash ("paths are ignored",
# exit 1), the commands the fixes above print; with its contents ignored both forms work, and plain `git add -A` too.
# [ ] * ? and \ in a folder's name are escaped, so "ios app [beta]" is that folder, not a class of characters; the line
# starts with "/", so a # or ! in a name is plain. An older preflight's .duo/env line is left as it is.
ENTRY="/$(git -C "$APP" rev-parse --show-prefix | sed 's/[][\\*?]/\\&/g').duo/*"
if ! grep -qxF "$ENTRY" "$EXCLUDE" 2>/dev/null; then
  mkdir -p "$(dirname "$EXCLUDE")"
  [ -s "$EXCLUDE" ] && [ -n "$(tail -c 1 "$EXCLUDE")" ] && echo >> "$EXCLUDE"
  printf '%s\n' "$ENTRY" >> "$EXCLUDE" || { echo "could not write $EXCLUDE" >&2; exit 1; }
fi
mkdir -p "$APP/.duo"
TMP="$APP/.duo/env.tmp.$$"
{
  echo "# Written by Foldsmith's preflight.sh, $(date -u +%Y-%m-%dT%H:%M:%SZ); run it again (without sourcing this) to refresh."
  echo "# Source it before each tool: source .duo/env"
  if [ -n "$DEV" ]; then echo "export DEVELOPER_DIR=$(q "$DEV")"; fi
  echo "export DUO_UDID=$(q "$UDID")"
  echo "export DUO_PY=$(q "$PY_PATH")"
  if [ -n "$XCTESTRUN" ]; then echo "export DUO_TAP_XCTESTRUN=$(q "$XCTESTRUN")"; fi
  echo "export FOLDSMITH_ENV=$(q "$APP/.duo/env")"
  SET="DUO_UDID=$UDID"$'\n'"DUO_PY=$PY_PATH"
  [ -z "$XCTESTRUN" ] || SET="$SET"$'\n'"DUO_TAP_XCTESTRUN=$XCTESTRUN"
  [ -z "$DEV" ] || SET="$SET"$'\n'"DEVELOPER_DIR=$DEV"
  echo "# What this file set, NAME=value per line: a preflight run after sourcing it derives those again."
  echo "export FOLDSMITH_ENV_SET=$(q "$SET")"
} > "$TMP" && mv -f "$TMP" "$APP/.duo/env" || { rm -f "$TMP"; echo "could not write $APP/.duo/env" >&2; exit 1; }
echo "wrote $APP/.duo/env (.duo/ is kept out of git by $ENTRY in .git/info/exclude); source it before each tool:"
if [ -n "$DEV" ]; then echo "  DEVELOPER_DIR=$DEV"; fi
echo "  DUO_UDID=$UDID ($UDID_LINE)"
echo "  DUO_PY=$PY_PATH"
if [ -n "$XCTESTRUN" ]; then echo "  DUO_TAP_XCTESTRUN=$XCTESTRUN"
else echo "  DUO_TAP_XCTESTRUN: not yet (the note above builds the tap runner; run this again after)"; fi
exit 0
