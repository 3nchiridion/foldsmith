#!/usr/bin/env python3
"""Does the migration still build with the Xcode the project's own CI uses? Read-only: it runs git's read commands and
reads files, and writes nothing.

    python3 sdkguard.py [<app folder>] [--base <rev>] [--scheme <name>] [--ci-only]

`#available` is a run-time check, and neither it nor `@available` hides a symbol the SDK lacks from the compiler: an
Xcode whose SDK lacks an iOS 27 symbol does not compile a line that names it. Only a compile-time check keeps such a
line from the older compiler. Xcode 27.1 ships Swift 6.4 (swiftlang-6.4.0.34.1), and so does Xcode 27.0, so `#if
compiler(>=6.4)` separates Xcode 26.x from 27.x, and passes on both 27.0 and 27.1: no supported compile-time check
separates those two.

The CI's Xcode. The repository's top folder and the app folder are read for the Xcode a CI selects:
  .github/workflows/*.yml|*.yaml, .github/actions/**/action.yml|yaml, the .sh scripts a workflow runs, .xcode-version,
  .circleci/config.yml, bitrise.yml, .gitlab-ci.yml, .travis.yml, fastlane/Fastfile, Makefile, ci_scripts/
in the forms Xcode_26.6.app, Xcode-26.6.app (DEVELOPER_DIR, xcode-select), xcode-version: '26.6' (setup-xcode), xcode:
"26.6" (CircleCI), xcodes select 26.6, osx_image: xcode26.6, a stack: or image: named …xcode-26.6…,
ensure_xcode_version(version: "26.6"), and .xcode-version's own content, comments left out. A version given through a
GitHub matrix (a list under a key, flow or block, or include: entries) or a variable (XCODE: "26.6", XCODE=26.6, export
too, XCODE ?= 26.6, := and ::=; a shell default, XCODE="${XCODE:-26.6}" or : "${XCODE:=26.6}", under a value the
workflow passes in, and XCODE=${1:-26.6}, the script's own) is read where it is used (${{ matrix.xcode }},
${{ env.XCODE }}, $XCODE, ${XCODE}, $(XCODE); ${XCODE:-26.6} is its default where XCODE is not set), every value of a
matrix; a list under an xcode key, and a variable named XCODE or …XCODE_VERSION…, are read where they are set too (a
default only where it holds). A workflow is read with its parts and the variables it sets: the .sh scripts it runs, the
Makefile when it runs make, and the local actions it uses (uses: ./…). Each version is printed with file:line; the
lowest is the constraint. A workflow that builds (xcodebuild, swift build or test, fastlane) on a macos runner, itself
or through its parts, or asks setup-xcode for latest or latest-stable, and names no version there (xcodes or xcversion
with no version reads .xcode-version) is printed too: the runner image's default Xcode builds it, which the repository
does not name. ci_scripts/ is Xcode Cloud, whose Xcode is set in App Store Connect, not in the repository.

Installed Xcodes: each /Applications/Xcode*.app with its Contents/version.plist version. When one matches the CI's,
the build line that proves the branch compiles with it (DEVELOPER_DIR=… xcodebuild … build, into
~/Library/Caches/duo-build/<app>-ci); --scheme fills its scheme, else it reads <scheme>.

Unguarded uses. The base is --base, else duo-baseline when that ref exists, else the merge base with origin/HEAD (not
when that is a duo-migration branch), main or master; none: exit 2, asking for --base. In each Swift file changed
between the base and the working tree (untracked ones whole, .duo/ left out), the whole file's #if/#elseif/#else/#endif
nesting is read and only the added lines are checked. A line is guarded when a branch around it cannot be compiled by
a compiler older than 6.4: `#if compiler(>=6.4)` (also with `&&`), the #else of `#if compiler(<6.4)` or of
`#if !compiler(>=6.4)`. Flagged, outside comments and string literals: an `#available(`, `#unavailable(` or
`@available(` naming iOS 27 or later (or anyAppleOS); a curated iOS 27.0/27.1 symbol (SDK_SYMBOLS below, the names the
patterns and references use); a Foldsmith reference type, whose file is compiled only by Swift 6.4 and needs the iOS
27.1 SDK, so a call site is guarded too; and a name the branch declares only inside a compile-time guard, read from
every changed Swift file first: a type, a top-level function or variable, a member of an extension (a
Notification.Name), a member of a type that is not itself inside the guard (a private one counts in its own file
only, an enum case too unless named with its enum, PaneLayout.foldTiled; an override's name is its superclass's, in a
type's body or in an extension), a member of a type written whole in the guard that its pre-Duo twin in #else lacks,
and a local let, var or func where it is used bare in the rest of its block; each name of a list (case a, b; var a =
0, b = 0); a property-wrapped var's $x and _x too (Toggle(isOn: $x), _x = State(initialValue:), model.$x). The older
compiler skips that code and does not know the name, so its uses go inside the guard too. A name also declared outside
a guard at the top level or in an extension (an #else stub) is not one; nor is a type's member also declared outside a
guard at the top level, in an extension of the same type or by the same type in its #else (for $x and _x, a wrapped
stub: an #else let x has no $x); nor is a local also declared outside a guard at the top level or in an extension of
the type its block sits in. Beside an extension of another type that declares it outside the guard (UIView's
isBookFoldActive beside a view controller's own guarded one), a guarded member counts where it is used bare or through
self inside its type's body, and not elsewhere: another use may be the extension's. A name a type declares outside the
guard as its own member is that member where it is used bare or through self inside that type's body and its
extensions' (a private one's in its own file); a local or a parameter is that local where it is used bare in its
block, from the line after a let or var, from just after its { for a closure's parameter ({ [weak self] x in), and only
inside the block an if, while, for or catch binding opens. self.name is never a local, so self.x = x, let x = self.x
and if let x = x read the member, and the shorthand if let x { and guard let x else read the x outside, on a line that
continues the condition too (if let a = b, then let x {). Another receiver's .name, an implicit .name, and every use
elsewhere still count. Scope is read from braces. The line that declares a name is not a use of it, nor is a label
named like it (f(x: 1), func f(x: Int), case a(x: Int), x y: Int, a call's x: alone on its line, } x: {), whereas the
value in f(x: x), c ? x : y and [x: 1] are uses; a dictionary key after a comma or alone on its line is read as a
label. A guarded local named like something the SDK or a superclass declares (let title) is flagged where its bare
use would compile with the guard false: that code then means something else. A Foldsmith name the app declares itself
outside a guard is the app's (a note), not Foldsmith's.
An availability check split over lines counts on its first line. `// sdkguard: ok <why>` on the line, or alone on the
line above, waives it (UITab.preferredPlacement, iOS 18, shares a curated name: a tab's line is waived so); each
waived line is listed with its why, for the review.

Verdict and exit code:
  CI lowest below 27  every flagged line is an error (exit 1): a symbol does not compile there (wrap it in #if
                      compiler(>=6.4) … #else <the pre-Duo code> #endif, keeping #available inside); an availability
                      check compiles but opens iOS 27 code, so it goes inside the guard with that code. The two are
                      counted apart.
  CI exactly 27.0     lines with 27.1 symbols are errors (exit 1), inside a compiler guard too, since 27.0 passes it:
                      propose moving CI to Xcode 27.1 in .duo/PLAN.md. 27.0 symbols and availability checks pass.
  CI 27.1 or later,   flagged lines are notes (exit 0).
  or none named
  2 for a wrong call: no such folder or revision, no base, not a git repository.
--ci-only prints the CI and installed-Xcode lines and the verdict sentence only (what the CI's Xcode means for the
run), reads no code, and always exits 0. The preflight prints that sentence as a note.
"""
import argparse
import bisect
import collections
import os
import pathlib
import plistlib
import re
import shlex
import subprocess
import sys

# --- Curated symbols: name → iOS version, as the iOS 27.1 SDK of Xcode 27.1 (27A9275) declares it (SwiftUI and
# SwiftUICore swiftinterfaces, UIKit's swiftinterface and headers). test_sdkguard.py checks every one against the
# installed SDK, and that the patterns and references name no iOS 27 symbol left out here. Members that only appear with
# one of these (.division, .includeInactive, .verticalPreferred, .trailing) are not listed: their call is.
SDK_SYMBOLS = {
    # SwiftUI: arrangements
    "ArrangementView": "27.1",
    "ArrangementViewStyle": "27.1",
    "arrangementViewStyle": "27.1",
    "SplitArrangementViewStyle": "27.1",
    "OverlayArrangementViewStyle": "27.1",
    "splitArrangementLayoutRatio": "27.1",
    "splitArrangementLayoutSize": "27.1",
    "splitArrangementFixedLayoutSize": "27.1",
    "splitArrangementAxis": "27.1",
    "overlayArrangementEdge": "27.1",
    "overlayArrangementZIndex": "27.1",
    # SwiftUI: reserved regions, the hinge
    "reservedRegions": "27.1",          # SwiftUI GeometryProxy and UIKit UIView
    "ReservedRegion": "27.1",
    "onHingeChange": "27.1",
    "DeviceHinge": "27.1",
    "DeviceHingeContext": "27.1",
    # SwiftUI: bars
    "toolbarVerticalEdge": "27.1",
    "toolbarVerticalBehavior": "27.1",
    "ToolbarVerticalBehavior": "27.1",
    "toolbarVerticalCompressionBehavior": "27.1",
    "ToolbarVerticalCompressionBehavior": "27.1",
    "axisBehavior": "27.1",             # SwiftUI ToolbarContent and UIKit UIBarButtonItem
    "ToolbarItemAxisBehavior": "27.1",
    "visibilityPriority": "27.0",       # SwiftUI ToolbarContent and UIKit UIBarButtonItem
    "ToolbarItemVisibilityPriority": "27.0",
    "ToolbarOverflowMenu": "27.0",
    "topBarPinnedTrailing": "27.0",
    "defaultTabBarPlacement": "27.0",
    # SwiftUI: sheets
    "presentationPlacement": "27.0",
    "PresentationPlacement": "27.0",
    # UIKit: arrangements
    "UIArrangementViewController": "27.1",
    "UISplitArrangement": "27.1",
    "UIOverlayArrangement": "27.1",
    "arrangementViewController": "27.1",
    "updateArrangement": "27.1",
    "setViewProperties": "27.1",
    # UIKit: the hinge, the vertical bar
    "UIHinge": "27.1",
    "UIHingeInteraction": "27.1",
    "UIVerticalBarEdge": "27.1",
    "verticalBarEdge": "27.1",
    "systemTraitsAffectingVerticalBarEdge": "27.1",
    "UIVerticalBarBehavior": "27.1",
    "preferredVerticalBarBehavior": "27.1",
    "childForPreferredVerticalBarBehavior": "27.1",
    "setNeedsUpdateOfVerticalBarConfiguration": "27.1",
    "UIVerticalBarCompressionBehavior": "27.1",
    "verticalBarCompressionBehavior": "27.1",
    "UIBarButtonItem.AxisBehavior": "27.1",
    # UIKit: bar items, sheets
    "UIBarButtonItemVisibilityPriority": "27.0",
    "isPaddingRemoved": "27.0",         # Swift's name for UIBarButtonItem.paddingRemoved
    "paddingRemoved": "27.0",
    "preferredPlacement": "27.0",       # UISheetPresentationController, UITabBarController.Sidebar (SHARED below)
    "UISheetPresentationController.Placement": "27.0",
}

