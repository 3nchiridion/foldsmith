# Precedent — how the two prior foldable platforms parametrized layout

Collected 2026-10-24. Primary docs and library source, not summaries of them.

## 1. Microsoft Surface Duo (2020–2023)

### The five dual-screen app patterns (Microsoft's own names)
Source: https://learn.microsoft.com/en-us/previous-versions/dual-screen/introduction (archived; last updated 2020-09-10). The dedicated `design/app-patterns` page is no longer served.

| Pattern | Definition | When | Microsoft's examples |
|---|---|---|---|
| **Extended canvas** | Both screens as one free-flowing canvas | Drawing, maps, anything scrollable so the user can move content off the seam; applies only to the canvas portion | Drawing, tables, maps |
| **List-detail** | Main pane (list) + details pane; selection updates detail | Mail, address books, galleries, playlists; in dual-landscape prefer list-only or detail-only because users want more space | Mail, scheduling, photo curation |
| **Two page** | Book-like paging, one page per screen | Naturally paginated content; advance one or two pages at a time | Documents, reading, notes, art boards |
| **Dual view** | Two views of the same content type side by side, or one thing two ways | Compare two images/lists/docs; list + map; before/after (Markdown + preview); if you don't want to design two views, use multi-instance instead | Find-the-differences, directions + map |
| **Companion pane** | Canvas on one screen, tools that act on it on the other; surfaces level-2 UI | Supplementary context or tools; place tools right or bottom for ergonomics and test | Image + controls, charts, tables, game controller |

Design principles stated: continuous value (spanning must enrich the whole task, not be a novelty); it isn't all about spanning (don't bury fundamentals behind it); users are always in control (never span programmatically); make spanning predictable.
User intent by orientation: dual-landscape = wants more real estate (expand content); dual-portrait = wants multitasking/productivity (separate and group).
Grid rule: even number of columns, margins accounted for toward the seam. No numeric device metrics anywhere; explicit advice not to design to any one device's specs.

### How the libraries parametrized it (source in `ms-source/`)
- `surface-duo-compose-sdk` @ 17769ca (2023-06-13), MIT. `TwoPaneLayout(paneMode, pane1, pane2)` with `TwoPaneMode { TwoPane, HorizontalSingle, VerticalSingle, SinglePane }`. Decision is one boolean function of `WindowMode { SINGLE_PORTRAIT, SINGLE_LANDSCAPE, DUAL_PORTRAIT, DUAL_LANDSCAPE }` × `paneMode` (`TwoPaneLayoutCore.kt:108`). `WindowState` carries `hasFold, foldIsHorizontal, foldBoundsDp, foldState {FLAT, HALF_OPENED}, foldIsSeparating, foldIsOccluding, windowWidthDp/HeightDp`, derives `foldSizeDp` (0 when not separating) and `largeScreenPane1Weight` (default 0.5).
- `surface-duo-sdk` @ e292ff5 (2026-09-14), MIT. View-system `FoldableLayout` takes **five layout ids** — `single_screen`, `dual_screen_start`, `dual_screen_end`, `dual_portrait_single`, `dual_landscape_single` — plus `is_dual_*_single_container` booleans and a hinge-color preview. I.e., the developer supplies a layout per window mode and the library swaps them.

**Lesson for the Duo catalog:** Microsoft's winning artifact was the five-name vocabulary. Their libraries were thin: a mode enum, a weight, and layout-per-mode swapping. Apple's `ArrangementView` already covers the library layer better than TwoPaneLayout did, which leaves the vocabulary layer open.

## 2. Android large screens and foldables (2021–)

### Canonical layouts (Google/Material names)
Source: https://developer.android.com/develop/ui/compose/layouts/adaptive/canonical-layouts (Material: https://m3.material.io/foundations/layout/canonical-layouts/overview, not fetched — client error).

| Layout | Content relationship | Expanded | Medium | Compact |
|---|---|---|---|---|
| **List-detail** | Detail is meaningful on its own | Both panes; selection updates detail | One pane; detail replaces list; back returns | same as medium |
| **Feed** | Elements are peers; size and proximity carry meaning | Multi-column grid | Multi-column as space allows | Single column |
| **Supporting pane** | Secondary is meaningful only relative to primary (comments, tools, related) | 70 / 30, landscape preferred | 50 / 50 if content tolerates narrow widths | Supporting content below main or in a bottom sheet behind a control |

Transitions: expanded → narrower keeps the detail and hides the list; detail-only → expanded shows both with the item highlighted; list-only → expanded shows list + placeholder detail. All state hoisted; back handling separate from navigation because it depends on size class.
Width size classes (from the general guide, not this page): compact < 600 dp, medium 600–839 dp, expanded ≥ 840 dp.

### Fold awareness
Source: https://developer.android.com/develop/ui/compose/layouts/adaptive/foldables/make-your-app-fold-aware
- `FoldingFeature { state: FLAT | HALF_OPENED; orientation: HORIZONTAL | VERTICAL; occlusionType: NONE | FULL; isSeparating; bounds }`. No hinge angle exposed: "reporting ranges and sensor accuracy vary by device".
- **Tabletop** = HALF_OPENED ∧ orientation HORIZONTAL (device on a surface). Media above the fold, controls and supplementary content below; camera viewfinder above, controls below.
- **Book** = HALF_OPENED ∧ orientation VERTICAL. Two-page layout across the fold; reading; hands-free photography.
- HALF_OPENED always implies `isSeparating`. Don't place controls near a separating fold. Use `occlusionType` to decide if content may sit inside `bounds`.
- Dual-screen mode (Pixel Fold, Android 14+): `WindowAreaController` with `OPERATION_PRESENT_ON_AREA` shows different content on both displays at once; `OPERATION_TRANSFER_ACTIVITY_TO_AREA` = rear display mode (the inner display turns off). Apple's `CameraCaptureAccessory` is the narrower analogue.

**Lesson:** Android converged on the same two postures Apple calls book and laptop/tabletop and the same split of "media/content above, controls below" for tabletop. Apple's own talk (111463, 4:00) states the identical rule. That cross-platform agreement is the strongest evidence any Duo pattern can cite.

## 3. Mapping between vocabularies (working hypothesis for Phase 2, to be checked against measurements)

| Microsoft | Android | Apple API / HIG wording |
|---|---|---|
| List-detail | List-detail | `NavigationSplitView`; "Mail shows list or email closed, both open" |
| Companion pane | Supporting pane | `ArrangementView` `.split` with `splitArrangementLayoutRatio`; "controls near the content they affect" |
| Two page | Book posture two-page | `ArrangementView` `.split.axes(.horizontal)` with an inactive division used for an even split; "avoid the crease" |
| Dual view | — (multi-instance) | Split View multitasking / multiple scenes (inner display only) |
| Extended canvas | Feed (scrolling) | `ScrollView`/`List`: "continuously scrolling content must not displace" |
| — | Tabletop: media above, controls below | 111463 4:00: top region for viewing at distance, bottom for stable touch; `.overlay` → side-by-side when folded |
| — | Dual-screen mode | `sceneAccessory` / `CameraCaptureAccessory` (camera only) |

Apple-only concepts with no precedent: vertical bars and the shared bar region; displacement as a named technique; occlusion regions for the under-display camera; the outer display as a *second* compact-width screen the app also has to be good on.
