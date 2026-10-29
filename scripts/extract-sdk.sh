#!/usr/bin/env bash
# Phase 1: pull the public Swift interfaces for the Duo APIs out of the iOS 27.1 simulator SDK
# into raw/sdk/, verbatim, with the SDK build recorded. Run on the Mac with Xcode 27.1 selected.
set -euo pipefail
OUT="$(cd "$(dirname "$0")/.." && pwd)/raw/sdk"
SDK="$(xcrun --sdk iphonesimulator --show-sdk-path)"

# Guards run before anything is written, so a refused run leaves earlier output in raw/sdk/ intact.
# On an older SDK every grep below comes back empty, which reads as "the SDK has none of these APIs".
SDK_VER="$(xcrun --sdk iphonesimulator --show-sdk-version)"
IFS=. read -r SDK_MAJ SDK_MIN _ <<< "$SDK_VER.0"
if (( SDK_MAJ < 27 || (SDK_MAJ == 27 && SDK_MIN < 1) )); then
  echo "error: simulator SDK $SDK_VER is selected ($(xcode-select -p)); the Duo APIs need 27.1 or later." >&2
  echo "       Install Xcode 27.1, then: sudo xcode-select -s /Applications/<Xcode 27.1>.app" >&2
  exit 1
fi

# Anchor symbols from raw/apple-docs/api-*.md. A single miss is a finding for DIFF.md, not a reason to
# stop (the SDK may spell a name differently); none at all means the SDK has no Duo APIs.
SWIFTUI_IF=$(find "$SDK/System/Library/Frameworks/SwiftUICore.framework" -name 'arm64-apple-ios*.swiftinterface' 2>/dev/null | head -1)
UIKIT_IF=$(find "$SDK/System/Library/Frameworks/UIKit.framework" -name 'arm64-apple-ios*.swiftinterface' 2>/dev/null | head -1)
found=0
for anchor in "$SWIFTUI_IF:DeviceHinge" "$SWIFTUI_IF:ReservedRegion" "$SWIFTUI_IF:ArrangementView" \
  "$UIKIT_IF:UIArrangementViewController" "$UIKIT_IF:UIHingeInteraction"; do
  f="${anchor%:*}" s="${anchor##*:}"
  if [ -n "$f" ] && grep -q -E "\b$s\b" "$f"; then found=$((found + 1)); else echo "warning: $s not found in ${f:-<no swiftinterface>}" >&2; fi
done
if (( found == 0 )); then
  echo "error: none of the Duo anchor symbols are in SDK $SDK_VER ($SDK)." >&2
  exit 1
fi

