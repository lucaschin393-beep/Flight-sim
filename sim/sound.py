"""Procedurally generated crash sounds (no audio files): an explosion boom and a fire loop.

If no audio device is available everything quietly does nothing.
"""
import array
import math
import random

RATE = 22050


def _to_sound(pygame, samples):
    peak = max(max(samples), -min(samples), 1e-9)
    data = array.array("h", (int(max(-1.0, min(1.0, s / peak)) * 30000) for s in samples))
    return pygame.mixer.Sound(buffer=data.tobytes())


def make_boom(rng, seconds=3.0):
    """Sharp crack, a deep sub-bass thump and a rumbling tail."""
    n = int(RATE * seconds)
    out, low = [], 0.0
    for i in range(n):
        t = i / RATE
        low += (rng.uniform(-1, 1) - low) * (0.02 + 0.10 * math.exp(-t * 2.0))   # darkening noise
        rumble = low * math.exp(-t / 0.9) * 5.0
        thump = math.sin(2 * math.pi * (28 * t + 38 * (1 - math.exp(-t * 3)) / 3)) * math.exp(-t / 0.7)
        crack = rng.uniform(-1, 1) * math.exp(-t / 0.035) * 1.4
        out.append(rumble + thump * 1.2 + crack)
    fade = int(RATE * 0.25)
    for i in range(fade):
        out[n - 1 - i] *= i / fade
    return out


def make_fire(rng, seconds=3.0):
    """Roaring flames with random crackles, built to loop without a click."""
    n, tail = int(RATE * seconds), int(RATE * 0.2)
    out, low, rumble = [], 0.0, 0.0
    pops = []                                               # (start sample, length, amplitude)
    for i in range(n + tail):
        if rng.random() < 0.0009:
            pops.append((i, rng.randint(80, 500), rng.uniform(0.3, 1.0)))
    for i in range(n + tail):
        low += (rng.uniform(-1, 1) - low) * 0.25
        rumble += (rng.uniform(-1, 1) - rumble) * 0.015
        out.append(low * 0.18 + rumble * 4.0 * (0.8 + 0.2 * math.sin(i / RATE * 7.0)))
    for start, length, amp in pops:
        for k in range(min(length, n + tail - start)):
            out[start + k] += rng.uniform(-1, 1) * amp * (1 - k / length) ** 2
    for i in range(tail):                                   # crossfade the end into the start
        k = i / tail
        out[i] = out[i] * k + out[n + i] * (1 - k)
    return out[:n]


def make_jet(rng, seconds=2.0):
    """Afterburner roar: broadband rushing noise with a deep rumble and a slight flutter."""
    n, tail = int(RATE * seconds), int(RATE * 0.2)
    out, hiss, mid, rumble = [], 0.0, 0.0, 0.0
    for i in range(n + tail):
        t = i / RATE
        white = rng.uniform(-1, 1)
        hiss += (white - hiss) * 0.55
        mid += (white - mid) * 0.12
        rumble += (white - rumble) * 0.02
        flutter = 1.0 + 0.18 * math.sin(2 * math.pi * 37 * t) + 0.12 * math.sin(2 * math.pi * 11 * t + 1.3)
        out.append((hiss * 0.45 + mid * 1.3 + rumble * 5.5) * flutter)
    for i in range(tail):                                   # loop seam
        k = i / tail
        out[i] = out[i] * k + out[n + i] * (1 - k)
    return out[:n]


def make_thunk(rng, seconds=0.45):
    """Heavy mechanical clunk: a falling low thump plus a short metallic click."""
    n = int(RATE * seconds)
    out = []
    for i in range(n):
        t = i / RATE
        thump = math.sin(2 * math.pi * (95 * t - 90 * t * t)) * math.exp(-t / 0.09)
        click = rng.uniform(-1, 1) * math.exp(-t / 0.008) * 0.9
        ring = math.sin(2 * math.pi * 420 * t) * math.exp(-t / 0.05) * 0.25
        out.append(thump + click + ring)
    return out