# A curated name an older API shares: a line using the older one is flagged all the same, and waived with why.
SHARED = {"preferredPlacement": ("18.0", "UITab.preferredPlacement (iOS 18)")}

# Foldsmith's reference types and their public API (Sources/Patterns/*.swift). Each file sits whole inside
# #if compiler(>=6.4) and reads reserved regions, so it needs Swift 6.4 and the iOS 27.1 SDK.
FOLDSMITH = ["FoldAlignedSplit", "FoldAlignedTiledSplit", "Arrangement", "ArrangementStyle", "EvenGrid",
             "ReflowingColumns", "readsBookFold", "foldAwareSheetPlacement", "duoBookFoldIsActive"]
FOLDSMITH_VERSION = "27.1"
GUARD = (6, 4)   # the first compiler that Xcode 27 ships


def symbol_pattern(name):
    """A use of the name in code: a whole identifier (a member after a dot too); a dotted name with any spacing around
    its dots. Foldsmith's Arrangement only as a type in use (Arrangement(…), Arrangement<…>, Arrangement { … }), so
    an app's own word arrangement, or UIKit's UIArrangementViewController.Arrangement, is not it."""
    if name == "Arrangement":
        return re.compile(r"(?<![\w$.])Arrangement(?=\s*[<({])")
    body = r"\s*\.\s*".join(re.escape(part) for part in name.split("."))
    return re.compile(r"(?<![\w$])" + body + r"(?![\w])")


SYMBOLS = [(name, version, False, symbol_pattern(name)) for name, version in SDK_SYMBOLS.items()]
SYMBOLS += [(name, FOLDSMITH_VERSION, True, symbol_pattern(name)) for name in FOLDSMITH]
AVAILABILITY = re.compile(r"([#@])(un)?available\s*\(([^()]*)\)")
PLATFORM_VERSION = re.compile(
    r"\b(iOS|iOSApplicationExtension|anyAppleOS)\s*(?:,\s*introduced\s*:\s*)?(\d+(?:\.\d+)*)")
WAIVER = re.compile(r"//\s*sdkguard:\s*ok\b(.*)$")
DIRECTIVE = re.compile(r"^\s*#(if|elseif|else|endif)\b(.*)$")
# The keyword before a name that declares it: the declaration is not a use.
DECLARING = re.compile(r"\b(?:struct|class|enum|actor|protocol|typealias|func|var|let|case)\s+$")
# What the declaration pass reads, in order: braces, and a keyword with the name it declares (class func: a modifier),
# and an init (not a call: self.init, super.init), whose parameters it reads.
MODIFIERS = r"(?:func|var|let|subscript|init|deinit|static|final|override|private|public|internal|open|fileprivate|" \
            r"convenience|required|class|mutating|nonmutating|lazy|weak|unowned|dynamic|indirect)"
DECLARATION = re.compile(r"[{}]|\b(struct|class|enum|actor|protocol|typealias|func|var|let|extension|case)\b"
                         rf"(?:\s+(?!{MODIFIERS}\b)([A-Za-z_]\w*))?|(?<![.\w])(init)\b[?!]?")
PRIVATE = re.compile(r"\b(?:file)?private\b(?!\s*\()")   # private(set) is a setter's, not the name's
# A member, not a bare name or self's: after a dot that does not follow self.
RECEIVED = re.compile(r"\.\s*$")
SELF = re.compile(r"(?<![\w$.])self\s*[?!]?\s*\.\s*$")   # self.name, self?.name in a [weak self] closure
# `if let x {`, `if let x,`, `guard let x else`: the shorthand binds x from the x outside, a use of that one. CLAUSE:
# the same on a line that continues an if, guard or while condition (`if let a = b,` then `let x {`).
SHORTHAND = re.compile(r"\b(?:if|guard|while)\b[^{]*\b(?:let|var)\s+$")
SHORTHAND_END = re.compile(r"\s*(?:\{|,|else\b)")
CLAUSE = re.compile(r"(?:^|,)\s*(?:let|var)\s+$")
# An argument, parameter, associated value or tuple label (`f(isFolded: false)`, `func f(isFolded: Bool)`,
# `case fold(isFolded: Bool)`, `isFolded folded: Bool`, `} detail: {`): a name, not a use of one. It sits after (, a
# comma or }, or starts a line (a call or parameter list split over lines), and a colon follows it directly (or after
# spaces, not at a line's start: `? x` ending the line above leaves `x : y`, a ternary's), or after an internal name.
LABEL_SLOT = re.compile(r"(?:^|[(,}])\s*$")
LABEL_AFTER = re.compile(r":(?!:)|\s+[A-Za-z_]\w*\s*:(?!:)")
SPACED_COLON = re.compile(r"\s+:(?!:)")


def vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v))


def vshow(v):
    """26 → 26.0, 27.1.0 stays as written."""
    return v if "." in v else v + ".0"


# --- Swift source: code, comments and string literals told apart

def lex(text):
    """(code, comments): the text with everything but code blanked, and with everything but comments blanked. Newlines
    stay, so lines keep their numbers. Nested block comments, multi-line and raw strings are read as Swift reads them;
    a string interpolation is code."""
    n = len(text)
    code = list(text)
    comments = ["\n" if ch == "\n" else " " for ch in text]

    def blank(a, b):
        for k in range(a, min(b, n)):
            if code[k] != "\n":
                code[k] = " "

    def comment(a, b):
        blank(a, b)
        for k in range(a, min(b, n)):
            comments[k] = text[k]

    stack = [["code", -1]]   # an interpolation's frame counts its open parentheses
    i = 0
    while i < n:
        top = stack[-1]
        ch = text[i]
        if top[0] == "code":
            if text.startswith("//", i):
                j = text.find("\n", i)
                j = n if j < 0 else j
                comment(i, j)
                i = j
                continue
            if text.startswith("/*", i):
                stack.append(["block", 1])
                comment(i, i + 2)
                i += 2
                continue
            if ch in "#\"":
                h = 0
                while i + h < n and text[i + h] == "#":
                    h += 1
                if text.startswith('"""', i + h):
                    stack.append(["string", True, h])
                    blank(i, i + h + 3)
                    i += h + 3
                    continue
                if i + h < n and text[i + h] == '"':
                    stack.append(["string", False, h])
                    blank(i, i + h + 1)
                    i += h + 1
                    continue
                i += max(h, 1)   # #if, #available, #selector: code
                continue
            if top[1] >= 0:
                if ch == "(":
                    top[1] += 1
                elif ch == ")":
                    top[1] -= 1
                    if top[1] == 0:
                        stack.pop()
                        blank(i, i + 1)
            i += 1
            continue
        if top[0] == "block":
            if text.startswith("/*", i):
                top[1] += 1
                comment(i, i + 2)
                i += 2
            elif text.startswith("*/", i):
                top[1] -= 1
                comment(i, i + 2)
                i += 2
                if top[1] == 0:
                    stack.pop()
            else:
                comment(i, i + 1)
                i += 1
            continue
        _, multi, h = top
        if ch == "\\" and text.startswith("#" * h, i + 1):
            k = i + 1 + h
            if k < n and text[k] == "(":
                blank(i, k + 1)
                stack.append(["code", 1])
            else:
                blank(i, k + 1)
            i = k + 1
            continue
        close = ('"""' if multi else '"') + "#" * h
        if text.startswith(close, i):
            blank(i, i + len(close))
            stack.pop()
            i += len(close)
            continue
        if ch == "\n" and not multi:
            stack.pop()   # an unterminated literal ends with its line
            i += 1
            continue
        blank(i, i + 1)
        i += 1
    return "".join(code), "".join(comments)


# --- #if conditions: can a compiler older than 6.4 take this branch?

WORD = re.compile(r"\s*(?:(&&|\|\|)|(!)|(\()|(\))|([A-Za-z_]\w*)\s*(\((?:[^()]|\([^()]*\))*\))?)")