# Clear this script's previous output so reruns don't append duplicates; DIFF.md, APPLE-SKILL.md and apple-skill/ stay.
mkdir -p "$OUT"
rm -f "$OUT"/SDK.txt "$OUT"/*.grep.txt "$OUT"/*.swiftinterface.txt "$OUT"/UIKit.*.h.txt \
  "$OUT"/SwiftUICore.DeviceHinge.Status.txt "$OUT"/SwiftUICore.VerticalEdge.txt

echo "SDK: $SDK" | tee "$OUT/SDK.txt"
xcodebuild -version | tee -a "$OUT/SDK.txt"
plutil -p "$SDK/SDKSettings.plist" 2>/dev/null | grep -iE 'Version|Build' | tee -a "$OUT/SDK.txt" || true

# SwiftUI layout APIs live in SwiftUICore; UIKit ones in UIKit (+ UIKitCore). Search all .swiftinterface.
SYMBOLS=(ArrangementView ArrangementViewStyle SplitArrangementViewStyle OverlayArrangementViewStyle
  splitArrangementLayoutRatio splitArrangementLayoutSize splitArrangementFixedLayoutSize overlayArrangementEdge overlayArrangementZIndex splitArrangementAxis
  ReservedRegion reservedRegions DeviceHinge DeviceHingeContext onHingeChange
  toolbarVerticalBehavior ToolbarVerticalBehavior toolbarVerticalEdge ToolbarVerticalCompressionBehavior toolbarVerticalCompressionBehavior
  ToolbarItemVisibilityPriority visibilityPriority axisBehavior AxisBehavior ToolbarOverflowMenu topBarPinnedTrailing presentationPlacement backgroundExtensionEffect
  sceneAccessory CameraCaptureAccessory onAvailabilityChange ConcentricRectangle defaultTabBarPlacement
  UIArrangementViewController UISplitArrangement UIOverlayArrangement UIHingeInteraction UIVerticalBarBehavior verticalBarEdge UIVerticalBarCompressionBehavior
  UIBarButtonItemVisibilityPriority additionalOverflowItems pinnedTrailingGroup leadingItemGroups preferredVerticalBarBehavior preferredPlacement
  UIBackgroundExtensionView UICornerConfiguration UIWindowSceneActivationAction registerSceneAccessory UISceneAccessory LayoutRegion cornerAdaptation)

for fw in SwiftUICore SwiftUI UIKit UIKitCore AVKit AVFoundation; do
  for f in $(find "$SDK/System/Library/Frameworks/$fw.framework" -name '*.swiftinterface' 2>/dev/null); do
    arch=$(basename "$f" .swiftinterface)
    case "$arch" in arm64-apple-ios*-simulator|arm64-apple-ios*) ;; *) continue;; esac
    for s in "${SYMBOLS[@]}"; do
      hits=$(grep -n -E "\b$s\b" "$f" | head -400 || true)
      [ -n "$hits" ] && { printf '\n#### %s :: %s :: %s\n' "$fw" "$arch" "$s"; echo "$hits"; } >> "$OUT/$fw.grep.txt"
    done
  done
done

# Full declarations with availability: extract whole blocks around each hit (context 12 lines) for the core types.
for fw in SwiftUICore UIKit; do
  f=$(find "$SDK/System/Library/Frameworks/$fw.framework" -name 'arm64-apple-ios*.swiftinterface' | head -1)
  [ -z "$f" ] && continue
  for s in ArrangementView ReservedRegion DeviceHinge onHingeChange toolbarVerticalBehavior toolbarVerticalEdge UIArrangementViewController UIHingeInteraction verticalBarEdge; do
    grep -n -B4 -A24 -E "(struct|class|enum|func|var|extension) .*\b$s\b" "$f" > "$OUT/$fw.$s.swiftinterface.txt" 2>/dev/null || true
    [ -s "$OUT/$fw.$s.swiftinterface.txt" ] || rm -f "$OUT/$fw.$s.swiftinterface.txt"
  done
done

# ObjC headers for UIKit (UIKit's public API also ships as .h)
for h in UIArrangementViewController UIHingeInteraction UIView UIBarButtonItem UINavigationItem UIViewController UITraitCollection UISheetPresentationController; do
  src=$(find "$SDK/System/Library/Frameworks/UIKit.framework/Headers" -name "$h.h" | head -1)
  [ -n "$src" ] && grep -n -iE 'duo|hinge|reservedRegion|verticalBar|arrangement|axisBehavior|visibilityPriority|overflow|pinnedTrailing|preferredPlacement|cornerAdaptation|LayoutRegion' "$src" > "$OUT/UIKit.$h.h.txt" || true
  [ -s "$OUT/UIKit.$h.h.txt" ] || rm -f "$OUT/UIKit.$h.h.txt"
done

# DeviceHinge.Status cases and ToolbarVerticalEdge cases, which the docs pages omit.
f=$(find "$SDK/System/Library/Frameworks/SwiftUICore.framework" -name 'arm64-apple-ios*.swiftinterface' | head -1)
[ -n "$f" ] && { grep -n -A30 'struct Status' "$f" | grep -n -E 'static|Status' | head -60 > "$OUT/SwiftUICore.DeviceHinge.Status.txt"; grep -n -E 'ToolbarVerticalEdge|VerticalEdge' "$f" | head -40 > "$OUT/SwiftUICore.VerticalEdge.txt"; } || true

ls -la "$OUT"
echo "Now diff these against raw/apple-docs/api-*.md and record every mismatch in raw/sdk/DIFF.md"
