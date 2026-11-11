"""Synthesizes the Battle Between Bugs sound set as 16-bit mono 44.1 kHz WAVs.
Usage: python gen_sfx.py <out_dir> [name ...]   (no names = all)
Loops (engine, music) are cut on whole cycles so they repeat without clicks."""
import sys, os, wave
import numpy as np

SR = 44100
rng = np.random.default_rng(7)


def t(d):
    return np.arange(int(SR * d)) / SR


def env(n, a=0.005, r=None, curve=3.0):
    """attack then exponential-ish decay over n samples"""
    x = np.linspace(0, 1, n)
    at = max(1, int(a * SR))
    e = np.clip(np.arange(n) / at, 0, 1)
    if r is None:
        return e * (1 - x) ** curve
    rel = np.clip((n - np.arange(n)) / max(1, int(r * SR)), 0, 1)
    return e * rel


def noise(n):
    return rng.uniform(-1, 1, n)


def lp(x, k):
    """one-pole low-pass, k in (0,1]: smaller = darker"""
    y = np.empty_like(x)
    s = 0.0
    for i, v in enumerate(x):
        s += k * (v - s)
        y[i] = s
    return y


def hp(x, k):
    return x - lp(x, k)


def sweep(f0, f1, d, shape="sin"):
    n = int(SR * d)
    f = np.geomspace(f0, f1, n)
    ph = 2 * np.pi * np.cumsum(f) / SR
    if shape == "saw":
        return 2 * ((ph / (2 * np.pi)) % 1) - 1
    if shape == "sq":
        return np.sign(np.sin(ph))
    if shape == "tri":
        return 2 * np.abs(2 * ((ph / (2 * np.pi)) % 1) - 1) - 1
    return np.sin(ph)


def tone(f, d, shape="sin"):
    return sweep(f, f * 1.0000001, d, shape)


def mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p
    return out


def at(x, sec, total):
    out = np.zeros(int(SR * total))
    s = int(sec * SR)
    e = min(len(out), s + len(x))
    out[s:e] += x[:e - s]
    return out


def norm(x, peak=0.89):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def fade_edges(x, ms=4):
    n = int(SR * ms / 1000)
    x = x.copy()
    x[:n] *= np.linspace(0, 1, n)
    x[-n:] *= np.linspace(1, 0, n)
    return x


# ---------------------------------------------------------------- UI
def ui_click():
    d = 0.09
    return norm(mix(tone(1400, d, "tri") * env(int(SR * d), 0.001, curve=6), tone(2800, d) * 0.3 * env(int(SR * d), 0.001, curve=9)), 0.7)


def ui_hover():
    d = 0.05
    return norm(tone(900, d, "tri") * env(int(SR * d), 0.001, curve=5), 0.35)


def ui_tick():
    d = 0.045
    return norm(mix(hp(noise(int(SR * d)), 0.3) * env(int(SR * d), 0.0005, curve=10), tone(2200, d) * env(int(SR * d), 0.0005, curve=12)), 0.6)


def ui_reveal():
    total = 1.3
    notes = [523.25, 659.25, 783.99, 1046.5]
    out = np.zeros(int(SR * total))
    for i, f in enumerate(notes):
        d = 0.9 if i == 3 else 0.22
        n = mix(tone(f, d, "sq") * 0.35, tone(f * 2, d, "tri") * 0.4, tone(f * 0.5, d) * 0.3) * env(int(SR * d), 0.004, curve=2)
        out += at(n, i * 0.1, total)
    sparkle = sweep(3000, 6000, 0.6) * env(int(SR * 0.6), 0.01, curve=3) * 0.15
    out += at(sparkle, 0.3, total)
    return norm(out, 0.8)


def count_beep():
    d = 0.22
    return norm(mix(tone(660, d, "sq") * 0.5, tone(660, d)) * env(int(SR * d), 0.003, 0.06), 0.7)


def count_go():
    d = 0.75
    x = mix(tone(988, d, "sq") * 0.4, tone(1318.5, d, "sq") * 0.3, tone(494, d, "saw") * 0.25)
    return norm(lp(x, 0.35) * env(int(SR * d), 0.004, 0.35), 0.85)


