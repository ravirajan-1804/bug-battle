"""Procedural sounds for the race intro (WBP_RG_StartLights). Writes 16-bit mono WAVs to audio/ and,
with --install, copies them into Content/RacingGame/Audio, where the editor auto-imports them as SoundWaves.

  SW_RG_CountHit     3 / 2 / 1: sub boom + bright beep
  SW_RG_GoHit        GO!: bigger boom + higher, longer beep
  SW_RG_Whoosh       GO camera swoop
  SW_RG_Riser        tension riser under the "1" shot
  SW_RG_EngineIdle   grid idle rumble (3 and 2)
  SW_RG_EngineRev    two throttle blips (1)
  SW_RG_EngineLaunch launch roar that fades out (GO)
"""
import os, shutil, sys, wave
import numpy as np

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "audio")
CONTENT = os.path.join(HERE, "..", "..", "Content", "RacingGame", "Audio")
rng = np.random.default_rng(7)


def t_axis(sec):
    return np.arange(int(SR * sec)) / SR


def env(t, attack, decay):
    return np.minimum(1.0, t / max(attack, 1e-4)) * np.exp(-t / decay)


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def boom(sec, f0, f1, decay):
    t = t_axis(sec)
    f = f1 + (f0 - f1) * np.exp(-t / 0.12)              # pitch drops like a cinematic hit
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * env(t, 0.004, decay)
    crack = lowpass(rng.standard_normal(len(t)), 1800) * env(t, 0.001, 0.05) * 1.5
    return body + crack


def beep(sec, freq, total):
    t = t_axis(total)
    g = (t < sec) * np.minimum(1, (sec - t) / 0.03)
    x = sum(np.sin(2 * np.pi * freq * k * t) / k ** 1.5 for k in (1, 2, 3))
    return x * g * np.minimum(1, t / 0.005)


def pad(x, n):
    return np.pad(x, (0, max(0, n - len(x))))[:n]


def engine(rpm_curve, sec, cyl=4, grit=0.35):
    """rpm_curve(t) -> rpm; firing frequency = rpm/60 * cyl/2. Harmonic stack + firing-pulse noise."""
    t = t_axis(sec)
    rpm = rpm_curve(t)
    f = rpm / 60.0 * cyl / 2.0
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(k * ph + 0.3 * k) * (1.0 / k) for k in range(1, 10))
    pulse = (0.5 + 0.5 * np.cos(ph)) ** 4
    noise = lowpass(rng.standard_normal(len(t)), 2500) * pulse * grit
    load = 0.6 + 0.4 * (rpm - rpm.min()) / max(1.0, rpm.max() - rpm.min())
    return np.tanh(1.6 * (x * 0.35 + noise) * load)


def norm(x, peak=0.89):
    return x / max(1e-6, np.abs(x).max()) * peak


def fade(x, fin=0.01, fout=0.05):
    n = len(x)
    a, b = int(SR * fin), int(SR * fout)
    g = np.ones(n)
    g[:a] = np.linspace(0, 1, a)
    g[n - b:] = np.linspace(1, 0, b)
    return x * g


def sounds():
    s = {}
    n = int(SR * 1.4)
    s["SW_RG_CountHit"] = norm(pad(boom(1.4, 140, 42, 0.45), n) + 0.55 * beep(0.22, 880, 1.4))
    n = int(SR * 2.2)
    s["SW_RG_GoHit"] = norm(pad(boom(2.2, 170, 36, 0.8), n) * 1.2 + 0.6 * beep(0.6, 1320, 2.2))
    t = t_axis(1.0)
    sweep = 300 + 3200 * np.sin(np.pi * np.clip(t / 0.9, 0, 1)) ** 2
    raw = rng.standard_normal(len(t))
    a = np.exp(-2 * np.pi * sweep / SR)          # time-varying one-pole low-pass
    acc, y = 0.0, np.empty(len(t))
    for i, v in enumerate(raw):
        acc = (1 - a[i]) * v + a[i] * acc
        y[i] = acc
    s["SW_RG_Whoosh"] = norm(fade(y * np.sin(np.pi * np.clip(t / 0.95, 0, 1)) ** 1.5, 0.01, 0.08), 0.8)
    t = t_axis(1.6)
    f = 110 * 2 ** (t / 1.6 * 2.0)
    ph = 2 * np.pi * np.cumsum(f) / SR
    riser = (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.3 * lowpass(rng.standard_normal(len(t)), 4000)) * (t / 1.6) ** 1.5
    s["SW_RG_Riser"] = norm(fade(riser, 0.02, 0.03), 0.7)
    idle = lambda t: 950 + 60 * np.sin(2 * np.pi * 1.3 * t) + 40 * np.sin(2 * np.pi * 3.1 * t)
    s["SW_RG_EngineIdle"] = norm(fade(engine(idle, 3.4, grit=0.45), 0.15, 0.25), 0.75)

    def rev(t):
        r = np.full_like(t, 1000.0)
        for t0, peak in ((0.1, 5200), (0.75, 7200)):
            up = np.clip((t - t0) / 0.18, 0, 1)
            down = np.exp(-np.clip(t - t0 - 0.18, 0, None) / 0.22)
            r += (peak - 1000) * up * np.where(t - t0 > 0.18, down, 1)
        return r
    s["SW_RG_EngineRev"] = norm(fade(engine(rev, 1.6), 0.02, 0.1), 0.85)
    launch = lambda t: 3000 + 4200 * (1 - np.exp(-t / 0.25)) - 1500 * np.clip(t - 0.9, 0, None) / 1.6
    x = engine(launch, 2.6, grit=0.5) * np.exp(-np.clip(t_axis(2.6) - 0.9, 0, None) / 0.6)
    s["SW_RG_EngineLaunch"] = norm(fade(x, 0.01, 0.2), 0.9)
    return s


def write(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, x in sounds().items():
        p = os.path.join(OUT, name + ".wav")
        write(p, x)
        print("%-20s %.2f s" % (name, len(x) / SR))
        if "--install" in sys.argv:
            os.makedirs(CONTENT, exist_ok=True)
            shutil.copy(p, os.path.join(CONTENT, name + ".wav"))
