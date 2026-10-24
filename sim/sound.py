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


class Sounds:
    def __init__(self):
        self.ok = False
        self.muted = False
        self._fire = None
        try:
            import pygame
            pygame.mixer.init(frequency=RATE, size=-16, channels=1, buffer=512)
            rng = random.Random(5)
            self._pg = pygame
            self._boom = _to_sound(pygame, make_boom(rng))
            self._fire_sound = _to_sound(pygame, make_fire(rng))
            self._jet_sound = _to_sound(pygame, make_jet(rng))
            self._fire_channel = None
            self._jet_channel = None
            self._jet_level = 0.0
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
            self._jet_channel.set_volume(self._jet_level * 0.6 if audible else 0.0)

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
        return self.muted
