"""Summarises the BPC_RGC_AutoPilot telemetry of the last Simulate run in Saved/Logs/Battle.log.

usage: python parse_autopilot.py [label]
Prints the lap time and, per corner, entry/min speed, worst slip angle, roll, how far the car ran
off the centreline, and how much of the corner the steering was at full lock.
"""
import os, re, sys
import numpy as np
from trackdef import Track, HALF_W

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Saved", "Logs", "Battle.log")
STRIDE = 4

rows, resets, frames = [], [], []
for line in open(LOG, encoding="utf-8", errors="ignore"):
    r = re.search(r"AP_RESET\|(\d+)", line)
    if r:
        resets.append((len(rows), int(r.group(1))))
        continue
    m = re.search(r"AP\|([-\d.|e]+)", line)
    if m:
        v = m.group(1).split("|")
        if len(v) == 10:
            rows.append([float(x) for x in v])
            f = re.match(r"\[[^]]*\]\[\s*(\d+)\]", line)
            frames.append(int(f.group(1)) if f else -1)
# keep only the last run (game time restarts)
start = 0
for k in range(1, len(rows)):
    if rows[k][0] < rows[k - 1][0]:
        start = k
resets = [i for k, i in resets if k >= start]
rows = np.array(rows[start:])
fr = np.array(frames[start:])
steps = (np.diff(fr) + 1000) % 1000          # log frame counter wraps at 1000
slow = (steps < 5).mean()                    # under 20 fps: physics runs in slow motion (max physics dt)
if not len(rows):
    sys.exit("no telemetry")
t, idx, kmh, cap, slip, roll, lat, steer, thr, brk = rows.T

# corners from the track definition (waypoint index ranges)
T = Track()
c = T.curv
hot = np.abs(c) > 1 / 5000
corners = []
i = 0
n = len(c)
while i < n:
    if hot[i]:
        j = i
        while j + 1 < n and hot[j + 1]:
            j += 1
        m = i + int(np.argmax(np.abs(c[i:j + 1])))
        corners.append((i // STRIDE, j // STRIDE, 1 / abs(c[m]), "R" if c[m] > 0 else "L"))
        i = j + 1
    else:
        i += 1

print("run: %.1f s of telemetry, %d samples, top speed %.0f km/h, mean %.0f km/h" % (t[-1] - t[0], len(t), kmh.max(), kmh.mean()))
# lap: first time idx wraps from the end back to the start
lap = None
for k in range(1, len(idx)):
    if idx[k - 1] > 350 and idx[k] < 40:
        lap = t[k] - t[0]
        break
if slow > 0.05:
    print("WARNING: %.0f%% of the run ran under 20 fps; the editor was throttled, rerun it" % (100 * slow))
print("lap (from waypoint 10): %s" % ("%.1f s" % lap if lap else "not completed"))
print("off track (|lat| > %.0f m): %d samples, spins (|slip| > 25 deg): %d samples, max |roll| %.1f deg"
      % (HALF_W / 100, int((np.abs(lat) > HALF_W / 100).sum()), int((np.abs(slip) > 25).sum()), np.abs(roll).max()))
drop = np.diff(kmh) < -25
hits = int((drop & (brk[1:] < 0.5) & (brk[:-1] < 0.5)).sum())
print("wall hits (lost > 25 km/h in 0.25 s without braking): %d" % hits)
print("resets after getting stuck: %d %s" % (len(resets), "(at waypoints %s)" % resets if resets else ""))
print("%-4s %-10s %6s %6s %6s %6s %6s %7s %6s" % ("#", "wp", "R m", "in", "min", "slip", "roll", "lat", "lock%"))
for k, (a, b, R, d) in enumerate(corners):
    sel = (idx >= a - 2) & (idx <= b + 3)
    if not sel.any():
        print("%-4d %3d-%-6d %5.0f%s   (not reached)" % (k + 1, a, b, R / 100, d))
        continue
    first = np.argmax(sel)
    print("%-4d %3d-%-6d %5.0f%s %6.0f %6.0f %6.1f %6.1f %7.1f %6.0f" % (
        k + 1, a, b, R / 100, d, kmh[first], kmh[sel].min(), np.abs(slip[sel]).max(), np.abs(roll[sel]).max(),
        lat[sel][np.argmax(np.abs(lat[sel]))], 100 * (np.abs(steer[sel]) > 0.98).mean()))