def parse_condition(text):
    """A compilation condition as a tree: ("and"|"or", a, b), ("not", a), ("atom", name, args); None when unreadable."""
    words, pos, text = [], 0, text.strip()
    while pos < len(text):
        m = WORD.match(text, pos)
        if not m or m.end() == pos:
            if text[pos:].strip():
                return None
            break
        pos = m.end()
        if m.group(1):
            words.append(m.group(1))
        elif m.group(2):
            words.append("!")
        elif m.group(3):
            words.append("(")
        elif m.group(4):
            words.append(")")
        elif m.group(5):
            words.append(("atom", m.group(5), (m.group(6) or "")[1:-1].strip()))
    at = [0]

    def peek():
        return words[at[0]] if at[0] < len(words) else None

    def take():
        at[0] += 1
        return words[at[0] - 1]

    def either():
        left = both()
        while peek() == "||":
            take()
            left = ("or", left, both())
        return left

    def both():
        left = negated()
        while peek() == "&&":
            take()
            left = ("and", left, negated())
        return left

    def negated():
        if peek() == "!":
            take()
            return ("not", negated())
        return primary()

    def primary():
        word = peek()
        if word == "(":
            take()
            inner = either()
            if take() != ")":
                raise ValueError
            return inner
        if isinstance(word, tuple):
            return take()
        raise ValueError

    try:
        tree = either()
        return tree if at[0] == len(words) else None
    except (ValueError, IndexError):
        return None


def k_not(a):
    return None if a is None else not a


def k_and(*values):
    """Three-valued and: False wins, then unknown (None)."""
    return False if False in values else None if None in values else True


def before_guard(tree):
    """The condition's value for a compiler older than 6.4: True, False, or None when other conditions decide it."""
    if tree is None:
        return None
    kind = tree[0]
    if kind == "atom":
        _, name, args = tree
        if name in ("true", "false"):
            return name == "true"
        if name == "compiler":
            m = re.match(r"(>=|<)\s*(\d+(?:\.\d+)*)$", args)
            if m and vtuple(m.group(2)) >= GUARD:
                return m.group(1) == "<"
        return None
    if kind == "not":
        return k_not(before_guard(tree[1]))
    a, b = before_guard(tree[1]), before_guard(tree[2])
    if kind == "and":
        return k_and(a, b)
    return k_not(k_and(k_not(a), k_not(b)))


def guarded_lines(code):
    """Per line (1-based, index 0 unused): whether a compiler older than 6.4 skips it; and which lines are directives.
    A branch is skipped when its own condition, with every earlier branch of its #if failing, is false there."""
    guarded, directive = [False], [False]
    frames = []   # per #if: the values of its branches so far, and whether the current one is skipped
    for line in code.split("\n"):
        m = DIRECTIVE.match(line)
        if m:
            word, rest = m.group(1), m.group(2)
            if word == "if":
                value = before_guard(parse_condition(rest))
                frames.append({"earlier": [value], "skipped": value is False})
            elif word in ("elseif", "else") and frames:
                frame = frames[-1]
                none_before = k_and(*[k_not(v) for v in frame["earlier"]])
                own = before_guard(parse_condition(rest)) if word == "elseif" else True
                frame["earlier"].append(own)
                frame["skipped"] = k_and(none_before, own) is False
            elif word == "endif" and frames:
                frames.pop()
            directive.append(True)
        else:
            directive.append(False)
        guarded.append(any(f["skipped"] for f in frames))
    return guarded, directive


def name_pattern(name):
    return re.compile(r"(?<![\w$])" + re.escape(name) + r"(?![\w])")


def labelled(before, after):
    """Whether a name with this code before and after it on its line is a label (LABEL_SLOT), not a use."""
    if not LABEL_SLOT.search(before):
        return False
    return bool(LABEL_AFTER.match(after) or (before.strip() and SPACED_COLON.match(after)))


def used(pattern, code_line, own=frozenset(), need=None, partial=(), condition=False, labels=False):
    """Whether the pattern names something on the line other than the name a declaration there gives (the shorthand
    `if let x {` reads the x outside: a use, on a line that continues the condition too when condition is true). own:
    the kinds of declaration outside the guard that the line sits in the reach of, for this name: member (a type's own
    member: a bare or self. use is it), local (a local or a parameter: a bare use is it; self.name never is), reach
    (inside the body of the type whose member is guarded, beside an extension of another type that declares the name:
    another receiver's .name may be the extension's), none (outside that body: every use may be the extension's),
    scoped (in the block of a local declared inside the guard: only a bare use is that local). partial: [(column,
    kind)], kinds that hold from that column on (a closure's parameters, after its {). need: what must come right
    before the name (an enum's name and a dot, for its case in another file). labels: a label is not a use (labelled());
    for a name the branch declares, not for an SDK symbol, whose call may be the label's."""
    for m in pattern.finditer(code_line):
        before, after = code_line[:m.start()], code_line[m.end():]
        shorthand = SHORTHAND_END.match(after) and (SHORTHAND.search(before)
                                                    or (condition and CLAUSE.search(before)))
        if DECLARING.search(before) and not shorthand:
            continue
        if labels and labelled(before, after):
            continue
        if need is not None and not need.search(before):
            continue
        here = set(own) | {kind for column, kind in partial if m.start() >= column}
        received, through_self = bool(RECEIVED.search(before)), bool(SELF.search(before))
        if ("none" in here or (not received and here & {"member", "local"}) or (through_self and "member" in here)
                or (received and not through_self and "reach" in here) or (received and "scoped" in here)):
            continue
        return True
    return False


def uses(code_line, symbols=None, app=None, own=None, listed=(), partial=None, condition=False):
    """[(label, version, kind)] on one line of code, availability checks aside: kind "foldsmith" or "sdk" for the
    symbols (SYMBOLS less the Foldsmith names the app declares itself), "app" for a name the branch declares only
    inside a compile-time guard (app: name → (its pattern, where it is declared, what must come before it or None);
    the version is that place). own: name → the kinds of declaration outside the guard whose reach the line is in,
    partial: name → [(column, kind)] for those that start on the line (used()). listed: the later names of a list this
    line declares (case a, b), not uses. condition: the line continues an if, guard or while condition."""
    found = []
    for name, version, foldsmith, pattern in SYMBOLS if symbols is None else symbols:
        if used(pattern, code_line):
            found.append((f"{name} (a Foldsmith reference type)" if foldsmith else name, version,
                          "foldsmith" if foldsmith else "sdk"))
    for name, (pattern, where, need) in (app or {}).items():
        if name not in listed and used(pattern, code_line, (own or {}).get(name, frozenset()), need,
                                       (partial or {}).get(name, ()), condition, labels=True):
            found.append((name, where, "app"))
    return found


def line_starts(code):
    """Each line's offset in the code, so an offset's line is found by bisection."""
    return [0] + [m.end() for m in re.finditer("\n", code)]


def checks(code, added):
    """line → [(label, version, "check")]: each availability check naming iOS 27 or later, on the line it starts, when
    any line it spans is added (a formatter may split one: `if #available(` and `iOS 27.1, *) {`)."""
    starts, out = line_starts(code), {}
    for m in AVAILABILITY.finditer(code):
        first, last = bisect.bisect_right(starts, m.start()), bisect.bisect_right(starts, m.end() - 1)
        if not any(n in added for n in range(first, last + 1)):
            continue
        for platform, version in PLATFORM_VERSION.findall(m.group(3)):
            if vtuple(version) >= (27,):
                label = f"{m.group(1)}{m.group(2) or ''}available({platform} {version})"
                out.setdefault(first, []).append((label, vshow(version), "check"))
                break
    return out


def scan_source(text, added, symbols=None, app=None, shadows=None, listed=(), confined=None, scoped=None):
    """(hits, waived) for the added line numbers that use an iOS 27 API: hits [(line, uses, guarded)], waived [(line,
    uses, why)], each waived by `// sdkguard: ok <why>` on the line itself or on the line above when that line holds
    nothing but the comment (a waiver after the code above it is that line's, not this one's). shadows: app name →
    [(first, last, kind[, column])], the lines where the file declares that name outside a guard itself, kind member (a
    type's own) or local (a local, a parameter), from that column of the first line when given (a closure's
    parameters). listed: {(line, name)} for the later names of a list. confined: app name → [(first, last)], the
    bodies of the types whose guarded member it is, where an extension of another type declares it outside the guard
    (reach inside them, none outside). scoped: app name → [(first, last, where)], the blocks of the locals the file
    declares only inside the guard (a bare use inside one is that local, declared where; nothing outside them is)."""
    code, comments = lex(text)
    guarded, directive = guarded_lines(code)
    code_lines, comment_lines = code.split("\n"), comments.split("\n")
    starts = line_starts(code)
    opened = checks(code, added)

    def waiver(number):
        for k in (number, number - 1):
            if 1 <= k <= len(comment_lines) and (k == number or not code_lines[k - 1].strip()):
                m = WAIVER.search(comment_lines[k - 1])
                if m and m.group(1).strip():
                    return m.group(1).strip()
        return None

    hits, waived = [], []
    for number in sorted(set(added) | set(opened)):
        if number < 1 or number > len(code_lines) or directive[number]:
            continue
        own, partial, names = {}, {}, app
        for name, spans in (shadows or {}).items():
            for a, b, kind, *column in spans:
                if not a <= number <= b:
                    continue
                if column and column[0] and a == number:
                    partial.setdefault(name, []).append((column[0], kind))
                else:
                    own.setdefault(name, set()).add(kind)
        for name, spans in (confined or {}).items():
            own.setdefault(name, set()).add("reach" if any(a <= number <= b for a, b in spans) else "none")
        for name, spans in (scoped or {}).items():
            where = next((at for a, b, at in spans if a <= number <= b), None)
            own.setdefault(name, set()).add("scoped" if where else "none")
            if where and app and name in app:
                names = dict(names) if names is app else names
                names[name] = (app[name][0], where, None)
        here = {name for line, name in listed if line == number}
        found = opened.get(number, []) + (uses(code_lines[number - 1], symbols, names, own, here, partial,
                                               bool(names) and in_condition(code, starts[number - 1]))
                                          if number in added else [])
        if not found:
            continue
        why = waiver(number)
        if why is not None:
            waived.append((number, found, why))
        else:
            hits.append((number, found, guarded[number]))
    return hits, waived


