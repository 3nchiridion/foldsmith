#!/usr/bin/env bash
# Every way onto and around an app's navigation stacks, as a Markdown table: the route inventory a structural change
# lists before it starts (SKILL.md) and takes through the change, every line of it, in the same commit.
#
# Usage:
#   bash routes.sh <app folder> [<type or file name> …]
# With names, only lines in the files that mention one of them as a word, or that are so named (`Foo` or `Foo.swift`).
# Swift only, read with rg (ripgrep, which the static scans need too; where none is installed, Claude Code's own,
# through $CLAUDE_CODE_EXECPATH); tests (`*Tests/` folders, `*Tests.swift`), build folders (`build`, `.build`,
# `DerivedData`, `SourcePackages`, `Pods`, `Carthage`), what git ignores and comment lines are left out.
#
# Prints `| file:line | kind | code |`, paths relative to the app folder, then a count by kind. Each line gets one kind,
# the first that matches in this order:
#   set           setViewControllers(, .viewControllers = , viewControllers = (a stack replaced whole); a SwiftUI path
#                 replaced or emptied, not declared (…path = [], …path = [.…, …path = NavigationPath(,
#                 …path.removeAll()
#   push          pushViewController(, show(… sender:), showDetailViewController(… sender:); …path.append(, and a
#                 router's navigate(to: (IceCubesApp's `routerPath.navigate(to: .statusDetail…)`)
#   pop           popViewController(, popToRootViewController(, popToViewController(, …path.removeLast(
#   present       present(, .sheet(, .fullScreenCover(, .popover(
#   swiftui       NavigationStack, NavigationSplitView, NavigationPath, NavigationLink, .navigationDestination(
#   restore       restorationIdentifier, stateRestorationActivity, NSUserActivity, onContinueUserActivity,
#                 continueUserActivity, restoreUserActivityState, SceneStorage, saveState, restoreState, save…State and
#                 restore…State (saveNavigationState; not Core Graphics' saveGState)
#   url           onOpenURL, openURLContexts, application(_:open:options:), handlesExternalEvents, and deep link
#                 handlers: a func named route…, navigate…, handle… or open… whose first parameter is a URL named
#                 url… or link…, or a func with DeepLink in its name
#   notification  UNUserNotificationCenterDelegate, userNotificationCenter(, UNNotificationResponse,
#                 didReceiveRemoteNotification
#   shortcut      UIApplicationShortcutItem, performActionFor, shortcutItem (quick actions)
#   walk          as? / as! UINavigationController, selectedViewController, presentedViewController, topViewController,
#                 visibleViewController, .viewControllers, navigationController? / navigationController!
# A line is a place to read, not a defect: a walk that expects a navigation controller, or a route that reaches a stack
# without the change, is what a structural change breaks where no capture goes. An app's own router is listed only
# where it calls navigate(to:) or changes a …path; follow the rest of its methods and properties by hand (IceCubesApp
# presents its sheets by setting `routerPath.presentedSheet`).
# Exit 0, also when nothing matches ("no routes found"); 2 for a wrong call or without rg.
set -o pipefail

usage() { echo "usage: bash routes.sh <app folder> [<type or file name> …]" >&2; exit 2; }
[ $# -ge 1 ] || usage
case "$1" in -h|--help) usage ;; esac
DIR="$1"; shift
[ -d "$DIR" ] || { echo "routes.sh: no folder $DIR" >&2; exit 2; }
WORK=$(mktemp -d "${TMPDIR:-/tmp}/routes.XXXXXX") || exit 2
trap 'rm -rf "$WORK"' EXIT
LIST="$WORK/files"
if ! command -v rg >/dev/null 2>&1 && [ -n "${CLAUDE_CODE_EXECPATH:-}" ] && [ -x "$CLAUDE_CODE_EXECPATH" ]; then
  # Claude Code answers as rg when started under that name; its shell gives rg as a function, which this script and
  # xargs cannot call, so a file of that name stands in for it.
  mkdir "$WORK/bin" && printf '#!/bin/bash\nexec -a rg "$CLAUDE_CODE_EXECPATH" "$@"\n' > "$WORK/bin/rg" &&
    chmod +x "$WORK/bin/rg" && export CLAUDE_CODE_EXECPATH && PATH="$WORK/bin:$PATH"
  rg --version >/dev/null 2>&1 < /dev/null || PATH="${PATH#"$WORK/bin:"}"
fi
command -v rg >/dev/null 2>&1 || { echo "routes.sh: needs rg (ripgrep): brew install ripgrep (in Claude Code it uses" \
  "Claude Code's own rg when none is installed)" >&2; exit 2; }
cd "$DIR" || exit 2
export LC_ALL=C

SCOPE=(--type swift
  -g '!*Tests/' -g '!*Tests.swift'
  -g '!build/' -g '!.build/' -g '!DerivedData/' -g '!SourcePackages/' -g '!Pods/' -g '!Carthage/')

