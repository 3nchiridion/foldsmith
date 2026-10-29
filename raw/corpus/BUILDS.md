# BUILDS — Mac phase Step 4 (all eight: 2048, NetNewsWire, IceCubesApp, home-assistant/iOS, wikipedia-ios, Signal-iOS, kickstarter/ios-oss, firefox-ios)

Xcode 27.1 (27A9275), iOS 27.1 simulator SDK, iPhone Duo simulator (runtime 24A94425). Each app at its pinned
commit in `manifest.txt`, built for the simulator with `CODE_SIGNING_ALLOWED=NO`, unmodified first. Build folders
lived in a scratch directory and were deleted after each app. Screens: `evidence/<app>/<screen>-<pose>-<panel>.png`
from `scripts/capture-corpus-app.sh`, which checks every shot's shape against its pose.

Build rule learned on the way: an app that keeps data in an app-group container (Home Assistant, Wikipedia, Signal) aborts
at launch when built with signing off (Firefox logs the same refusal and carries on, so the trap is in how each app handles
the nil container), because no entitlements are embedded and the container lookup is refused. The
second step for such an app is ad-hoc simulator signing on the command line (`CODE_SIGN_IDENTITY=-
CODE_SIGN_STYLE=Manual DEVELOPMENT_TEAM= PROVISIONING_PROFILE_SPECIFIER=`), a flag, not a source change.

Erratum (Phase 2, 2026-10-26): the fold's division frame is 455.5–495.5 pt, centred on the display's middle at 475.5 pt
(`raw/metrics.json`). Home Assistant, Wikipedia, Signal and Firefox were first measured against 435.5–475.5 pt;
every fold finding was re-measured, the notes below and `defects.csv` carry the corrected numbers, and the rows that
no longer hold are listed in `patterns/CLUSTERING.md`.

| App | Commit | Unmodified build | What it took | Runs? | Screens captured |
|---|---|---|---|---|---|
| 2048 | 6f89eab | **failed**: deployment target 8.0 is below Xcode 27.1's minimum (15.0) | `IPHONEOS_DEPLOYMENT_TARGET=15.0` on the command line (needed target bump); 0 warnings | **no — crashes at launch** in every pose | launch (shows the Home Screen) |
| NetNewsWire | d9ec7df | **failed**: `SecretKey` missing (Feedly/Inoreader OAuth keys) | its CI's own step, `buildscripts/updateSecrets.sh`, with no keys set (empty strings; only those sign-ins are affected); then 0 code warnings; build folder 788 MB | yes | launch (Feeds on the cover; empty timeline and "No selection" inside) |
| IceCubesApp | 98098b9 | not attempted bare: its README says the build fails without `IceCubesApp.xcconfig` | README step: `IceCubesApp.xcconfig` from the template, empty team, bundle prefix `dev.enchiridion.corpus`; then 0 code warnings; build folder 1.9 GB | yes | launch = Add Account sheet with keyboard (no account) |
| home-assistant/iOS (`iOS` in the manifest; evidence under `HomeAssistant/`) | 3ef4355 | **compiled, traps at launch**: with signing off no entitlements are embedded, the app-group container lookup is refused, and the environment's one-time setup re-enters itself while logging that (`_dispatch_once_wait`, SIGTRAP; `Environment.swift:31`) | README step: `Configuration/HomeAssistant.overrides.xcconfig` with no team, prefix `dev.enchiridion.corpus`, SwiftLint off; then ad-hoc simulator signing on the command line (`CODE_SIGN_IDENTITY=- CODE_SIGN_STYLE=Manual`) so the entitlements go in; warnings in its own code (self-imports, deprecations, Sendable); build folder 5.7 GB, packages 2.1 GB | yes | launch (Welcome), servers (Searching on home network), manual-url (sheet + keyboard), invalid-url (empty Connect: no visible change), learn-more (Safari sheet); 5 screens × 7 poses |
| wikipedia-ios (evidence under `Wikipedia/`) | 2031b89 | **failed**: the project's base configuration `Configurations/OpenSourceDebug.xcconfig` is git-ignored and absent | README step: `scripts/setup_bundle_id ci` writes it (Wikimedia's default team, empty `SIGNING_DISAMBIGUATOR`, so the bundle id is `org.wikimedia.wikipedia`); then compiled, but the unsigned app aborts at launch on its app-group container (SIGABRT after `client is not entitled`); ad-hoc signing fixed it. Warnings in its own code (a missing `WMFBackgroundFetcher` protocol ×43, deprecations, capture semantics); build folder 1.9 GB, 6 packages | yes | launch (onboarding page 1), explore (feed), article (Mount Everest via Search), places (map), settings (via Profile); 5 screens × 7 poses |
| Signal-iOS (evidence under `Signal/`) | 3ace2d5 | **failed**: Xcode 27.1 has no Metal compiler until its Metal Toolchain component is downloaded (`SpoilerParticleShader.metal`); everything else compiled | BUILDING.md's steps without CocoaPods: the `Pods` submodule (signalapp/Signal-Pods, fetched with a blob filter), RingRTC's prebuilt via `Pods/SignalRingRTC/bin/set-up-for-cocoapods` with the Podfile's checksum, libsignal's prebuilt fetched by its own build phase, `Config/User.xcconfig` from the sample (warnings not errors); `xcodebuild -downloadComponent MetalToolchain`; then the unsigned app traps at launch (`MainAppContext.swift:144`, app-group container nil) and ad-hoc signing fixed it. 0 warnings in its own code; build folder 4.7 GB | yes | launch (splash), permissions, phone (number entry with keypad), restore (choice sheet), restore-no-device; 5 screens × 7 poses; the chat list and the custom tab bar are behind registration |
| kickstarter/ios-oss (evidence under `Kickstarter/`) | 5f5463c | **succeeded** after the README's setup: `make configs` (copies the `.example` configs) and the secrets fallback (`Configs/Secrets.swift.example` into `KsApi`, with the README's mock-data switch `isOSS = true`); warnings in its own code (deprecated legacy colours and grid, `statusOfValue`); build folder 2.5 GB, 41 packages | nothing else | **no — fails to launch** in every pose: `UIScene life cycle is required for apps built with this SDK` (`_UIApplicationEvaluateRuntimeIssueForNoSceneLifecycleAdoption`, SIGTRAP); no `UIApplicationSceneManifest`, the app delegate owns the window | launch (the Home Screen) |
| firefox-ios (evidence under `Firefox/`) | 783d862 | **failed** on my first attempt only: I passed `-configuration Fennec`, which does not exist (the Fennec scheme builds with Debug), so the local BrowserKit packages went to a different products folder and `ActionExtension` could not find `ActionExtensionKit` | README setup: Nimbus FML bootstrap (`application-services` script, read before running) and `npm install && npm run build` for the JavaScript assets; then the Fennec scheme with its Debug configuration, unsigned: succeeded; warnings in its own code (deprecations, a Swift 6 isolation warning in generated Rust bindings); build folder 3.7 GB | yes, unsigned (logs the app-group refusal and continues) | launch (first-run Welcome), home, page (Mount Everest on en.wikipedia.org), tabs, menu, settings; 6 screens × 7 poses |