# One name a Swift file declares: name, line, guarded (a compiler older than 6.4 skips its line), scope (top,
# extension: a member of one, member: of a type, local: a let, var or func in a body, an if, while, for or catch
# binding, a parameter of a function or a closure), private (private or fileprivate, or an enum case: seen from its own
# file only), type_guarded (a member: whether its type's line is skipped too), frame (the type's or block's braces, an
# id), first and last, the lines it is seen from (a member: its type's body; a let or var local: from the line after it
# to the end of its block; a local func: from its line; a parameter or a binding: the block it opens; None at the top
# level and in an extension), owner (a member: its type's name; an extension's member: the extended type's; a local:
# the type or extension its block sits in, or None), listed (a later name of a list: case a, b; var a = 0, b = 0; its
# line declares it), keyword (case, var, func, …; parameter for a parameter or a binding), and column (a closure's
# parameter: it is seen from that column of its first line, after the {; else 0, the whole line). A property-wrapped
# var (@State var x) also declares $x and _x, as entries of their own.
Declared = collections.namedtuple("Declared", "name line guarded scope private type_guarded frame first last owner "
                                  "listed keyword column", defaults=(None, False, None, 0))
TYPES = ("struct", "class", "enum", "actor", "protocol")
TOP_LEVEL = "<top level>"   # the owner of a top-level declaration: no type's name has < in it
EXTENDED = re.compile(r"(?:\s*\.\s*([A-Za-z_]\w*))*")   # extension Outer.Inner: Inner
LIST_NAME = re.compile(r"\s*([A-Za-z_]\w*)")
# A closure's header, right after its {: attributes, a capture list, then its parameters, (…) or a, b, then in.
CLOSURE = re.compile(r"\s*(?:@\w+(?:\([^()]*\))?\s*)*(?:\[[^\]]*\]\s*)?(?:\(([^)]*)\)|([A-Za-z_]\w*(?:\s*,\s*"
                     r"[A-Za-z_]\w*)*))\s*(?:async\b\s*)?(?:throws\b\s*(?:\([^()]*\)\s*)?)?(?:->[^{}]*?)?\s*\bin\b")
# A property wrapper's attribute (@State, @Binding, @Published, @AppStorage("k"), @Environment(\.x), a custom one):
# its var also has $x and _x. Not an attribute that wraps nothing (@MainActor and other actors, @Entry, @IBOutlet, …).
WRAPPER = re.compile(r"@(?!(?:Entry|IBOutlet|IBInspectable|NSManaged|Sendable|ObservationIgnored|ObservationTracked|"
                     r"Attribute|Relationship|Transient|GKInspectable)\b)[A-Z]\w*(?<!Actor)\b")
ATTRIBUTES_ONLY = re.compile(r"^\s*(?:@[\w.]+(?:\((?:[^()]|\([^()]*\))*\))?\s*)+$")


def opened_inside(code, start, at):
    """Whether offset at sits inside a parenthesis opened after start: a closure in a default value or in a
    condition's call, not the body that follows."""
    span = code[start:at]
    return span.count("(") > span.count(")")


def statement_head(code, at):
    """The statement offset at sits in, from its start to at: back to the last brace or ;, and read back over lines
    that end in a comma, && or || (a condition split over lines)."""
    brace = max(code.rfind("{", 0, at), code.rfind("}", 0, at))
    start = max(brace, code.rfind(";", brace + 1, at)) + 1
    lines = code[start:at].split("\n")
    k = len(lines) - 1
    while k > 0 and re.search(r"(?:,|&&|\|\|)\s*$", lines[k - 1]):
        k -= 1
    return "\n".join(lines[k:])


def binds_block(code, at):
    """Whether the let or var at offset at binds a name for the block an if or while condition (else if too), a for
    loop or a catch opens: the statement it sits in starts with if, while, for or catch."""
    return bool(re.match(r"\s*(?:else\s+)?(?:if|while|for|catch)\b", statement_head(code, at)))


def in_condition(code, at):
    """Whether offset at (a line's start) continues an if, guard or while condition from the lines above (`if let a =
    b,` then `let x {`)."""
    head = statement_head(code, at)
    return "\n" in head and bool(re.match(r"\s*(?:else\s+)?(?:if|guard|while)\b", head))


def closure_parameters(code, at):
    """[(name, offset)]: the parameters a closure's header names right after its { (at just after it): `{ [weak self]
    isFolded in`, `{ _, new in`, `{ (a: Int, b) -> Bool in`; [] when there is no header (`{ [weak self] in`, `{ $0 }`, a
    block that is not a closure)."""
    m = CLOSURE.match(code, at)
    if not m:
        return []
    group = 1 if m.group(1) is not None else 2
    names, offset = [], m.start(group)
    for item in m.group(group).split(","):
        word = item.split(":", 1)[0].split()
        if word and re.fullmatch(r"[A-Za-z_]\w*", word[-1]) and word[-1] != "_":
            names.append((word[-1], offset + item.rfind(word[-1], 0, len(item.split(":", 1)[0]))))
        offset += len(item) + 1
    return names


def wrapped(code, code_lines, line, at):
    """Whether the var whose keyword is at offset at (on line) carries a property wrapper's attribute: before it on its
    line, after the last ; or brace there, or on the lines just above that hold only attributes."""
    head = re.split(r"[;{}]", code[code.rfind("\n", 0, at) + 1:at])[-1]
    if WRAPPER.search(head):
        return True
    k = line - 1
    while k >= 1 and ATTRIBUTES_ONLY.match(code_lines[k - 1]):
        if WRAPPER.search(code_lines[k - 1]):
            return True
        k -= 1
    return False


def listed_names(code, at):
    """The later names of a declaration list, from offset at just after its first name (case a, b(Int), c = 2; var a =
    0, b: [String: Int] = [:]): [(name, offset)], the first word after each comma outside brackets, up to the
    statement's end (a ; a closing bracket it did not open, or a line end not after a comma). A type's <…> counts as
    brackets, a value's < does not."""
    names, depth, typed, last, i, n = [], 0, False, "", at, len(code)
    while i < n:
        ch = code[i]
        if ch in "([{" or (ch == "<" and typed):
            depth += 1
        elif ch in ")]}" or (ch == ">" and typed and depth and code[i - 1] != "-"):
            if not depth:
                break
            depth -= 1
        elif not depth:
            if ch == ";" or (ch == "\n" and last != ","):
                break
            if ch == ":":
                typed = True
            elif ch == "=":
                typed = False
            elif ch == ",":
                typed = False
                m = LIST_NAME.match(code, i + 1)
                if m:
                    names.append((m.group(1), m.start(1)))
        if not ch.isspace():
            last = ch
        i += 1
    return names


def parameters(code, at):
    """The parameter names of the function whose name (or init) ends at offset at: from its (…), after any <…>; []
    when there is none."""
    m = re.compile(r"\s*(<(?:[^<>]|<[^<>]*>)*>)?\s*\(").match(code, at)
    if not m:
        return []
    depth, i = 1, m.end()
    while i < len(code) and depth:
        depth += {"(": 1, ")": -1}.get(code[i], 0)
        i += 1
    names, part, level = [], "", 0
    for ch in code[m.end():i - 1] + ",":
        if ch in "([<{":
            level += 1
        elif ch in ")]>}" and not (ch == ">" and part.endswith("-")):   # a function type's -> closes nothing
            level -= 1
        if ch == "," and level == 0:
            head = part.split(":", 1)[0].split()
            if len(part.split(":", 1)) == 2 and head and re.fullmatch(r"[A-Za-z_]\w*", head[-1]) and head[-1] != "_":
                names.append(head[-1])
            part = ""
        else:
            part += ch
    return names