KINDS=(set push pop present swiftui restore url notification shortcut walk)
patterns() {
  case "$1" in
    set) printf '%s\n' '\bsetViewControllers\(' '\.viewControllers\s*=[^=]' '^\s*viewControllers\s*=[^=]' \
      '(\.|^\s*)\w*[Pp]ath\s*=\s*(\[\s*[].]|NavigationPath\()' '\b\w*[Pp]ath\.removeAll\(' ;;
    push) printf '%s\n' '\bpushViewController\(' '\b(show|showDetailViewController)\(.*\bsender:' \
      '\b\w*[Pp]ath\.append\(' '\bnavigate\(to:' ;;
    pop) printf '%s\n' '\bpop(ViewController|ToRootViewController|ToViewController)\(' '\b\w*[Pp]ath\.removeLast\(' ;;
    present) printf '%s\n' '\bpresent\(' '\.(sheet|fullScreenCover|popover)\(' ;;
    swiftui) printf '%s\n' '\b(NavigationStack|NavigationSplitView|NavigationPath|NavigationLink)\b' \
      '\.navigationDestination\(' ;;
    restore) printf '%s\n' '\b(restorationIdentifier|stateRestorationActivity|NSUserActivity)\b' \
      '\b(onContinueUserActivity|continueUserActivity|restoreUserActivityState|SceneStorage)\b' \
      '\b(save|restore)(State|[A-Z]\w+State)\b' ;;
    url) printf '%s\n' '\b(onOpenURL|openURLContexts|handlesExternalEvents)\b' 'func application\(.*\bopen url\b' \
      'func (route|navigate|handle|open)\w*\((_ )?\w*\s*(?i:url|link)\w*\s*:\s*URL\b' 'func \w*[Dd]eep[Ll]ink\w*\(' ;;
    notification) printf '%s\n' '\b(UNUserNotificationCenterDelegate|UNNotificationResponse)\b' \
      '\buserNotificationCenter\(' '\bdidReceiveRemoteNotification\b' ;;
    shortcut) printf '%s\n' '\b(UIApplicationShortcutItem|performActionFor|shortcutItem)\b' ;;
    walk) printf '%s\n' '\bas[?!]\s*UINavigationController\b' \
      '\b(selectedViewController|presentedViewController|topViewController|visibleViewController)\b' \
      '\.viewControllers\b' '\bnavigationController[?!]' ;;
  esac
}

# The files to read: every Swift file in scope, or, with names, those that mention one or are so named.
if [ $# -gt 0 ]; then
  WORDS=(); for name in "$@"; do WORDS+=(-e "$name"); done
  {
    rg -l -w -F "${WORDS[@]}" "${SCOPE[@]}" -- . < /dev/null 2>/dev/null
    rg --files "${SCOPE[@]}" -- . < /dev/null 2>/dev/null | awk -v names="$*" '
      BEGIN { n = split(names, want, " ") }
      { base = $0; sub(/.*\//, "", base); stem = base; sub(/\.swift$/, "", stem)
        for (i = 1; i <= n; i++) if (want[i] == base || want[i] == stem) { print; next } }'
  } | sed 's|^\./||' | sort -u > "$LIST"
else
  rg --files "${SCOPE[@]}" -- . < /dev/null 2>/dev/null | sed 's|^\./||' | sort > "$LIST"
fi

: > "$LIST.rows"
if [ -s "$LIST" ]; then
  rank=0
  for kind in "${KINDS[@]}"; do
    rank=$((rank + 1))
    EXPRS=(); while IFS= read -r p; do EXPRS+=(-e "$p"); done < <(patterns "$kind")
    # A path always follows, so rg never reads its standard input (it does when given no path and stdin is a pipe).
    tr '\n' '\0' < "$LIST" | xargs -0 rg -n -H --no-heading --color never "${EXPRS[@]}" -- 2>/dev/null |
      awk -v kind="$kind" -v rank="$rank" '
        { if (!match($0, /:[0-9]+:/)) next
          file = substr($0, 1, RSTART - 1); line = substr($0, RSTART + 1, RLENGTH - 2)
          code = substr($0, RSTART + RLENGTH)
          sub(/^[ \t]+/, "", code); sub(/[ \t\r]+$/, "", code)
          if (code ~ /^(\/\/|\/\*|\*)/) next
          printf "%s\t%s\t%d\t%s\t%s\n", file, line, rank, kind, code }' >> "$LIST.rows"
  done
fi

if [ ! -s "$LIST.rows" ]; then
  if [ $# -gt 0 ]; then echo "no routes found (in the Swift files that mention or are named: $*)"
  else echo "no routes found"; fi
  exit 0
fi

sort -t "$(printf '\t')" -k1,1 -k2,2n -k3,3n "$LIST.rows" | awk -F '\t' -v kinds="${KINDS[*]}" '
  function tail(s) { return substr(s, length(s), 1) }
  function chop(s) { return substr(s, 1, length(s) - 1) }
  BEGIN { print "| file:line | kind | code |"; print "|---|---|---|" }
  { key = $1 ":" $2; if (key == last) next; last = key
    code = $0; for (i = 1; i <= 4; i++) sub(/^[^\t]*\t/, "", code)
    if (length(code) > 160) {   # 157 bytes, then back to the start of a character, so no UTF-8 sequence is split
      code = substr(code, 1, 157)
      while (code != "" && tail(code) >= "\200" && tail(code) < "\300") code = chop(code)
      if (tail(code) >= "\300") code = chop(code)
      code = code "…" }
    gsub(/\|/, "\\|", code)
    fence = index(code, "`") ? "`` " : "`"; close_ = index(code, "`") ? " ``" : "`"
    printf "| %s:%s | %s | %s%s%s |\n", $1, $2, $4, fence, code, close_
    count[$4]++; total++ }
  END { n = split(kinds, k, " "); summary = ""
        for (i = 1; i <= n; i++) if (count[k[i]]) summary = summary (summary == "" ? "" : " · ") k[i] " " count[k[i]]
        printf "\n%d lines: %s\n", total, summary }'
exit 0
