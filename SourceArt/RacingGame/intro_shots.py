"""Camera shots for the race intro (one per countdown number). Race direction on the grid is +X; pole car at
(-5424, 12426), grid slots back to x = -8622, road centre y = 12990, start arch at x = -5445.

Each shot: (start position, end position, look-at target, FOV). The camera moves start -> end with a
smoothstep over the shot and always aims at the target.
"""
import math

SHOTS = [
    # "3": low close-up from the left kerb, sliding along the asphalt towards the pole car's front corner
    ((-4150.0, 11930.0, 28.0), (-4700.0, 11990.0, 34.0), (-5900.0, 12700.0, 110.0), 72.0),
    # "2": high crane on the outside of the grid showing the cars, the arch and the garden around them
    ((-10200.0, 10150.0, 650.0), (-9100.0, 9950.0, 1350.0), (-6200.0, 13050.0, 150.0), 66.0),
    # "1": head-on telephoto at car height, in line with the pole column, pushing in on the grid
    ((-2600.0, 12560.0, 125.0), (-3300.0, 12520.0, 105.0), (-6200.0, 12900.0, 70.0), 36.0),
]
# GO (gen_racemanager.py): the camera arcs from the end of shot "1" to the player car's active camera, then
# the view blends into that camera.


def look(p, target):
    dx, dy, dz = (target[i] - p[i] for i in range(3))
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    return pitch, yaw


if __name__ == "__main__":
    for k, (a, b, tgt, fov) in enumerate(SHOTS):
        for tag, p in (("start", a), ("end", b)):
            print(3 - k, tag, p, "pitch %.1f yaw %.1f" % look(p, tgt), "fov", fov)