def declarations(text, extensions=None):
    """[Declared]: the names a Swift file declares (types, functions, variables, typealiases, enum cases, every name
    of a list) at its top level, as members of its extensions (static lets too: a Notification.Name) and of its types,
    and as locals (a let, var or func in a body, an if, while, for or catch binding, a function's, init's or closure's
    parameter), each with where it sits and whether a compiler older than 6.4 skips its line. Scope is read from
    braces. extensions, when given, gets (extended type, first line, last line) for each extension's body."""
    code, _ = lex(text)
    guarded, _ = guarded_lines(code)
    starts = line_starts(code)
    code_lines = code.split("\n")

    def line_of(offset):
        return bisect.bisect_right(starts, offset)

    def skipped(line):
        return guarded[line] if line < len(guarded) else False

    def enclosing():
        """The type or extension the innermost block sits in: its (extended) type's name, or None."""
        return next((f["owner"] for f in reversed(stack) if f["kind"] in ("type", "extension")), None)

    def closure(brace, line):
        """Its header's parameters, locals of the block the { at offset brace opens, seen from just after it."""
        for p, at in closure_parameters(code, brace + 1):
            out.append(Declared(p, line_of(at), skipped(line_of(at)), "local", False, None, stack[-1]["id"], line,
                                None, enclosing(), False, "parameter", brace - starts[line - 1] + 1))
            stack[-1]["open"].append(len(out) - 1)

    # pending: (kind, skipped, owner) for the next {; params: [(name, first line or None)] that {'s block declares,
    # since the offset they were read from; binding: they are an if, while, for or catch statement's.
    out, stack, ids = [], [], 0
    pending, params, since, binding = None, [], None, False
    for m in DECLARATION.finditer(code):
        token, keyword, name, init = m.group(0), m.group(1), m.group(2), m.group(3)
        line = line_of(m.start())
        if token == "{":
            if params and since is not None and opened_inside(code, since, m.start()):
                # A closure inside the parentheses: its block is not the one the names belong to.
                stack.append({"kind": "other", "guarded": skipped(line), "id": ids, "start": line, "open": [],
                              "owner": None, "resume": (pending, params, since, binding)})
                ids += 1
                pending, params, since, binding = None, [], None, False
                closure(m.start(), line)
                continue
            kind, was, owner = pending or ("other", skipped(line), None)
            stack.append({"kind": kind, "guarded": was, "id": ids, "start": line, "open": [], "owner": owner})
            ids += 1
            for p, first in params:
                out.append(Declared(p, line, skipped(line), "local", False, None, stack[-1]["id"],
                                    max(first or line, line), None, enclosing(), keyword="parameter"))
                stack[-1]["open"].append(len(out) - 1)
            if kind == "other" and since is None:   # no function, init or binding claims it: maybe a closure
                closure(m.start(), line)
            pending, params, since, binding = None, [], None, False
            continue
        if token == "}":
            frame = stack.pop() if stack else None
            for i in (frame or {}).get("open", []):
                out[i] = out[i]._replace(last=line)
            if frame and frame["kind"] == "extension" and extensions is not None:
                extensions.append((frame["owner"], frame["start"], line))
            pending, params, since, binding = (frame or {}).get("resume", (None, [], None, False))
            continue
        if keyword == "extension":
            dotted = EXTENDED.match(code, m.end())
            pending = ("extension", skipped(line), dotted.group(1) or name)
            params, since, binding = [], None, False
            continue
        top = stack[-1] if stack else None
        scope = ("top" if top is None else "extension" if top["kind"] == "extension"
                 else "member" if top["kind"] == "type" else "local")
        if keyword == "case" and scope != "member":
            continue   # a switch's case, not an enum's
        if init or keyword == "func":
            params, since, binding = [(p, None) for p in parameters(code, m.end())], m.end(), False
        if init or not name:
            if init:
                pending = ("other", skipped(line), None)
            continue
        if keyword in ("let", "var") and scope in ("local", "top") and (binding or binds_block(code, m.start())):
            # if let x = …, while var x = …, catch let x: x is seen in the block the statement opens, from the next
            # line.
            if not binding:
                params, since, binding = [], m.start(), True
            params.append((name, line + 1))
            pending = ("other", skipped(line), None)
            continue
        if keyword != "func":
            params, since, binding = [], None, False
        if keyword != "case":
            kind = "type" if keyword in TYPES else "other"
            pending = (kind, skipped(line), name if kind == "type" else None)
        # A private member, and an enum case (a generic name: .trailing), are seen from their own file only. An
        # override's name is its superclass's, there on every Xcode: as if declared outside the guard, in a type's
        # body or in an extension.
        head = code[starts[line - 1]:m.start()]
        private = keyword == "case" or bool(PRIVATE.search(head))
        is_skipped = skipped(line) and not (scope in ("member", "extension") and re.search(r"\boverride\b", head))
        first = {"member": top and top["start"], "local": line + 1 if keyword in ("let", "var") else line}.get(scope)
        owner = top["owner"] if scope in ("member", "extension") else enclosing() if scope == "local" else None
        d = Declared(name, line, is_skipped, scope, private, top["guarded"] if scope == "member" else None,
                     top["id"] if top else None, first, None, owner, False, keyword)
        out.append(d)
        if scope in ("member", "local"):
            top["open"].append(len(out) - 1)
        if keyword == "var" and wrapped(code, code_lines, line, m.start()):
            for projected in ("$" + name, "_" + name):   # @State var x: $x (its projected value) and _x (its storage)
                out.append(d._replace(name=projected))
                if scope in ("member", "local"):
                    top["open"].append(len(out) - 1)
        if keyword in ("case", "let", "var") and scope in ("member", "extension", "top"):
            for extra, at in listed_names(code, m.end()):
                out.append(d._replace(name=extra, line=line_of(at), guarded=skipped(line_of(at)), listed=True))
                if scope == "member":
                    top["open"].append(len(out) - 1)
    return [d._replace(last=len(guarded) - 1) if d.scope in ("member", "local") and d.last is None else d
            for d in out]


# --- git, read-only

def git(app, *args, check=False):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", LC_ALL="C")   # no index refresh written behind a read
    r = subprocess.run(["git", "-C", str(app), *args], capture_output=True, env=env)
    if check and r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="replace").strip() or f"git {' '.join(args)} failed")
    return r


def out(r):
    return r.stdout.decode(errors="replace").strip()


def is_repo(app):
    return out(git(app, "rev-parse", "--is-inside-work-tree")) == "true"


def commit(app, rev):
    r = git(app, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    return out(r) if r.returncode == 0 else None


def resolve_base(app, given):
    """(how it is named, commit), or exit 2."""
    if given:
        sha = commit(app, given)
        if not sha:
            fail(f"--base {given}: no such commit in {app}")
        return given, sha
    sha = commit(app, "duo-baseline")
    if sha:
        return "duo-baseline", sha
    skipped = ""
    for ref in ("origin/HEAD", "main", "master"):
        if not commit(app, ref):
            continue
        target = out(git(app, "symbolic-ref", "-q", "refs/remotes/origin/HEAD")) if ref == "origin/HEAD" else ""
        if target.endswith("/duo-migration"):
            skipped = f" (origin/HEAD is {target[len('refs/remotes/'):]}, a run's own branch)"
            continue   # a clone of a run's folder: its default branch is that run's migration
        r = git(app, "merge-base", "HEAD", ref)
        if r.returncode == 0 and out(r):
            return f"the merge base with {ref}", out(r)
    hint = ""
    remote = out(git(app, "for-each-ref", "--format=%(refname:short)", "refs/remotes/*/duo-baseline")).split("\n")[0]
    if remote:
        hint = f"; {remote} exists: --base {remote} if it is this run's baseline"
    fail(f"no base to compare with: no duo-baseline, and no default branch (origin/HEAD, main, master) to take a merge "
         f"base with{skipped}. Pass --base <rev>, the commit the migration started from{hint}")


def added_lines(app, base, old, new):
    """The line numbers of new that are added since base (renames followed)."""
    paths = [f":(literal){p}" for p in dict.fromkeys([old, new])]
    r = git(app, "diff", "-U0", "-M", "--relative", "--no-color", "--no-ext-diff", "--no-textconv", base, "--", *paths,
            check=True)
    numbers = set()
    for m in re.finditer(rb"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", r.stdout, re.M):
        start, count = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
        numbers.update(range(start, start + count))
    return numbers


def changed_swift(app, base):
    """[(old path, new path)] of Swift files changed since base, untracked ones (old None) last; .duo/ left out."""
    r = git(app, "diff", "--name-status", "-z", "-M", "--relative", "--no-ext-diff", base, "--", ".", ":(exclude).duo",
            check=True)
    fields = r.stdout.decode(errors="surrogateescape").split("\0")
    files, i = [], 0
    while i < len(fields) and fields[i]:
        status = fields[i]
        if status[:1] in "RC":
            old, new, i = fields[i + 1], fields[i + 2], i + 3
        else:
            old = new = fields[i + 1]
            i += 2
        if status[:1] != "D" and new.endswith(".swift"):
            files.append((old, new))
    r = git(app, "ls-files", "--others", "--exclude-standard", "-z", "--", "*.swift", ":(exclude).duo", check=True)
    files += [(None, p) for p in r.stdout.decode(errors="surrogateescape").split("\0") if p]
    return files


# --- The CI's Xcode

V = r"(\d+(?:\.\d+)*)"
Q = r"['\"]?"
CI_PATTERNS = [
    re.compile(rf"Xcode[_-]{V}[^\s/'\"]*\.app", re.I),
    re.compile(rf"\bxcode-version\s*:\s*{Q}{V}{Q}", re.I),
    re.compile(rf"\bxcode\s*:\s*{Q}{V}{Q}", re.I),
    re.compile(rf"\bxcodes\s+(?:select|install|use)\s+{Q}{V}{Q}", re.I),
    re.compile(rf"\bxcversion\s+select\s+{Q}{V}{Q}", re.I),
    re.compile(rf"\bosx_image\s*:\s*{Q}xcode{V}{Q}", re.I),
    # a stack or image named …xcode-26.6… (Bitrise, GitLab): only as such a value, not a cache key's spm-xcode-16
    re.compile(rf"\b(?:stack|image)\s*:\s*{Q}[\w.-]*?xcode-{V}[\w.-]*{Q}", re.I),
    re.compile(rf"\b(?:ensure_xcode_version|xcversion)\b.*?\bversion\s*:\s*['\"]{V}['\"]"),
]
SCHEME = re.compile(r"-scheme\s+['\"]?([\w.+-]+)")
LATEST = re.compile(r"\bxcode-version\s*:\s*['\"]?(latest(?:-stable)?)\b", re.I)
RUNNER = re.compile(r"\bruns-on\s*:\s*['\"]?(macos-[\w.-]+)", re.I)
BUILDS = re.compile(r"\b(?:xcodebuild|swift\s+(?:build|test)|fastlane)\b")
# NAME: 26.6 (YAML), NAME=26.6 and export NAME=26.6 (shell), NAME := 26.6, ?=, ::= (Makefile)
ASSIGNED = re.compile(rf"^\s*-?\s*(?:export\s+)?([A-Za-z_][\w-]*)\s*(?:::=|:=|\?=|=|:)\s*{Q}{V}{Q}\s*$")
FLOW_LIST = re.compile(r"^\s*-?\s*([A-Za-z_][\w-]*)\s*:\s*\[([^\]]*)\]")
BLOCK_KEY = re.compile(r"^(\s*)([A-Za-z_][\w-]*)\s*:\s*$")
BLOCK_ITEM = re.compile(rf"^(\s*)-\s*{Q}{V}{Q}\s*$")
CALLED = re.compile(r"(?:^|[\s;&|(])(?:bash\s+|sh\s+|zsh\s+|\./)?((?:[\w.-]+/)*[\w.-]+\.sh)\b")
MAKE = re.compile(r"(?:^|[\s;&|(])g?make(?:\s|$)")
LOCAL_ACTION = re.compile(r"\buses\s*:\s*['\"]?\./([^\s'\"@]+)")
# xcodes or xcversion with no version: it reads .xcode-version
FROM_FILE = re.compile(r"\b(?:xcodes|xcversion)\s+(?:select|install|use)\b(?!\s+(?:['\"]?\d|--latest))")
# A variable that holds the Xcode version (XCODE, XCODE_VERSION, xcode-version), not XCODE_TIMEOUT
XCODE_NAME = re.compile(r"(?i)^xcode$|xcode[_-]?version")
# A shell default: X="${X:-26.6}" or : "${X:=26.6}" (a fallback under what the workflow passes in), X=${1:-26.6} (the
# script's own value: it reads another variable)
DEFAULTED = re.compile(rf"^\s*(?:export\s+)?([A-Za-z_]\w*)={Q}\$\{{(\w+):?[-=]{Q}{V}{Q}\}}{Q}\s*$")
DEFAULT_SET = re.compile(rf"^\s*:\s*{Q}\$\{{([A-Za-z_]\w*):?={Q}{V}{Q}\}}{Q}\s*$")
# ${{ matrix.X }}, ${{ env.X }}, ${X}, ${X:-26.6}, ${X:=26.6}, $X (YAML and shell), $(X) (Makefile)
REFERENCE = re.compile(r"\$\{\{\s*(matrix|env)\.([A-Za-z_][\w-]*)\s*\}\}|\$\{([A-Za-z_]\w*)(?::?[-=]([^}]*))?\}"
                       r"|\$([A-Za-z_]\w*)|\$\(([A-Za-z_]\w*)\)")


def referred(m):
    """The variable a REFERENCE match names."""
    return m.group(2) or m.group(3) or m.group(5) or m.group(6)


def given_default(m):
    """The version a ${X:-26.6} or ${X:=26.6} match falls back to, or None."""
    value = (m.group(4) or "").strip().strip("'\"")
    return value if re.fullmatch(V, value) else None


def uncommented(line):
    """A CI file's line without its comment: from a # at the line's start or after a space, outside quotes (YAML,
    shell, Makefile and Ruby all read it so). A single quote opens one only where a quoted token can start (the
    line's start, after a space, :, =, (, [, { or a comma): the apostrophe of `app's` is a letter."""
    quote = None
    for i, ch in enumerate(line):
        if quote:
            quote = None if ch == quote else quote
        elif ch == '"' or (ch == "'" and (i == 0 or line[i - 1] in " \t:=([{,")):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1].isspace()):
            return line[:i]
    return line


