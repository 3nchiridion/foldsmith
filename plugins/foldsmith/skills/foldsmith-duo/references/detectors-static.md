# Static detectors

Source scans the skill runs before any capture (workflow step 1). Each rule names its taxonomy class
(`taxonomy.md`); a hit is a question to answer by reading the code, not a finding until a capture confirms it.

| Class | Scan | Hit means | Confirm with |
|---|---|---|---|
| T9 inactive-division-ignored | `reservedRegions(kind: .division)` without `.includeInactive` in code that computes a column count or a split | the layout changes when the fold activates instead of reserving space for it [tt-111463 7:50] | the flat-sideways capture against book: column count or split moves |
| T10 stranded-horizontal-item | `ToolbarItem`, `ToolbarItemGroup` (the whole word: an app's own `ToolbarItems` type is not one) / `UIBarButtonItem` with a text-only label (`Button("…")`, `Button(NSLocalizedString(…))` or `Button(String(localized:…))` with no `systemImage`, over one line or several; `UIBarButtonItem(title:…)` with no image) / a custom-view item (`UIBarButtonItem(customView:)`, a subclass's `init(customView:)`, `initWithCustomView:`) | the item stays horizontal while the bar goes vertical [tt-111462 5:56]; a custom-view toolbar can vanish where the bar goes vertical (T7) | closed and book captures: the item sits outside the vertical bar, or is gone |
| T3 custom-bar-not-vertical | custom `UIToolbar`, `UINavigationBar`, `UITabBar` added as subviews, or a hand-built bar `HStack` pinned to an edge | the system does not move it to the side [tt-111462 2:00] | closed capture: the bar is still horizontal |
| T14 columns-off-fold | `navigationSplitViewColumnWidth(…)` with a fixed or ideal width; `minimum…`, `maximum…`, `preferred…` `PrimaryColumnWidth` or `SupplementaryColumnWidth` set to anything but `automaticDimension` | split views adjust their columns to the fold on their own [hig reserved regions]; a set sidebar width stops that (measured in [`verification/matrices/split`](https://github.com/3nchiridion/foldsmith-evidence/tree/main/verification/matrices/split): fixed 320 pt leaves the detail across the fold) | book capture: a pane edge or pane straddles 455.5–495.5 pt |
| T5 stretched-single-column | a reading `ScrollView`/`UITextView` with no width limit and no column split on regular width | one text column across the fold where the inner display wants two [tt-111466 7:34] | book and flat-sideways captures |
| T13 no-scene-lifecycle | none of: `UIApplicationSceneManifest` in an `Info.plist` (or a target's `<name>-Info.plist`) or the project's build settings, a SwiftUI `App`, a scene delegate configured in code (`configurationForConnecting`, `UIWindowSceneDelegate`) | fails to launch on the 27.1 SDK; hand to Apple's App Resizability skill | launch |

Shell versions (ripgrep):

```sh
rg -n 'reservedRegions\(kind: *\.division\)' --type swift
rg -nU '\bToolbarItem(?:Group)?\b[^{}]*\{\s*Button\(\s*(?:"[^"]*"|NSLocalizedString\([^)]*\)|String\(localized:[^)]*\))\s*(?:,\s*role:[^)]*)?\)' --type swift
rg -n 'UIBarButtonItem\(title:' --type swift
rg -n '\binit\(customView:|UIBarButtonItem\(customView:|initWithCustomView:' --type swift --type objc
rg -n 'navigationSplitViewColumnWidth|(Primary|Supplementary)ColumnWidth' --type swift
rg -n 'UIToolbar\(|UITabBar\(|UINavigationBar\(' --type swift
# T13: no file listed by all three together means no scene lifecycle (checked on the corpus: 2048 and Kickstarter only)
rg -l 'UIApplicationSceneManifest' -g '*Info.plist' -g '*.pbxproj'
rg -lU '@main\s+struct\s+\w+\s*:\s*App\b' --type swift
rg -l 'configurationForConnecting|UIWindowSceneDelegate' --type swift --type objc
```
Checked on NetNewsWire's unmodified source ([`verification/runs/NetNewsWire/`](https://github.com/3nchiridion/foldsmith-evidence/tree/main/verification/runs/NetNewsWire/)): the T10 scan lists Add Feed, Add Folder,
Account Setup, Current Activity, Activity Log and Error Log; the T14 scan lists its six sidebar and timeline widths. On
IceCubesApp's ([`verification/runs/IceCubesApp/`](https://github.com/3nchiridion/foldsmith-evidence/tree/main/verification/runs/IceCubesApp/)) the T10 scan lists the list's Add Account and the relationship note;
before it matched whole words it also caught the composer's `ToolbarItems(…)`, an app type, and ran on to an alert's
`Button("OK")`. On Wikipedia's ([`verification/runs/Wikipedia/`](https://github.com/3nchiridion/foldsmith-evidence/tree/main/verification/runs/Wikipedia/)) the custom-view scan lists 13 lines, among them
`IconBarButtonItem`, the subclass behind the article toolbar that stayed horizontal on the cover and vanished in book;
read each against the captures (a spinner in a sheet's bar is harmless, a toolbar is not). NetNewsWire's three include
the article's Reader View button, which stays beside the vertical bar on the cover and in the detail pane. T13's plist
glob takes `*Info.plist`: Wikipedia's manifest is in `Wikipedia/Wikipedia-Info.plist`, which `Info.plist` missed.