def make_snap(rng, seconds=0.8):
    """A wing tearing off: a sharp crack and a rattle of falling parts."""
    n = int(RATE * seconds)
    out, hiss = [], 0.0
    for i in range(n):
        t = i / RATE
        hiss += (rng.uniform(-1, 1) - hiss) * 0.4
        crack = rng.uniform(-1, 1) * math.exp(-t / 0.02) * 1.5
        rattle = hiss * math.exp(-t / 0.3) * (0.6 if (i // 400) % 3 else 0.2)
        out.append(crack + rattle)
    return out


def make_gear_motor(rng, seconds=1.0):
    """Gear in motion: a low mechanical grind with pump pulses, no tonal whine (loops seamlessly)."""
    n = int(RATE * seconds)
    sin = _SIN
    out, low, mid = [], 0.0, 0.0
    for i in range(n):
        w = rng.uniform(-1, 1)
        low += (w - low) * 0.03
        mid += (w - mid) * 0.15
        pulse = 1.0 + 0.5 * sin[(14 * i) % RATE]
        out.append((low * 4.0 + mid * 0.6) * pulse)
    tail = 200                                           # tiny fade so the loop joins without a click
    for i in range(tail):
        out[i] *= i / tail
        out[n - 1 - i] *= i / tail
    return out


def make_roll(rng, seconds=1.0):
    """Tyres rumbling along tarmac: low noise with regular bumps (runway joints)."""
    n, tail = int(RATE * seconds), int(RATE * 0.1)
    noise, a, b = [], 0.0, 0.0
    for _ in range(n + tail):
        w = rng.uniform(-1, 1)
        a += (w - a) * 0.08
        b += (w - b) * 0.6
        noise.append((a, b))
    for i in range(tail):
        k = i / tail
        noise[i] = tuple(x * k + y * (1 - k) for x, y in zip(noise[i], noise[n + i]))
    sin = _SIN
    return [noise[i][0] * 3.0 + noise[i][1] * 0.4 + 0.5 * max(0.0, sin[(9 * i) % RATE]) ** 6
            for i in range(n)]


def make_touchdown(rng, seconds=0.9):
    """Wheels meeting the runway: a thump and a short burst of tyre noise."""
    n = int(RATE * seconds)
    sin = _SIN
    out, hiss = [], 0.0
    for i in range(n):
        t = i / RATE
        hiss += (rng.uniform(-1, 1) - hiss) * 0.3
        thump = math.sin(2 * math.pi * (70 * t - 60 * t * t)) * math.exp(-t / 0.12) * 1.3
        chirp = hiss * 0.8 * math.exp(-t / 0.22) * min(1.0, t / 0.01)
        out.append(thump + chirp * 0.7)
    return out


# Engine sound profiles: three looped layers (idle / cruise / full power) are cross-faded by throttle.
# "piston": harmonics of a firing frequency (Hz); "turbine": rushing noise (a whine tone can be
# added with `whine` in Hz, but every profile currently has it off).
ENGINES = {
    "prop": dict(kind="piston", gain=0.30, layers=(
        dict(f=30, harm=(1.0, 0.7, 0.5, 0.35, 0.2), noise=0.10, trem=(7, 0.15)),
        dict(f=52, harm=(1.0, 0.75, 0.55, 0.4, 0.25), noise=0.14, trem=(7, 0.10)),
        dict(f=84, harm=(1.0, 0.8, 0.6, 0.45, 0.3), noise=0.20, trem=(11, 0.08)))),
    "radial": dict(kind="piston", gain=0.32, layers=(
        dict(f=20, harm=(0.6, 1.0, 0.8, 0.5, 0.3), noise=0.18, trem=(5, 0.35)),
        dict(f=36, harm=(0.6, 1.0, 0.85, 0.55, 0.3), noise=0.22, trem=(6, 0.25)),
        dict(f=58, harm=(0.6, 1.0, 0.9, 0.6, 0.35), noise=0.28, trem=(9, 0.18)))),
    "jet": dict(kind="turbine", gain=0.26, layers=(
        dict(whine=0, hiss=0.15, rumble=0.9),
        dict(whine=0, hiss=0.35, rumble=0.9),
        dict(whine=0, hiss=0.7, rumble=1.0))),
    "airliner": dict(kind="turbine", gain=0.24, layers=(
        dict(whine=0, hiss=0.10, rumble=1.0),        # no whine: just a deep rumble and rushing air
        dict(whine=0, hiss=0.22, rumble=1.0),
        dict(whine=0, hiss=0.38, rumble=1.0))),
}
LAYER_GAIN = (0.6, 0.8, 1.0)


_SIN = [math.sin(2 * math.pi * j / RATE) for j in range(RATE)]     # one second of a 1 Hz sine


def make_engine_layer(rng, kind, params, seconds=1.0):
    """One seamless loop. Tones use whole-Hz frequencies over a whole-second loop, so they join
    perfectly; the noise part is cross-faded at the seam."""
    n, tail = int(RATE * seconds), int(RATE * 0.1)
    noise, a, b = [], 0.0, 0.0
    lp1, lp2 = (0.35, 0.02) if kind == "piston" else (0.5, 0.03)
    for _ in range(n + tail):
        white = rng.uniform(-1, 1)
        a += (white - a) * lp1                  # hissy part
        b += (white - b) * lp2                  # rumbly part
        noise.append((a, b))
    for i in range(tail):
        k = i / tail
        noise[i] = tuple(x * k + y * (1 - k) for x, y in zip(noise[i], noise[n + i]))
    out, sin = [], _SIN
    for i in range(n):
        if kind == "piston":
            f, (tf, td) = params["f"], params["trem"]
            tone = sum(h * sin[(f * (k + 1) * i) % RATE] for k, h in enumerate(params["harm"]))
            tone *= 1.0 + td * sin[(tf * i) % RATE]
            out.append(tone * 0.5 + noise[i][0] * params["noise"] * 1.5 + noise[i][1] * params["noise"] * 3)
        else:
            w = params["whine"]
            tone = (0.22 * sin[(w * i) % RATE] + 0.09 * sin[(2 * w * i) % RATE]) if w else 0.0
            out.append(tone + noise[i][0] * params["hiss"] + noise[i][1] * params["rumble"] * 4.0)
    return out


class Sounds:
    def __init__(self):
        self.ok = False
        self.muted = False
        self._fire = None
        try:
            import pygame
            pygame.mixer.init(frequency=RATE, size=-16, channels=1, buffer=512)
            pygame.mixer.set_num_channels(16)
            rng = random.Random(5)
            self._pg = pygame
            self._boom = _to_sound(pygame, make_boom(rng))
            self._fire_sound = _to_sound(pygame, make_fire(rng))
            self._jet_sound = _to_sound(pygame, make_jet(rng))
            self._fire_channel = None
            self._jet_channel = None
            self._jet_level = 0.0
            self._engines = {}                 # profile name -> three layer Sounds (made on first use)
            self._engine_name = None
            self._engine_channels = []
            self._engine_levels = [0.0, 0.0, 0.0]
            self._cache = {}                   # short effects, made the first time they are needed
            self._loops = {}                   # name -> channel of a running loop (gear motor, tyres)
            self._loop_levels = {}
            self._prev_gear = None
            self.ok = True
        except Exception:                                    # no audio device, mixer missing, ...
            self.ok = False

    def crash(self, intensity=1.0):
        """Boom now, and a crackling fire loop that fades out as the wreck burns down."""
        if not self.ok:
            return
        self._boom.set_volume(0 if self.muted else max(0.3, min(1.0, intensity)))
        self._boom.play()
        self._fire_channel = self._fire_sound.play(loops=-1)
        self.fire_level(0.0)

    def fire_level(self, level):
        """0..1 loudness of the fire."""
        if self.ok and self._fire_channel is not None:
            self._fire_channel.set_volume(0.0 if self.muted else max(0.0, min(1.0, level)) * 0.7)

    def afterburner(self, power, dt):
        """Jet roar following the afterburner flame: `power` 0 (silent) .. 1 (full), eased over time."""
        if not self.ok:
            return
        self._jet_level += (power - self._jet_level) * min(1.0, 4.0 * dt)
        audible = self._jet_level > 0.01 and not self.muted
        if audible and (self._jet_channel is None or not self._jet_channel.get_busy()):
            self._jet_channel = self._jet_sound.play(loops=-1)
        if self._jet_channel is not None:
            self._jet_channel.set_volume(self._jet_level * 0.22 if audible else 0.0)

    def engine(self, name, throttle, dt, quiet=False):
        """Engine note for the current aircraft; pitch and loudness follow the throttle by
        cross-fading idle / cruise / full-power loops."""
        if not self.ok or self.muted or name is None:
            return
        if name != self._engine_name or not self._engine_channels:
            for ch in self._engine_channels:
                ch.stop()
            if name not in self._engines:
                prof = ENGINES[name]
                rng = random.Random(sum(map(ord, name)))
                self._engines[name] = [_to_sound(self._pg, make_engine_layer(rng, prof["kind"], p))
                                       for p in prof["layers"]]
            self._engine_name = name
            self._engine_levels = [0.0, 0.0, 0.0]
            self._engine_channels = [snd.play(loops=-1) for snd in self._engines[name]]
        t = max(0.0, min(1.0, throttle))
        weights = (max(0.0, 1.0 - t / 0.5), max(0.0, 1.0 - abs(t - 0.5) / 0.5), max(0.0, (t - 0.5) / 0.5))
        gain = 0.0 if quiet else ENGINES[name]["gain"]
        for i, ch in enumerate(self._engine_channels):
            target = weights[i] * LAYER_GAIN[i] * gain
            self._engine_levels[i] += (target - self._engine_levels[i]) * min(1.0, 5.0 * dt)
            ch.set_volume(self._engine_levels[i])

    def _sound(self, name, factory):
        if name not in self._cache:
            self._cache[name] = _to_sound(self._pg, factory(random.Random(sum(map(ord, name)))))
        return self._cache[name]

    def _loop(self, name, factory, target, dt, rate=8.0):
        """Keep looped effect `name` at eased volume `target`; it only runs while audible."""
        level = self._loop_levels.get(name, 0.0)
        level += (target - level) * min(1.0, rate * dt)
        self._loop_levels[name] = level
        channel = self._loops.get(name)
        if level > 0.01 and not self.muted:
            if channel is None or not channel.get_busy():
                channel = self._loops[name] = self._sound(name, factory).play(loops=-1)
            channel.set_volume(level)
        elif channel is not None:
            channel.stop()
            self._loops[name] = None

    def gear(self, gear, dt, quiet=False):
        """Mechanical grind while the gear moves, and a clunk when it locks down or tucks up."""
        if not self.ok or self.muted:
            return
        prev, self._prev_gear = self._prev_gear, gear
        moving = 0.0 < gear < 1.0 and prev is not None and gear != prev
        self._loop("gear_motor", make_gear_motor, 0.0 if quiet or not moving else 0.22, dt)
        if prev is not None and not quiet:
            if prev < 1.0 <= gear or (prev > 0.0 and gear <= 0.0):
                snd = self._sound("gear_thunk", make_thunk)
                snd.set_volume(0.8 if gear >= 1.0 else 0.6)
                snd.play()

    def wheels(self, on_ground, speed, dt, quiet=False):
        """Tyre rumble that grows with ground speed."""
        if not self.ok or self.muted:
            return
        rolling = on_ground and not quiet
        self._loop("wheel_roll", make_roll, min(speed / 45.0, 1.0) * 0.45 if rolling else 0.0, dt)

    def wing_snap(self):
        if self.ok and not self.muted:
            snd = self._sound("wing_snap", make_snap)
            snd.set_volume(0.9)
            snd.play()

    def touchdown(self, sink_rate=1.0):
        """Thump and tyre noise on a safe landing; a firmer landing is louder."""
        if self.ok and not self.muted:
            snd = self._sound("touchdown", make_touchdown)
            snd.set_volume(max(0.35, min(1.0, 0.35 + sink_rate / 6.0)))
            snd.play()

    def stop(self):
        if self.ok:
            self._pg.mixer.stop()
            self._fire_channel = None
            self._jet_channel = None
            self._jet_level = 0.0

    def pause(self, paused):
        if self.ok:
            (self._pg.mixer.pause if paused else self._pg.mixer.unpause)()

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted and self.ok:
            self._pg.mixer.stop()
            self._fire_channel = None
            self._jet_channel = None
            self._engine_channels, self._engine_name = [], None
            self._loops, self._loop_levels = {}, {}
        return self.muted