def ci_files(root):
    found = []
    workflows = root / ".github/workflows"
    if workflows.is_dir():
        found += sorted(p for p in workflows.iterdir() if p.suffix in (".yml", ".yaml") and p.is_file())
    actions = root / ".github/actions"
    if actions.is_dir():
        found += sorted(p for p in actions.rglob("action.y*ml") if p.suffix in (".yml", ".yaml") and p.is_file())
    for rel in (".xcode-version", ".circleci/config.yml", "bitrise.yml", ".gitlab-ci.yml", ".travis.yml",
                "fastlane/Fastfile", "Makefile"):
        if (root / rel).is_file():
            found.append(root / rel)
    scripts = root / "ci_scripts"
    if scripts.is_dir():
        found += sorted(p for p in scripts.rglob("*") if p.is_file())
    return found


def defaults(line):
    """(name, version, fallback) for a shell default on the line, else None: fallback when it reads the same variable
    (X="${X:-26.6}", : "${X:=26.6}"), so a value the workflow passes in wins; not when it reads another
    (X=${1:-26.6})."""
    m = DEFAULTED.match(line)
    if m:
        return m.group(1), m.group(3), m.group(2) == m.group(1)
    m = DEFAULT_SET.match(line)
    return (m.group(1), m.group(2), True) if m else None


def values(lines, fallbacks=None):
    """name → [version]: what a file sets once (XCODE: "26.6", XCODE_VERSION=26.6, XCODE_VERSION ?= 26.6,
    XCODE_VERSION=${1:-26.6}) and every value of its lists (a matrix's xcode: ['26.4', '27.1'], a block of - "26.4"
    items, include: entries' - xcode: "26.4"). fallbacks, when given, gets the defaults a value passed in overrides
    (XCODE_VERSION="${XCODE_VERSION:-26.6}")."""
    out, key, indent = {}, None, -1
    for line in lines:
        m = BLOCK_ITEM.match(line)
        if key and m and len(m.group(1)) > indent:
            out.setdefault(key, []).append(m.group(2))
            continue
        key = None
        m = BLOCK_KEY.match(line)
        if m:
            key, indent = m.group(2), len(m.group(1))
            continue
        m = FLOW_LIST.match(line)
        if m:
            out.setdefault(m.group(1), []).extend(re.findall(rf"{Q}{V}{Q}", m.group(2)))
            continue
        m = ASSIGNED.match(line)
        if m:
            out.setdefault(m.group(1), []).append(m.group(2))
            continue
        given = defaults(line)
        if given:
            name, version, fallback = given
            if not fallback:
                out.setdefault(name, []).append(version)
            elif fallbacks is not None:
                fallbacks.setdefault(name, []).append(version)
    if fallbacks is not None:
        fallbacks.update({k: list(dict.fromkeys(v)) for k, v in fallbacks.items()})
    return {k: list(dict.fromkeys(v)) for k, v in out.items()}


def resolved_lines(line, known):
    """The line with each ${{ matrix.X }}, ${{ env.X }}, ${X}, $X or $(X) the file (or the workflow that runs it) sets
    put in, once per value (a matrix's every value), and a ${X:-26.6} whose X is not set put in as its default; []
    when it refers to none."""
    found = list(REFERENCE.finditer(line))
    names = [n for n in dict.fromkeys(referred(m) for m in found) if n in known]
    if not names and not any(referred(m) not in known and given_default(m) for m in found):
        return []
    out = [line]
    for name in names:
        out = [REFERENCE.sub(lambda m, n=name, v=v: v if referred(m) == n else m.group(0), text)
               for text in out for v in known[name]]
    return [REFERENCE.sub(lambda m: given_default(m) or m.group(0) if referred(m) not in known else m.group(0), text)
            for text in out]


def read_ci(roots, shown_from):
    """([(file:line, version, what)], [scheme], has ci_scripts/, [(file:line, what)] of the workflows that build on a
    runner's default Xcode or setup-xcode's latest) over the CI files of each root, once each. A workflow's parts are
    read with it, with the variables it sets: the .sh scripts it runs, the Makefile when it runs make, and the local
    actions it uses (uses: ./…); what they name and build is the workflow's."""
    versions, schemes, xcode_cloud, runners, listed, seen = [], [], False, [], set(), set()

    def add(entries):
        for entry in entries:
            if entry[:2] not in listed:
                listed.add(entry[:2])
                versions.append(entry)

    def scan(path, text, inherited=None):
        """(found, lines, the variables known) for one file; inherited: the variables of the workflow that runs it."""
        where, found = os.path.relpath(path, shown_from), []
        lines = [uncommented(line) for line in text.split("\n")]
        if path.name == ".xcode-version":
            for number, line in enumerate(lines, 1):
                m = re.match(r"\s*(\d+(?:\.\d+)*)", line)
                if m:
                    found.append((f"{where}:{number}", m.group(1), line.strip()))
                    break
            return found, lines, {}
        fallbacks = {}
        own = values(lines, fallbacks)
        known = {**fallbacks, **(inherited or {}), **own}
        for number, line in enumerate(lines, 1):
            on_line = {}
            for variant in [line] + resolved_lines(line, known):
                for pattern in CI_PATTERNS:
                    for m in pattern.finditer(variant):
                        what = m.group(0).strip()
                        if variant is not line:
                            what = f"{what}, from {REFERENCE.search(line).group(0)}"
                        on_line.setdefault(m.group(1), what)
            m = re.match(r"^\s*-?\s*([A-Za-z_][\w-]*)\s*:\s*\[", line)
            if m and "xcode" in m.group(1).lower():   # a matrix's own list of Xcodes, where it is
                for v in own.get(m.group(1), []):
                    on_line.setdefault(v, f"{m.group(1)}: {v}")
            m = ASSIGNED.match(line)
            if m and XCODE_NAME.search(m.group(1)):
                on_line.setdefault(m.group(2), line.strip())   # XCODE_VERSION: "26.6", where it is set
            given = defaults(line)
            if given and XCODE_NAME.search(given[0]) and given[1] in known.get(given[0], []):
                on_line.setdefault(given[1], line.strip())   # a default in effect: none passed in overrides it
            m = BLOCK_ITEM.match(line)
            if m:
                key = next((k for k in reversed(lines[:number - 1]) if BLOCK_KEY.match(k)), "")
                key = BLOCK_KEY.match(key).group(2) if key else ""
                if "xcode" in key.lower():
                    on_line.setdefault(m.group(2), f"{key}: - {m.group(2)}")
            for version, what in on_line.items():
                found.append((f"{where}:{number}", version, what))
            for m in SCHEME.finditer(line):
                if m.group(1) not in schemes:
                    schemes.append(m.group(1))
        return found, lines, known

    def read(path):
        try:
            return path.read_text(errors="replace")
        except OSError:
            return None

    for root in roots:
        xcode_cloud = xcode_cloud or (root / "ci_scripts").is_dir()
        pin = root / ".xcode-version"
        pinned = next(iter(scan(pin, read(pin) or "")[0]), None) if pin.is_file() else None
        for path in ci_files(root):
            real = path.resolve()
            if real in seen:
                continue
            seen.add(real)
            text = read(path)
            if text is None:
                continue
            found, lines, known = scan(path, text)
            workflow = path.parent.name == "workflows" and path.parent.parent.name == ".github"
            if not workflow:
                add(found)
                continue
            parts = [root / rel for rel in dict.fromkeys(m.group(1) for line in lines for m in CALLED.finditer(line))]
            if any(MAKE.search(line) for line in lines):
                parts.append(root / "Makefile")
            for rel in dict.fromkeys(m.group(1).rstrip("/") for line in lines for m in LOCAL_ACTION.finditer(line)):
                parts += [root / rel / "action.yml", root / rel / "action.yaml"]
            every = list(lines)
            for part in parts:
                body = read(part) if part.is_file() else None
                if body is not None:
                    more, part_lines, _ = scan(part, body, known)
                    found += more
                    every += part_lines
            add(found)
            if pinned and any(FROM_FILE.search(line) for line in every):
                found.append(pinned)   # xcodes select with no version reads .xcode-version
            if not found:
                where = os.path.relpath(path, shown_from)
                latest = next(((n, m) for n, line in enumerate(lines, 1) for m in [LATEST.search(line)] if m), None)
                runner = next(((n, m) for n, line in enumerate(lines, 1) for m in [RUNNER.search(line)] if m), None)
                if latest:
                    runners.append((f"{where}:{latest[0]}", f"setup-xcode's {latest[1].group(1)}"))
                elif runner and any(BUILDS.search(line) for line in every):
                    runners.append((f"{where}:{runner[0]}", f"runs-on: {runner[1].group(1)}"))
    return versions, schemes, xcode_cloud, runners


