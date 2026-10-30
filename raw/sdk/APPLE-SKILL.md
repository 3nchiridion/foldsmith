# APPLE-SKILL — what Xcode 27.1's own agent skills cover for iPhone Duo, and what they leave to us

Source: `xcrun agent skills export --output-dir raw/sdk/apple-skill` on Xcode 27.1 (27A9275), 2026-10-25.
The export needs Xcode running and a one-time "allow" in Xcode's agent-access dialog. It also resolves a
relative `--output-dir` against `/`, so pass an absolute path.

11 skills came out (~990 KB). Only three touch Duo layout:

| Skill | Duo relevance |
|---|---|
| `app-resizability` | **The** Duo skill. Its trigger names "iPhone Duo" and "the foldable iPhone" |
| `swiftui-whats-new-27` (`references/toolbar.md`) | Toolbar overflow APIs for constrained width |
| `device-interaction` | Drives the simulator (tap, swipe, orientation, screenshots, UI hierarchy). Relevant to the harness |

The rest (`adopt-c-bounds-safety`, `app-intents-*`, `audit-xcode-security-settings`, document-based apps,
`modernize-tests`, `swiftui-specialist`) don't mention Duo, folds, hinges or reserved regions.

## What `app-resizability` does

A **code-migration** skill for UIKit (Swift and Objective-C): find legacy shared-state APIs and replace each one
in place. Treats any Duo request as "run every task". Five tasks, run in order:

1. **`UIScreen.main`** → `traitCollection.displayScale`, `view.bounds`, etc., plus trait-change registration when the value is cached.
2. **`interfaceOrientation`** → size classes or window bounds; deprecated scene geometry callback → `didUpdateEffectiveGeometry`.
3. **App → scene lifecycle** (adds a scene manifest and a `SceneDelegate`).
4. **Safe area**: replaces `top/bottomLayoutGuide` and hard-coded bar offsets, and removes **symmetric-inset assumptions** (the one Duo-hardware rule, below).
5. **`userInterfaceIdiom`** → size classes where the check is really about space.

Before it edits, it does three read-only `Info.plist`/build-setting checks: a launch screen is declared (iOS 27
rejects uploads without one, `ITMS-90870`), iPad lists all orientations, and `UIRequiresFullScreen` (ignored on
iOS 27, TN3192). It never deletes or adds those keys.

Strict editing rules: always apply a replacement when one fits (an empty diff is a failure), touch only lines
with the target API, never substitute a global (`UIApplication.shared`, `UIDevice.current`) as the replacement,
API swap plus invalidation applied together or not at all, ask the user before risky signature changes.

### Its Duo-specific content (all in `references/safe-area-task.md`)

- **Asymmetric horizontal insets are the normal case.** With a vertical bar, one edge carries the whole
  (large) inset and the other carries zero. Which edge changes with orientation **and with which display is in use**.
- Never infer the inset edge from device, model, orientation, size or size class. Its own wording: two
  physically different poses report the same orientation and the same geometry.
- `traitCollection.verticalBarEdge` (UIKit) and `@Environment(\.toolbarVerticalEdge)` (SwiftUI) say which edge
  holds the bar. The UIKit one is `leading`/`trailing` (directional) while `safeAreaInsets` is physical, and
  `.unspecified` is ambiguous (no bar possible *or* edge not resolved). Read the inset when you need the size.
- Register with `systemTraitsAffectingVerticalBarEdge` when reading outside a layout method.
- SwiftUI: `EdgeInsets` is directional; `GeometryProxy.size` is already inset; don't re-apply reported insets as padding.

These agree with `raw/sdk/DIFF.md` (`UIVerticalBarEdge`, `toolbarVerticalEdge: HorizontalEdge?`).

## What it does NOT cover (our catalog's territory)

Checked by searching all 11 exported skills, references included:

| Duo API / topic | Mentioned anywhere? |
|---|---|
| `ReservedRegion` / `reservedRegions(…)` (occlusion, division, `includeInactive`) | **No** |
| `DeviceHinge`, `onHingeChange`, `UIHingeInteraction`, `UIHinge` | **No** |
| `ArrangementView`, `UIArrangementViewController`, split/overlay arrangements, layout ratios | **No** |
| `UIView.LayoutRegion` (incl. `bar(onEdge:extent:)`) | **No** |
| `toolbarVerticalBehavior` / `UIVerticalBarBehavior` (turning the vertical bar off) | **No** |
| `toolbarVerticalCompressionBehavior` / `UIVerticalBarCompressionBehavior` | **No** |
| `axisBehavior` (`.horizontalOnly`, `.verticalPreferred`) | **No** (toolbar.md covers `visibilityPriority`, `ToolbarOverflowMenu`, `.topBarPinnedTrailing`, minimize-on-scroll, not axis behavior) |
| `presentationPlacement` / sheet `preferredPlacement` | **No** |
| Folding as a runtime event: state across a fold, what moves, settle time | **No** |
| Which **layout pattern** a screen should use on a fold (list/detail, media + controls, canvas + tools, …) | **No** |
| Verifying every pose (flat, book, laptop, closed/outer display) | **No** |

In short: Apple's skill makes an app *able* to resize correctly (no stale screen or orientation assumptions,
honest safe areas). It says nothing about *designing for the fold*: where content goes around the
division, when to split or overlay, what the hinge state should change, or how to prove each pose.

## `device-interaction` and the harness

It drives a simulator session: `t`/`d`/swipe/`drag`/multi-touch, hardware buttons (`b h/p/u/d`), typing,
`orientation portrait|landscapeLeft|…|faceUp|faceDown`, screenshots and UI-hierarchy captures. **No fold, hinge
or pose command**, and no display selection. That confirms docs/history/STATUS.md finding 2: pose control still needs Device
Hub or the community `duo.py`. It is still useful for screenshots and accessibility hierarchy in each pose once
something else has set the pose.

## What this means for our skill (`skills/foldsmith-duo`)

- **Defer to Apple's skill for migration.** Don't re-teach `UIScreen.main`, orientation, idiom, scene lifecycle or
  symmetric insets. Route to `app-resizability` first ("run Apple's App Resizability skill, then come back").
- **Own everything in the "No" table:** reserved regions, hinge, arrangements, vertical-bar opt-out/compression,
  toolbar axis behavior, sheet placement, and above all pattern choice per screen and per-pose proof.
- **Cite, don't contradict:** our patterns should use Apple's inset rules as-is (asymmetric, per-edge, directional
  vs physical) and point to the safe-area task for them.
- **Harness:** pose control stays external (Device Hub / `duo.py`); `device-interaction` can do capture and taps.

## Licensing note

`raw/sdk/apple-skill/` is Apple's text, copied verbatim. Like the talk transcripts (docs/history/STATUS.md, docs/history/DEVIATIONS.md),
it is git-ignored: regenerate it locally with the export command above.
