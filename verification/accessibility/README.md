# verification/accessibility/

The pattern catalog read from outside, the way the detectors read any other app: `catalog/<pattern>-<config>-<pose>.json`
is the accessibility tree XCTest saw with the phone in that pose (`scripts/capture-corpus-flow.sh` with `SNAPSHOT=1`,
the catalog launched with `-pattern … -variant … [-sheet 1]`), 17 configs × 7 poses on the iOS 27.1 Duo simulator:
captured 2026-10-26, the two sheet configs again and the two three-level and three tiled configs first on 2026-10-27
(the New Item sheet's Cancel and Add became symbols), the three arrangement configs on 2026-10-29.

`Tests/DuoPoseTestingTests/AccessibilityTests.swift` reads each through `AccessibilitySnapshot` and checks that the
detectors find the same classes as in the catalog's own frame record of the same config and pose
(`verification/matrices/`). They do, in all 119. T7 compares poses, which a frame record does not: it finds the
top-level three-level config upright on `FoldAlignedSplit`, where SwiftUI shows the empty detail alone (P1, "Three
levels"), and not on `FoldAlignedTiledSplit`, which keeps the collections beside it.

| config | closed | closed-sideways | book | laptop | tent | flat-sideways | flat-upright |
|---|---|---|---|---|---|---|---|
| catalog/arrangement-aligned | · | · | · | · | · | · | · |
| catalog/arrangement-inline | · | · | T5 | T1 | T1 | T5 | · |
| catalog/arrangement-overlay | · | · | · | · | · | · | · |
| catalog/columns-aligned | · | · | · | · | · | · | · |
| catalog/columns-single | · | · | T5 | · | · | T5 | · |
| catalog/grid-aligned | · | · | · | · | · | · | · |
| catalog/grid-naive | · | · | T14 | · | · | · | · |
| catalog/split-aligned | · | · | · | · | · | · | · |
| catalog/split-aligned-sheet | · | · | · | · | · | · | · |
| catalog/split-fixed | · | · | T14 | · | · | · | · |
| catalog/split-system | · | · | · | · | · | · | · |
| catalog/split-system-sheet | · | · | T15 | · | · | · | · |
| catalog/split-three | · | · | · | T7 | T7 | · | T7 |
| catalog/split-three-list | · | · | · | · | · | · | · |
| catalog/split-tiled | · | · | · | · | · | · | · |
| catalog/split-tiled-three | · | · | · | · | · | · | · |
| catalog/split-tiled-three-list | · | · | · | · | · | · | · |

`swift run duo-detect verification/accessibility` prints it. Frames agree to the point where it matters (the sheet at
8–467.3 pt in both) and differ where accessibility sees content rather than containers: a split view's detail column
is read from its text (511.7 pt), not its pane (495.5 pt), because its scroll view runs under the sidebar. On the
turned cover the arrangement split's frame record still lists the hidden secondary and its transcript at the primary's
frame (84–678 × 82–432); the shot and the accessibility capture show the primary alone, and are the record of what is
shown.