def installed_xcodes():
    apps = pathlib.Path(os.environ.get("SDKGUARD_APPLICATIONS", "/Applications"))
    found = []
    for app in sorted(apps.glob("Xcode*.app")):
        info = {}
        for name in ("version.plist", "Info.plist"):
            try:
                with open(app / "Contents" / name, "rb") as f:
                    info = plistlib.load(f)
                break
            except (OSError, plistlib.InvalidFileException, ValueError):
                continue
        version = info.get("CFBundleShortVersionString")
        if version:
            found.append((app, str(version), str(info.get("ProductBuildVersion") or "")))
    return found


def matches(ci_version, installed_version):
    """The CI's version names this Xcode: its numbers are the start of the installed one's (26.6 is 26.6.1 too)."""
    want, have = vtuple(ci_version), vtuple(installed_version)
    have = have + (0,) * (3 - len(have))
    return have[:len(want)] == want


def build_line(app, xcode, scheme):
    containers = sorted(app.glob("*.xcworkspace")) or sorted(app.glob("*.xcodeproj"))
    flag = ("-workspace" if containers[0].suffix == ".xcworkspace" else "-project") if containers else None
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", app.name).strip("-") or "app"
    parts = [f"DEVELOPER_DIR={shlex.quote(str(xcode / 'Contents/Developer'))}", "xcodebuild"]
    if flag:
        parts += [flag, shlex.quote(str(containers[0]))]
    parts += ["-scheme", shlex.quote(scheme) if scheme else "<scheme>", "-destination",
              "'generic/platform=iOS Simulator'", "-derivedDataPath", f"~/Library/Caches/duo-build/{name}-ci", "build"]
    return " ".join(parts)


def fail(message):
    print(f"sdkguard.py: {message}", file=sys.stderr)
    sys.exit(2)


# --- The verdict

def band(version):
    """below (no iOS 27 SDK), 27.0, or 27.1 (that or later)."""
    v = vtuple(version)
    if v < (27,):
        return "below"
    return "27.0" if v < (27, 1) else "27.1"


def ci_sentence(lowest, where, xcode_cloud, runners=()):
    """What the CI's Xcode means for the run, in one sentence (the preflight's note)."""
    if lowest is None:
        cloud = ("ci_scripts/ is Xcode Cloud, whose Xcode is set in App Store Connect, not here" if xcode_cloud
                 else "")
        if runners:
            at, what = runners[0]
            return (f"no Xcode version is named in the repository: {at} builds with the Xcode its runner image picks "
                    f"({what}), which the repository does not name, so check that image's Xcode before trusting a "
                    f"pass{'; ' + cloud if cloud else ''}; until then sdkguard's lines are notes")
        if xcode_cloud:
            return (f"no CI Xcode found in the repository: {cloud}; check it there, and until then sdkguard's lines "
                    "are notes")
        return "no CI Xcode found in the repository, so nothing says which Xcode builds it: sdkguard's lines are notes"
    at = f"Xcode {lowest} ({where})"
    kind = band(lowest)
    if kind == "below":
        return (f"CI builds with {at}, which has no iOS 27 SDK: every iOS 27 API and every Foldsmith reference type "
                "goes inside #if compiler(>=6.4) with the pre-Duo code in #else, and tools/sdkguard.py must pass")
    if kind == "27.0":
        return (f"CI builds with {at}: iOS 27.0 APIs build there and iOS 27.1 APIs do not, and Xcode 27.0 ships Swift "
                "6.4 like 27.1, so no supported compile-time check separates them: propose moving CI to Xcode 27.1 "
                "in .duo/PLAN.md")
    return f"CI builds with {at}, which has the iOS 27.1 SDK: the iOS 27 APIs build there"


def lines(n):
    return f"{n} line{'' if n == 1 else 's'}"


def said(entries, note=False):
    """What a flagged line uses, in a line's words: the symbols and their iOS version; each name declared only inside
    the guard and where; an availability check alone opens iOS 27 code."""
    symbols = [e for e in entries if e[2] in ("sdk", "foldsmith")]
    apps = [e for e in entries if e[2] == "app"]
    parts = []
    if symbols:
        names = list(dict.fromkeys(label for label, _, _ in symbols))
        version = max((v for _, v, _ in symbols), key=vtuple)
        parts.append(f"{', '.join(names)} {'are' if len(names) > 1 else 'is'} iOS {version}")
    for name, where, _ in apps:
        parts.append(f"{name} (declared only inside #if compiler(>=6.4), at {where})" if note
                     else f"{name} is declared only inside #if compiler(>=6.4) at {where}")
    if not parts:
        parts.append(f"{entries[0][0]} opens iOS 27 code")
    return "; ".join(parts)