def time_warn():
    d = 0.12
    return norm(tone(1760, d, "sq") * env(int(SR * d), 0.002, 0.04), 0.5)


def match_end():
    d = 1.6
    x = mix(sweep(440, 330, d, "saw"), sweep(554, 415, d, "saw") * 0.8, sweep(659, 494, d, "saw") * 0.6)
    return norm(lp(x, 0.12) * env(int(SR * d), 0.02, 0.6), 0.85)


# ---------------------------------------------------------------- combat
def hit():
    d = 0.35
    n = int(SR * d)
    thud = sweep(160, 45, d) * env(n, 0.001, curve=5)
    crunch = lp(noise(n), 0.25) * env(n, 0.0005, curve=9)
    clank = mix(tone(820, 0.2, "sq"), tone(1230, 0.2, "sq") * 0.6) * env(int(SR * 0.2), 0.0005, curve=8) * 0.25
    return norm(mix(thud, crunch * 0.8, clank), 0.9)


def hurt():
    d = 0.4
    n = int(SR * d)
    x = mix(sweep(120, 40, d) * env(n, 0.001, curve=4), lp(noise(n), 0.08) * env(n, 0.001, curve=6) * 0.7)
    return norm(x, 0.95)


def explode():
    d = 1.8
    n = int(SR * d)
    boom = sweep(90, 28, d) * env(n, 0.002, curve=3)
    rumble = lp(noise(n), 0.03) * env(n, 0.003, curve=2) * 2.0
    crack = hp(noise(n), 0.4) * env(n, 0.0005, curve=14) * 0.8
    debris = np.zeros(n)
    for i in range(14):
        s = rng.uniform(0.15, 1.1)
        dd = 0.06
        debris += at(hp(noise(int(SR * dd)), 0.5) * env(int(SR * dd), 0.0005, curve=6) * rng.uniform(0.1, 0.3), s, d)[:n]
    return norm(mix(boom, rumble, crack, debris), 0.95)


def kill_ding():
    d = 0.7
    n = int(SR * d)
    x = mix(tone(1568, d) * 0.6, tone(2093, d) * 0.5, tone(3136, d) * 0.2)
    x2 = at(mix(tone(2093, 0.5), tone(2637, 0.5) * 0.6) * env(int(SR * 0.5), 0.002, curve=3), 0.09, d)
    return norm(x * env(n, 0.002, curve=3) + x2, 0.8)


# ---------------------------------------------------------------- powers
def whoosh(d=0.7, f0=300, f1=2400, k=0.15):
    n = int(SR * d)
    x = noise(n)
    out = np.empty(n)
    s = 0.0
    ks = np.geomspace(0.02, k, n)
    for i in range(n):
        s += ks[i] * (x[i] - s)
        out[i] = s
    bell = np.sin(np.linspace(0, np.pi, n)) ** 1.5
    return out * bell


def dash():
    d = 0.8
    x = mix(whoosh(d, k=0.35) * 2.0, sweep(180, 900, d, "saw") * 0.15 * np.sin(np.linspace(0, np.pi, int(SR * d))))
    return norm(x, 0.9)


def power_up():
    d = 0.6
    n = int(SR * d)
    x = mix(sweep(200, 1600, d, "sq") * 0.3, sweep(400, 3200, d) * 0.4) * env(n, 0.01, curve=1.5)
    return norm(lp(x, 0.3), 0.75)


def web_shot():
    d = 0.35
    n = int(SR * d)
    thwip = sweep(2600, 500, 0.18, "tri") * env(int(SR * 0.18), 0.001, curve=3)
    hiss = hp(noise(n), 0.5) * env(n, 0.001, curve=5) * 0.4
    return norm(mix(thwip, hiss), 0.8)


def bite():
    d = 0.3
    n = int(SR * d)
    snap = hp(noise(int(SR * 0.05)), 0.6) * env(int(SR * 0.05), 0.0003, curve=6)
    crunch = lp(noise(n), 0.3) * env(n, 0.001, curve=7) * 0.8
    gulp = sweep(300, 120, d) * env(n, 0.01, curve=4) * 0.5
    return norm(mix(snap, at(snap, 0.07, d), crunch, gulp), 0.85)


