# METRICS-NOTES — Step 2 probe run, 2026-10-25

iPhone Duo simulator, iOS 27.1 runtime 24A94425, Xcode 27.1 (27A9275). DuoProbe metrics schema 2.
Poses driven by `duo.py` at commit `60cdda2` (fold + orientation through the simulator's hinge HID event).
Source: `raw/metrics.jsonl` (72 samples), summary `raw/metrics.json`, screenshots `raw/apple-apps/_probe/`.
Each pose's figures are the settled end of the burst right after launch (see `scripts/metrics-to-poses.py`).

## Per pose

Window = scene bounds. Insets = the key window's `safeAreaInsets` (no app bars). Frames in points, view coordinates.

| Pose | duo.py | Window | Insets | Classes h/v | Vertical bar | Division | Occlusions (active) | Hinge read back |
|---|---|---|---|---|---|---|---|---|
| closed | close, sideways | 466×678 | trailing 84, bottom 34 | compact/regular | trailing | none | camera 37×37 at (400,29); system column 84×174 at (382,0) | 0° closed |
| closed-sideways | close, upright | 678×466 | leading 84, bottom 34 | **compact/compact** | leading | none | camera 37×37 at (29,29); column 84×82 at (0,0) | 0° closed |
| book | book (128°), sideways | 951×669 | trailing 84, bottom 34 | regular/regular | trailing | x 455.5, 40 wide, **active** | clock column 84×124 at (867,0); inner camera 58×37 inactive | 125.9° partiallyOpen |
| laptop | laptop (110°), upright | 669×951 | top 82, bottom 34 | regular/regular | none | y 455.5, 40 tall, **active** | status 144×82 at (525,0); inner camera 37×58 inactive | 108.9° partiallyOpen |
| tent | laptop (110°), landscape-right | 669×951 | top 82, bottom 34 | regular/regular | none | y 455.5, 40 tall, **active** | status 144×82 at (525,0); inner camera inactive, now at (611,677) | 108.9° partiallyOpen |
| flat-sideways | open, sideways | 951×669 | trailing 84, bottom 34 | regular/regular | trailing | x 455.5, inactive | clock column 84×124; inner camera inactive | 180° fullyOpen |
| flat-upright | open, upright | 669×951 | top 82, bottom 34 | regular/regular | none | y 455.5, inactive | status 144×82; inner camera inactive | (no hinge event in that launch) |

## The checks docs/history/MAC-PHASE.md asks for

- **Window and insets per pose:** table above.
- **First frame (seq 1):** no division and no occlusion regions in any pose; they appear within 0.1–0.3 s.
  Agrees with the community report (iphone-duo-probe) that `reservedRegions` is empty on first evaluation.
- **secondsToSettle** (launch to last sample of the first burst): 0.14–0.48 s; tent is the slowest (0.48 s).
- **Division:** frame 40 pt wide from 455.5 to 495.5 pt, centred on the display's middle (475.5 pt), 20 pt margin each side; active when part folded (book, laptop, tent), inactive when flat
  (frame still reported with `.includeInactive`), absent when closed.
- **Occlusions on the outer display:** the camera (37×37) and the system column, both active.
- **toolbarVerticalEdge:** `trailing` closed and open sideways, `leading` closed while turned, `nil` whenever the
  open phone stands upright (laptop, tent, flat upright).

## Against the community table (raw/complaints/README.md §B, duo.py SKILL.md)

Agree: every window size; every inset; the 40 pt fold frame starting at 455.5 pt; regions empty on the first evaluation;
bars vertical on the right (trailing) closed and open sideways, horizontal when upright; closed-and-turned uses the
camera side (leading here).

Disagree (small, likely margins): occlusion sizes run 4–10 pt larger than the community's chrome sizes:
clock column 84×124 (community 84×120), status cluster 144×82 (134×82), closed column 84×174 (84×170). Apple's docs
say an occlusion frame already includes its margins, which would explain it.

New here: tent; size classes per pose (closed-sideways is compact/compact, which DECISION-TABLE I3 had as `?`);
hinge read-back is quantized (128° set → 125.9°, 110° → 108.9°).

## Limits of this run

- Tent was driven, not set by hand: the manual attempt in Device Hub recorded the laptop pose again (same
  orientation and hinge), so it was discarded. The duo.py tent is laptop's fold turned hinge-up. That is our
  reading of the HIG's "standing on its edges"; Apple does not define the pose.
- Split-view half is a window state, not a pose; it can't be driven headless and is not measured here.
- One run, one simulator, no physical device.