## Notes per app

**2048** — no launch screen (`UILaunchStoryboardName` absent), portrait only, no `UIScene` adoption. Built
against SDK 27.1 it traps in `_UIApplicationEvaluateRuntimeIssueForNoSceneLifecycleAdoption` as the first scene
is created (`EXC_BREAKPOINT`), so it never draws: an app that has not adopted scene lifecycle cannot run once it
is rebuilt with the 27.1 SDK. This is the scene-lifecycle task in Apple's `app-resizability` skill, seen failing
hard. Logged as `NEW-1`.

**NetNewsWire** — uses scenes; iPhone orientations portrait and landscape (no upside-down). Moves its controls into
the system's vertical bar on the cover (trailing; leading when the cover is turned) and on the inner display held
sideways. In book its split view keeps its own column width (≈323 pt), so the article pane straddles the active
fold (`NEW-2`). The Add Feed sheet (`feed://` URL) could not be reached headless: a custom scheme raises an
"Open in NetNewsWire?" system alert that only a tap can answer, and taps work on the cover only.

**IceCubesApp** — uses scenes; portrait and landscape (no upside-down). Already reads `toolbarVerticalEdge`
(`ToolbarTab.swift`). Without an account it opens on the Add Account sheet with the keyboard up. In book the sheet
sits on the **leading** half, over the Trending timeline on the trailing half; the app sets no
`presentationPlacement`, so this is the system's automatic placement, which the app could override (`NEW-3`).
Upright (laptop, tent, flat) the sheet spans the width and the keyboard fills the lower half; flat sideways it is a
centred form sheet over the app's sidebar layout.

System behaviour seen along the way: in book the keyboard splits into two halves around the fold.