def compiles_not(entries):
    """Whether the line itself fails on an Xcode without the iOS 27 SDK (a symbol, a name declared only inside the
    guard), rather than only opening iOS 27 code (an availability check, which compiles anywhere)."""
    return any(e[2] != "check" for e in entries)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sdkguard.py", description="Does the migration build with the CI's Xcode?")
    parser.add_argument("app", nargs="?", default=".", help="the app folder (default: the current one)")
    parser.add_argument("--base", help="the commit the migration started from")
    parser.add_argument("--scheme", help="the scheme for the build line")
    parser.add_argument("--ci-only", action="store_true", help="the CI's Xcode and what it means, nothing else")
    args = parser.parse_args(argv)
    app = pathlib.Path(args.app).expanduser()
    if not app.is_dir():
        fail(f"no folder {args.app}")
    app = app.resolve()
    repo = is_repo(app)
    top = pathlib.Path(out(git(app, "rev-parse", "--show-toplevel"))).resolve() if repo else app
    if not repo and not args.ci_only:
        fail(f"{app} is not a git repository: the uses are read from the changes since the base (--ci-only reads "
             "the CI alone)")
    label, base = resolve_base(app, args.base) if not args.ci_only else (None, None)

    print(f"sdkguard: {app}")
    versions, schemes, xcode_cloud, runners = read_ci(list(dict.fromkeys([top, app])), app)
    lowest = where = None
    print("CI's Xcode:")
    for at, version, what in versions:
        print(f"  {at}: Xcode {version} ({what})")
    for at, what in runners:
        print(f"  {at}: the runner image's Xcode ({what}), which the repository does not name")
    if versions:
        at, lowest, _ = min(versions, key=lambda v: vtuple(v[1]))
        where = at
        if len({vtuple(v) for _, v, _ in versions}) > 1 or runners:
            print(f"  lowest{' named' if runners else ''}, the constraint: Xcode {lowest} ({where})"
                  + (": check the runner image's Xcode above too" if runners else ""))
    elif xcode_cloud:
        print("  ci_scripts/ is Xcode Cloud, whose Xcode is set in App Store Connect"
              + (", and the workflow above builds on a runner's" if runners else ": none in the repository"))
    elif not runners:
        print("  none found (looked in .github/workflows, .github/actions, the scripts a workflow runs, "
              ".xcode-version, .circleci, bitrise.yml, .gitlab-ci.yml, .travis.yml, fastlane/Fastfile, Makefile, "
              "ci_scripts/)")
    if schemes:
        print(f"  schemes the CI builds: {', '.join(schemes)}")

    print("Installed Xcodes:")
    xcodes = installed_xcodes()
    for path, version, build in xcodes:
        print(f"  {path}: {version}{f' ({build})' if build else ''}")
    if not xcodes:
        print(f"  none in {os.environ.get('SDKGUARD_APPLICATIONS', '/Applications')}")
    if lowest is not None:
        same = [x for x in xcodes if matches(lowest, x[1])]
        if same:
            print(f"  {same[0][0].name} is the CI's Xcode {lowest}: this proves the branch compiles with it:")
            print(f"  {build_line(app, same[0][0], args.scheme)}")
        else:
            print(f"  none is the CI's Xcode {lowest}: with it installed beside 27.1 "
                  "(developer.apple.com/download/all), this prints the build line that proves the branch compiles "
                  "with it")

    sentence = ci_sentence(lowest, where, xcode_cloud, runners)
    if args.ci_only:
        print(f"verdict: {sentence}")
        return 0

    short = out(git(app, "rev-parse", "--short", base))
    files = changed_swift(app, base)
    texts = {}
    for old, new in files:
        try:
            texts[new] = (app / new).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

    # First pass: the names the branch declares, inside the guard and outside it, in every changed Swift file. A name
    # declared outside a guard at the top level or in an extension (an #else stub) compiles everywhere; one declared
    # outside a guard by a type, or as a local, only where that type's body (and its extensions'), or that block,
    # reaches (shadows).
    inside_at, outside_at, outside_owners, members, shadows, listed = {}, {}, {}, {}, {}, {}
    extensions, own_members, guarded_types, twin_members, guarded_locals = {}, [], set(), [], {}
    for new, text in texts.items():
        extensions[new] = []
        found = declarations(text, extensions[new])
        listed[new] = {(d.line, d.name) for d in found if d.listed}
        stubs = {(d.frame, d.name) for d in found if d.scope == "member" and not d.guarded}
        for d in found:
            place = f"{new}:{d.line}"
            if d.scope in ("top", "extension"):
                if d.guarded:
                    inside_at.setdefault(d.name, []).append((place, None, None))
                    if d.scope == "top" and d.keyword in TYPES:
                        guarded_types.add(d.name)
                else:
                    outside_at.setdefault(d.name, place)
                    outside_owners.setdefault(d.name, set()).add(d.owner if d.scope == "extension" else TOP_LEVEL)
            elif not d.guarded:
                shadows.setdefault(new, {}).setdefault(d.name, []).append(
                    (d.first, d.last, "member" if d.scope == "member" else "local", d.column))
                if d.scope == "member":
                    own_members.append((d, new))
            elif d.scope == "member" and not d.type_guarded and (d.frame, d.name) not in stubs:
                # A member inside the guard in a type outside it: the type's name does not cover it.
                members.setdefault(d.name, []).append((d, new, place))
            elif d.scope == "member" and d.type_guarded:
                twin_members.append((d, new, place))
            elif d.scope == "local" and d.keyword in ("let", "var", "func"):
                guarded_locals.setdefault(new, {}).setdefault(d.name, []).append((d, place))
    # An unguarded member is its type's own in that type's extensions too (each changed file; its own file when
    # private): an #else stub there covers a bare use in `extension T { … }`.
    bodies = {}
    for path, spans in extensions.items():
        for owner, first, last in spans:
            bodies.setdefault(owner, []).append((path, first, last))
    for d, new in own_members:
        for path, first, last in bodies.get(d.owner, []):
            if path == new or not d.private:
                shadows.setdefault(path, {}).setdefault(d.name, []).append((first, last, "member", 0))
    # A type written whole in the guard with its pre-Duo twin in #else: its type's name is declared outside, so the
    # members only the guarded twin has are guarded members of a type outside the guard.
    has = {}
    for d, _ in own_members:
        has.setdefault(d.owner, set()).add(d.name)
    for d, new, place in twin_members:
        if (d.owner in guarded_types and TOP_LEVEL in outside_owners.get(d.owner, set())
                and d.name not in has.get(d.owner, set())):
            members.setdefault(d.name, []).append((d, new, place))
    apps_own = {n: outside_at[n] for n in FOLDSMITH if n in outside_at}
    symbols = [s for s in SYMBOLS if s[0] not in apps_own]
    curated = {s[0].split(".")[-1] for s in SYMBOLS}
    inside_at = {n: at for n, at in inside_at.items() if n not in outside_at and n not in curated}
    # A guarded member is dropped by an unguarded top-level declaration of its name (what a bare use reaches) or an
    # unguarded extension of its own type (an #else stub). Beside an extension of another type that declares it, it is
    # confined to its type's body: a bare or self. use there is the member's, any other may be the extension's. A
    # private member is seen from its own file only, an enum case too unless named with its enum (PaneLayout.split).
    confined = {}
    for name, entries in members.items():
        owners = outside_owners.get(name, set())
        if name in curated or TOP_LEVEL in owners:
            continue
        for d, new, place in entries:
            if d.owner in owners:
                continue
            inside_at.setdefault(name, []).append((place, new if d.private else None,
                                                   d.owner if d.keyword == "case" and d.owner else None))
            if owners:
                confined.setdefault(name, {}).setdefault(new, []).append((d.first, d.last))
    # A local let, var or func declared inside the guard counts where it is used bare in the rest of its block; an
    # #else local, member or parameter of that name there is that one (shadows). Dropped by an unguarded top-level
    # declaration of its name, or an unguarded extension of the type its block sits in.
    scoped = {}
    for new, names in guarded_locals.items():
        for name, entries in names.items():
            owners = outside_owners.get(name, set())
            if name in curated or TOP_LEVEL in owners:
                continue
            spans = [(d.first, d.last, place) for d, place in entries if d.owner is None or d.owner not in owners]
            if spans:
                scoped.setdefault(new, {})[name] = spans
    patterns = {n: name_pattern(n) for n in inside_at}

    def only_inside(path):
        """The names declared only inside the guard that a use in path can mean: name → (its pattern, where, what
        must come before it or None)."""
        mine = {}
        for name, places in inside_at.items():
            place = next((at for at, only, _ in places if only in (None, path)), None)
            if place:
                mine[name] = (patterns[name], place, None)
                continue
            enums = {enum: at for at, _, enum in places if enum}
            if enums:   # an enum's case in another file: only named with its enum
                need = re.compile(r"(?<![\w$])(?:" + "|".join(map(re.escape, enums)) + r")\s*\.\s*$")
                mine[name] = (patterns[name], next(iter(enums.values())), need)
        return mine

    kind = band(lowest) if lowest is not None else None
    errors, notes, inside, waived = [], [], 0, []
    for old, new in files:
        if new not in texts:
            continue
        text = texts[new]
        added = set(range(1, text.count("\n") + 2)) if old is None else added_lines(app, base, old, new)
        guarded_names = only_inside(new)
        locals_here = {n: spans for n, spans in scoped.get(new, {}).items() if n not in guarded_names}
        guarded_names.update({n: (name_pattern(n), spans[0][2], None) for n, spans in locals_here.items()})
        hits, quiet = scan_source(text, added, symbols, guarded_names,
                                  {n: spans for n, spans in shadows.get(new, {}).items() if n in guarded_names},
                                  listed.get(new, ()),
                                  {n: spans.get(new, []) for n, spans in confined.items() if n in guarded_names},
                                  locals_here)
        waived += [(new, number, found, why) for number, found, why in quiet]
        for number, found, is_guarded in hits:
            if kind == "27.0":
                # Xcode 27.0 passes compiler(>=6.4) too: a 27.1 symbol fails there, guarded or not.
                late = [f for f in found if f[2] in ("sdk", "foldsmith") and vtuple(f[1]) >= (27, 1)]
                if late:
                    errors.append((new, number, late))
                    continue
            if is_guarded:
                inside += 1
                continue
            (errors if kind == "below" else notes).append((new, number, found))

    compile_errors = sum(1 for _, _, found in errors if compiles_not(found))
    check_errors = len(errors) - compile_errors

    def checks_said(n):
        return f"{n} availability check{'' if n == 1 else 's'}"

    print(f"iOS 27 uses added since {label} ({short}), in {len(files)} changed Swift file"
          f"{'' if len(files) == 1 else 's'}:")
    for name, at in apps_own.items():
        print(f"note: {name} is declared by the app at {at}, not Foldsmith's: its uses are the app's to guard")
    if errors and kind == "27.0":
        print(f"errors: {lines(len(errors))} the CI's Xcode {lowest} does not compile")
    elif errors:
        heads = ([f"{lines(compile_errors)} the CI's Xcode {lowest} does not compile"] if compile_errors else []) + (
            [f"{checks_said(check_errors)} outside #if compiler(>=6.4)"] if check_errors else [])
        print(f"errors: {', and '.join(heads)}")
    for new, number, found in errors:
        if kind == "27.0":
            print(f"{new}:{number}: {said(found)}: Xcode 27.0 ships Swift 6.4 like 27.1, so no supported compile-time "
                  "check separates them: propose moving CI to Xcode 27.1 in .duo/PLAN.md")
        elif any(f[2] in ("sdk", "foldsmith") for f in found):
            print(f"{new}:{number}: {said(found)}: wrap it in #if compiler(>=6.4) … #else <the pre-Duo code> #endif, "
                  "keeping #available inside")
        elif compiles_not(found):
            print(f"{new}:{number}: {said(found)}: guard this use too")
        else:
            print(f"{new}:{number}: {found[0][0]} opens iOS 27 code: put it inside #if compiler(>=6.4) with the code "
                  "it guards")
    if notes:
        print(f"notes: {lines(len(notes))} outside #if compiler(>=6.4)"
              f"{'' if kind is None else f', which the CI Xcode {lowest} builds'}")
    for new, number, found in notes:
        print(f"{new}:{number}: {said(found, note=True)}, not inside #if compiler(>=6.4)")
    if inside:
        print(f"  {lines(inside)} more inside #if compiler(>=6.4): fine")
    if waived:
        print(f"waived: {lines(len(waived))} with // sdkguard: ok, each with its why (the review reads them):")
        for new, number, found, why in waived:
            print(f"  {new}:{number}: {said(found, note=True)}: {why}")
    if not (errors or notes or inside or waived):
        print("  none")

    if kind == "below":
        if errors:
            parts = ([f"the {lines(compile_errors)} above {'does' if compile_errors == 1 else 'do'} not compile there"]
                     if compile_errors else []) + (
                [f"{checks_said(check_errors)} {'is' if check_errors == 1 else 'are'} outside the guard"]
                if check_errors else [])
            tail = f"{' and '.join(parts)} (exit 1)"
        else:
            tail = ("every iOS 27 use added is inside #if compiler(>=6.4)"
                    + (f" or waived ({len(waived)})" if waived else "") + " (exit 0)")
        print(f"verdict: CI builds with Xcode {lowest} ({where}), which has no iOS 27 SDK: {tail}")
    elif kind == "27.0":
        if errors:
            print(f"verdict: CI builds with Xcode {lowest} ({where}) and {lines(len(errors))} "
                  f"{'uses' if len(errors) == 1 else 'use'} iOS 27.1 APIs: Xcode 27.0 ships Swift 6.4 like 27.1, so no "
                  "supported compile-time check separates them: propose moving CI to Xcode 27.1 in .duo/PLAN.md (exit "
                  "1)")
        else:
            late = sum(1 for _, _, found, _ in waived
                       if any(f[2] in ("sdk", "foldsmith") and vtuple(f[1]) >= (27, 1) for f in found))
            print(f"verdict: CI builds with Xcode {lowest} ({where}): no iOS 27.1 API is used"
                  + (f" outside the {lines(late)} waived" if late else "") + ", and the iOS 27.0 ones build there "
                  "(exit 0)")
    elif kind == "27.1":
        print(f"verdict: {sentence}; the lines above are notes (exit 0)")
    else:
        print(f"verdict: {sentence} (exit 0)")
    return 1 if errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as e:   # a git command that failed: say which, as a wrong call
        fail(str(e))