def storm():
    d = 1.4
    n = int(SR * d)
    x = mix(whoosh(d, k=0.2) * 1.5, lp(noise(n), 0.05) * env(n, 0.05, curve=1.5), sweep(80, 160, d, "saw") * 0.15 * env(n, 0.1, curve=1))
    return norm(x, 0.85)


def shield():
    d = 1.0
    n = int(SR * d)
    sh = mix(*[tone(f, d) * (0.4 / (i + 1)) * (1 + 0.5 * np.sin(2 * np.pi * (6 + i) * t(d))) for i, f in enumerate([880, 1320, 1760, 2640])])
    rise = sweep(220, 880, 0.3, "tri") * env(int(SR * 0.3), 0.005, curve=1) * 0.5
    return norm(mix(sh * env(n, 0.03, curve=2), rise), 0.75)


def honey_bomb():
    d = 0.5
    n = int(SR * d)
    bloop = sweep(140, 520, 0.22) * env(int(SR * 0.22), 0.002, curve=2)
    pop = lp(noise(int(SR * 0.05)), 0.4) * env(int(SR * 0.05), 0.0005, curve=5)
    whiz = sweep(900, 400, d, "tri") * env(n, 0.05, curve=3) * 0.2
    return norm(mix(pop, bloop, whiz), 0.85)


def splat():
    d = 0.6
    n = int(SR * d)
    x = mix(lp(noise(n), 0.12) * env(n, 0.002, curve=5), sweep(220, 70, d) * env(n, 0.002, curve=4) * 0.7)
    return norm(x, 0.85)


def acid():
    d = 0.9
    n = int(SR * d)
    launch = sweep(500, 140, 0.25, "saw") * env(int(SR * 0.25), 0.002, curve=3) * 0.5
    sizzle = hp(noise(n), 0.55) * env(n, 0.05, curve=1.5) * (0.6 + 0.4 * np.sin(2 * np.pi * 23 * t(d)))
    return norm(lp(mix(launch, sizzle * 0.6), 0.6), 0.8)


def swarm():
    d = 1.6
    n = int(SR * d)
    x = np.zeros(n)
    for i in range(7):
        f = rng.uniform(180, 320)
        vib = 1 + 0.05 * np.sin(2 * np.pi * rng.uniform(4, 9) * t(d))
        ph = 2 * np.pi * np.cumsum(f * vib) / SR
        x += (2 * ((ph / (2 * np.pi)) % 1) - 1) * rng.uniform(0.5, 1)
    return norm(lp(x, 0.2) * np.sin(np.linspace(0, np.pi, n)) ** 0.6, 0.7)


def armor():
    d = 0.7
    n = int(SR * d)
    clang = mix(tone(310, d, "sq") * 0.3, tone(465, d, "sq") * 0.2, tone(930, d) * 0.3) * env(n, 0.001, curve=4)
    return norm(mix(lp(clang, 0.3), power_up()[:n] * 0.5), 0.8)


# ---------------------------------------------------------------- loops
def engine_loop():
    # 2 s loop around a 55 Hz fundamental (pitched up/down by speed in game)
    d = 2.0
    tt = t(d)
    f = 55.0
    ph = 2 * np.pi * f * tt
    x = (np.sin(ph) + 0.6 * np.sin(2 * ph + 0.3) + 0.35 * np.sin(3 * ph) + 0.2 * np.sin(4 * ph + 1.1)
         + 0.25 * (2 * ((ph / (2 * np.pi)) % 1) - 1))
    puls = 1 + 0.25 * np.sin(2 * np.pi * 27.5 * tt)
    grit = lp(noise(len(tt)), 0.1) * 0.25
    return norm(lp(x * puls + grit, 0.25), 0.6)