Redacted: the Trending timeline behind the sheet showed a third party's public Mastodon post. It is pixelated in
`launch-book-inner.png` (the post, plus a strip behind the bottom keyboard row, which clips the `.com` and return
keys) and `launch-flat-sideways-inner.png` (fragments at the sheet's edge). Layout, sheet and keyboard are untouched.

Captured by accident, kept as evidence: with NetNewsWire's notification prompt up, the system placed the alert
on the **trailing half in book** and centred it when flat (`evidence/NetNewsWire/alert-*.png`), matching Apple's
"alerts and sheets to the trailing half" rule.

## What the screenshots cannot show

`simctl io screenshot` returns each display in the app's own interface orientation, so a screenshot cannot tell
whether an app followed the device upside down (tent). That needs the app's own reading (as DuoProbe logs it).

## Capture problems met (and fixed) during the pilot

- A system alert (notification permission, "Open in …?") survives relaunches and covers every later shot; restart
  the simulator and dismiss it on the cover before capturing (`Don't Allow` tapped with the desktop app's
  simulator control).
- Book's orientation was dropped once after unfolding; the capture script now re-posts it when a shot comes out
  the wrong shape.
- An interrupted Xcode device-interaction session (`xcode_device.py`) left the simulator unable to launch apps
  until CoreSimulatorService was restarted. Not used again.

**home-assistant/iOS** — uses scenes, supports multiple scenes; all four orientations; `UIRequiresFullScreen` absent;
deployment target 16.4. Already carries Duo code at this commit: a `UIHingeInteraction` observer feeding a hinge
sensor, an occlusion-region reader (`reservedRegionsOfKind:` looked up at runtime), and a welcome screen that shifts
its content by half the safe-area asymmetry so it reads as centred on the whole display. That centring is what puts it
on the fold: in book the logo, title, body, the Connect button (267–686 pt) and Learn more all straddle the active
division (455.5–495.5 pt), `T1`. Held upright (laptop, tent) a body line (459–474 pt) lies inside the horizontal
division, but the text is inside the screen's scroll view, which Apple exempts (Phase 2, `patterns/CLUSTERING.md`);
the Connect button sits on the flat half, the logo on the raised one. Flat, the same layout over the inactive division. On the turned cover (compact height) the app rotates and
moves both actions into the navigation bar (Learn more leading, Connect trailing); the status bar is hidden there.
Deeper screens via `scripts/capture-corpus-flow.sh` and `Tap/DuoTapUITests` (tap shut, fold, shoot), 7 poses each:
- **servers** (Searching on home network, the debug build's test servers): one centred column. Book: cards
  244–624 pt (scrolling content) and the floating Enter address manually button (edge ≈ 542 pt) straddle the
  vertical division, `T1` for the button; back and help sit in the trailing vertical bar. Laptop/tent: card
  backgrounds cross the horizontal division but they scroll (exempt); the floating button is on the flat half. Cover turned: back/help in the leading bar, list centred.
- **manual-url** (What is your Home Assistant address?): a sheet with the keyboard up. Book: on the **leading** half
  (8–467 pt), the keyboard split around the fold, the sheet's trailing edge in the division's leading margin and the
  Connect button (28–447 pt) clear of it, `T15` (was `NEW-3`) (second app after IceCubesApp; the app sets no `presentationPlacement`).
  Laptop/tent: full-width card, the Connect button (400–447 pt) stays above the horizontal division (455.5–495.5 pt),
  the keyboard fills the flat half. (Logged as `T1` until Phase 2 re-measured it against the correct band.) On the cover the sheet's close button is in the vertical bar; the title scrolls off
  under the keyboard (not Duo-specific).
- **invalid-url** (Connect with an empty field): no visible change in any pose, kept as a duplicate of manual-url.
- **learn-more** (`SFSafariViewController`): on the cover Safari's controls fill the trailing vertical bar (leading
  when turned). Book: the sheet is on the leading half, ending at 467.3 pt, `NEW-3`; its toolbar pills stay horizontal
  at the sheet bottom. Flat sideways the same sheet is centred (151–804 pt): the system's placement follows the
  division's state. Laptop/tent: full-width card, web content scrolls across the horizontal fold exactly as Apple's
  Safari does in the oracle, so not logged.
Continuity held in every flow: each screen survived the fold from shut to the pose with its state intact.

**wikipedia-ios** — uses scenes (single scene), portrait and both landscapes (no upside-down), `UIRequiresFullScreen`
present but **false** (the corpus profile's count of 4 was the key, not the hazard), system `UITabBarController`.
No Duo APIs. Flows: onboarding is four pages with Next and no Skip on page 1; Explore after it; an article through
the Search tab (typed with the runner's `type:` step); Places; Settings through the Profile button.
- **Cover**: the system tab bar goes vertical into the trailing column with the nav items above it, and Safari-style
  pills float at the bottom of the article. Turned (compact height) the vertical bar compresses: on Explore it keeps
  the three nav items and shows only the current tab, on Places it collapses the nav items into an overflow button and
  shows all five tabs, `NEW-4`. The onboarding image overlaps its Learn more link there, `T6`.
- **Book**: the article is one column across the whole display (measure ≈ 690–740 pt), `T5`, every line over the
  fold; Settings is one full-width list, `T5`, where Apple's Settings splits on the fold; Explore's two-column grid
  puts the right column's edge at 458.7 pt, inside the division, `T14` (columns off the fold); Places spans its
  search field across the fold but keeps the list panel on the leading half and the callout on the trailing half, `T1`; the onboarding centres its
  illustration on the fold, `T1`.
- **Laptop/tent**: the onboarding keeps the band clear (text raised, image flat); Explore's feed, the article, the
  Settings list and the Places list panel all scroll across the horizontal division, which Apple exempts (Phase 2
  reclassified these from `T1`); tab bars and tools float on the flat half.
- **Flat**: identical to book and laptop (inactive division ignored).
Cover orientation: after an upright pose the shut cover launched the app landscape and it ignored every orientation
posted until it was turned while running; the flow script now primes the orientation before each flow
(docs/history/DEVIATIONS.md). Build: the git-ignored team xcconfig from `scripts/setup_bundle_id ci`, then ad-hoc signing.

**Signal-iOS** — uses scenes; portrait and both landscapes in the plist, but the registration screens do not rotate on
the turned cover (every closed-sideways shot is upright, as Apple's Settings behaves); custom `OWSTabBar` and
`HomeTabBarController` exist but sit behind phone-number registration, which the simulator cannot complete
(no SMS, no debug bypass in the source). No Duo APIs. What is reachable, 7 poses each:
- **Splash**: one centred column; book puts the Continue and Restore buttons (32–855 pt) and the illustration on
  the fold, `T1`; laptop keeps text and buttons on the flat half but the illustration's figure crosses the fold.
- **Permissions**: the Continue button spans the fold in book, `T1`; laptop keeps the band clear.
- **Phone entry**: the number field and the Register Without Number pill cross the fold in book, `T1`; the system
  numeric keypad goes to the trailing half in book and fills the flat half in laptop; there the pill (to 439 pt) stays
  above the division (455.5–495.5 pt).
- **Restore choice**: a sheet on the leading half in book (8–467 pt), `T15` (was `NEW-3`), third app; centred (149.0-801.7 pt) when
  the fold is inactive (flat sideways); on the flat half in laptop.
- **Restore, no old phone**: "I don't have my old phone" leads to the same Allow Permissions screen, so this flow
  duplicates the permissions findings (kept as `restore-no-device-*`).
- **Cover**: Next, close and more buttons go into the trailing vertical bar; the content is centred on the safe area.
Flows: contacts and notifications prompts denied (iOS 27's contacts prompt has a second system sheet the runner
cannot press); a fresh install before every capture because Signal persists that its splash was shown.

**kickstarter/ios-oss** — the one corpus app whose custom tab bar (`FloatingTabBar: UITabBar`, a pill with icon-only
tabs and its own selection indicator, under `RootTabBarViewController`) is reachable without an account, and it
never draws: with no scene manifest and a window owned by the app delegate, the 27.1 SDK build traps at launch
exactly as 2048 did, `NEW-1`, now two apps, one of them maintained (deployment target 18.0, commit of 2026-10).
`raw/corpus/evidence/Kickstarter/launch-crash.txt` has the report. The custom-tab-bar hazard therefore stays
untested in this corpus; testing it means the scene-lifecycle migration first, which is a task of Apple's
`app-resizability` skill and belongs to a migration, not to this measurement step. A 26.x SDK build would run in
compatibility mode (`T12`) but no earlier Xcode is installed.

**firefox-ios** — scenes adopted, all four orientations, no `UIRequiresFullScreen`; already queries
`reservedRegions(kind: .occlusion)` and `.division` in a debug settings screen (`SafeAreaGuidesSetting.swift`), so the
team knows the regions exist. Layout per pose:
- **Cover**: its own bottom toolbar stays horizontal (address field, then back, forward, search, menu, tabs), clear of
  the trailing system column; Apple's Safari puts the same controls in the trailing vertical bar, `T3`. Turned, the
  browser rotates to a top bar like Safari; the first-run Welcome card does not rotate.
- **Book**: the iPad layout (top bar with the address field 121–711 pt, a tab strip), so the address field crosses the
  fold on every screen, `T1`; the tab tray's segmented control does too, `T1`. The menu and Settings sheets go to the
  leading half and centre when the fold is inactive, `T15` (was `NEW-3`), the fourth app. Web content (the Wikipedia article) runs
  across the fold at an ≈ 817 pt measure, as Safari's does in the oracle, so it is not logged; the Wikipedia app laid
  the same article out at 690–740 pt.
- **Laptop/tent**: chrome on the raised half; the Welcome card's text and the Settings list scroll across the
  horizontal division (exempt, reclassified from `T1` in Phase 2); web content scrolls across it as in Safari. Tent differed from laptop on the article only because
  the page showed Wikipedia's install banner in that capture.
- **Flat**: identical to laptop and book except the menu and Settings sheets, which centre.
Flows used Firefox's own UI-test launch arguments (docs/history/DEVIATIONS.md); the first-run card is from a plain launch.
