# Airplane Simulator

A small 3D flight simulator in Python. Fly a light plane over a procedurally generated
landscape of mountains, buildings and trees, and switch between **1st person** (cockpit)
and **3rd person** (chase camera) views. Rendering is done in software with pygame, so
there is nothing to install besides pygame.

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip      # older pips can't find pygame's prebuilt wheels
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

## Controls

| Key | Action |
|-----|--------|
| `W` / `S` | Nose down / nose up |
| `A` / `D` | Bank (and turn) left / right |
| `Shift` / `Ctrl` (or `↑` / `↓`) | Throttle up / down |
| `B` (hold) | Air brake: heavy extra drag to shed speed |
| `G` | Landing gear up / down (starts up; can't be raised while on the ground) |
| `C` (or `1`–`4`) | Change aircraft |
| `Space` | Pause / resume |
| `P` | Change view (3rd person ⇄ 1st person) |
| `R` | Restart (after a safe landing: carry on from where you landed, ready to taxi and take off) |
| `M` | Mute / unmute sound |
| `N` (or `F1`–`F5`) | Change map |
| `H` | Show / hide the help text |
| `Esc` | Quit |

Prefer `W` = climb? Set `INVERT_PITCH = True` in `sim/config.py`.

## Aircraft

| Key | Aircraft | Character |
|-----|----------|-----------|
| `1` | Skylark trainer | Forgiving all-rounder |
| `2` | Barnstormer biplane | Slow, light and nimble |
| `3` | Falcon jet | Very fast, snappy roll, high landing speed; afterburner flame and roar |
| `4` | Atlas airliner | Big, heavy, sluggish; needs wide turns and gentle inputs |

Each aircraft has its own engine sound (buzzy prop, lumpy radial, rushing turbine roar, deep airliner rumble) whose pitch and loudness follow the throttle. You also hear the gear's mechanical grind and a clunk as it locks, tyre rumble while rolling, and a thump on touchdown; none of the sounds whine.

Switching mid-flight keeps your position and attitude (not available after a crash or landing).

## Maps

Press `N` to cycle maps (or `F1`–`F5` to pick one). Switching restarts you at the runway,
which is always on dry land, in the same aircraft.

| Key | Map | Look |
|-----|-----|------|
| `F1` | Home Fields | The original green plains, no water |
| `F2` | Emerald Lakes | Green hills dotted with lakes |
| `F3` | Island Chain | A warm sea scattered with islands; the runway is on one |
| `F4` | Sunset Coast | Dry shores in the west, open ocean to the east, a few ponds |
| `F5` | Frozen Fjords | Snowy highlands cut by long, dark fjords and lakes |

Water is not landable: touching it (landing, or taxiing into it) is a crash, with a splash
instead of a fireball, and the wreck sinks. Each map has its own ground, sky and tree colours.

## Flying tips

- You start airborne over the runway's start, heading north.
- Banking turns the plane; level the wings by releasing `A`/`D`.
- Flight is physics-flavoured: thrust vs. drag, gravity slows climbs and speeds dives,
  controls lag the keys and weaken at low speed, and banking pulls the nose down, so
  add back-pressure (`S`) in turns. Tune it in `sim/config.py`.
- Climbing bleeds speed. Below stall speed the plane sinks and the nose drops — push `W`
  and add throttle to recover.
- Lower the landing gear with `G` before touching down: landing with it up (or still
  moving) is a crash. With the gear down the HUD (bottom left) shows the speed limit for your aircraft. Cut the throttle and
  hold `B` to slow down; the brake backs off near stall speed so it can't stall you.
- After a safe landing, `R` parks you right there on the ground. Hold `Shift` for throttle,
  steer with `A`/`D`, brake with `B`, and pull back (`S`) above the rotate speed shown on screen.
  Ground speed is capped at 300 km/h.
  Crashing or restarting mid-flight sends you back to the start.
- Touch down gently, on the runway or anywhere else on open dry ground (level wings, low speed, slow descent) to **land**.
  Hitting the ground too fast or unlevel, or touching a mountain, building or tree with the body, tail, propeller or wheels is a
  **crash**. Clipping with just a **wing** snaps that wing off instead: it tumbles away, you keep
  flying, but the plane rolls and turns toward the missing side and sinks, and aileron input
  only partly cancels it. Losing the second wing, or hitting anything else, is a crash: the plane blows apart (the view switches to 3rd person).
  The wreck breaks into tumbling pieces that land, char and smoulder beside a scorch mark;
  the blast is bigger the faster you hit, and the camera shakes, and you hear a boom followed by crackling fire that dies down.

## Layout

```
main.py            game loop, input, view switching, landing/crash rules
sim/config.py      tunable settings (speeds, fog, window size, pitch inversion)
sim/aircraft.py    the four aircraft: handling numbers, mesh, camera offsets
sim/plane.py       flight model + the plane's low-poly mesh in world space
sim/camera.py      1st-person and chase cameras, projection
sim/maps.py       the maps: where the seas and lakes are, colours, sky
sim/world.py       runway and chunked procedural world with collisions
sim/renderer.py    projection, near/screen clipping, fog, painter's algorithm
sim/meshes.py      box / cone / airplane shape builders
sim/sound.py      generated engine, crash, fire and afterburner sounds (no audio files)
sim/explosion.py  crash: fireball, tumbling wreckage, scorch mark, smoke
sim/hud.py         flight data, throttle bar, cockpit frame
tests/             logic tests (no display needed)
```

## Tests

```bash
python3 -m unittest discover -s tests
```