def music(bpm, root, minor, d_bars=8, menu=False):
    beat = 60.0 / bpm
    bar = beat * 4
    total = bar * d_bars
    n = int(SR * total)
    out = np.zeros(n)
    scale = [0, 2, 3, 5, 7, 8, 10] if minor else [0, 2, 4, 5, 7, 9, 11]
    prog = [0, 5, 3, 4] if minor else [0, 3, 4, 0]

    def hz(semi):
        return root * 2 ** (semi / 12)

    for b in range(d_bars):
        deg = prog[b % 4]
        chord = [scale[deg % 7], scale[(deg + 2) % 7] + (12 if deg + 2 >= 7 else 0), scale[(deg + 4) % 7] + (12 if deg + 4 >= 7 else 0)]
        # bass on 8ths
        for k in range(8):
            dd = beat / 2 * 0.9
            semi = chord[0] - 12 + (12 if k % 2 else 0)
            note = tone(hz(semi), dd, "saw") * env(int(SR * dd), 0.003, curve=2) * 0.35
            out += at(lp(note, 0.15), b * bar + k * beat / 2, total)[:n]
        # chord pad / arp
        if menu:
            dd = bar
            pad = mix(*[tone(hz(c), dd, "tri") * 0.12 for c in chord]) * env(int(SR * dd), 0.15, 0.4)
            out += at(pad, b * bar, total)[:n]
            for k in range(8):
                dd2 = beat / 2
                c = chord[k % 3] + 12
                out += at(tone(hz(c), dd2, "tri") * env(int(SR * dd2), 0.002, curve=4) * 0.12, b * bar + k * dd2, total)[:n]
        else:
            for k in range(16):
                dd2 = beat / 4
                c = chord[(k * 2) % 3] + 12 + (12 if k % 4 == 3 else 0)
                out += at(lp(tone(hz(c), dd2 * 0.8, "sq"), 0.3) * env(int(SR * dd2 * 0.8), 0.002, curve=3) * 0.09, b * bar + k * dd2, total)[:n]
        # drums
        for k in range(4):
            kick = sweep(150, 45, 0.18) * env(int(SR * 0.18), 0.001, curve=4) * (0.55 if not menu else 0.35)
            out += at(kick, b * bar + k * beat, total)[:n]
            if k % 2 == 1:
                sn = mix(hp(noise(int(SR * 0.15)), 0.3) * 0.4, tone(190, 0.15) * 0.25) * env(int(SR * 0.15), 0.001, curve=5) * (1.0 if not menu else 0.5)
                out += at(sn, b * bar + k * beat, total)[:n]
            for h in range(2 if menu else 4):
                step = beat / (2 if menu else 4)
                hh = hp(noise(int(SR * 0.03)), 0.7) * env(int(SR * 0.03), 0.0005, curve=6) * 0.12
                out += at(hh, b * bar + k * beat + h * step, total)[:n]
    return norm(out, 0.75)


SOUNDS = {
    "SFX_UI_Click": ui_click, "SFX_UI_Hover": ui_hover, "SFX_UI_Tick": ui_tick, "SFX_UI_Reveal": ui_reveal,
    "SFX_Count_Beep": count_beep, "SFX_Count_Go": count_go, "SFX_Time_Warn": time_warn, "SFX_Match_End": match_end,
    "SFX_Hit": hit, "SFX_Hurt": hurt, "SFX_Explode": explode, "SFX_Kill_Ding": kill_ding,
    "SFX_Dash": dash, "SFX_Power": power_up, "SFX_Web_Shot": web_shot, "SFX_Bite": bite, "SFX_Web_Storm": storm,
    "SFX_Shield": shield, "SFX_Honey_Bomb": honey_bomb, "SFX_Splat": splat, "SFX_Acid": acid, "SFX_Swarm": swarm,
    "SFX_Armor": armor, "SFX_Engine_Loop": engine_loop,
    "MUS_Menu": lambda: music(96, 196.0, False, 8, True),
    "MUS_Battle": lambda: music(140, 110.0, True, 8, False),
}


def write(path, x):
    x = np.clip(x, -1, 1)
    data = (x * 32767).astype("<i2").tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data)


if __name__ == "__main__":
    out = sys.argv[1]
    names = sys.argv[2:] or list(SOUNDS)
    os.makedirs(out, exist_ok=True)
    for nm in names:
        x = SOUNDS[nm]()
        if not nm.startswith("MUS") and nm != "SFX_Engine_Loop":
            x = fade_edges(x)
        write(os.path.join(out, nm + ".wav"), x)
        print(nm, round(len(x) / SR, 2), "s")
