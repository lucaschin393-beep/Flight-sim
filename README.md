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
| `P` | Change view (3rd person ⇄ 1st person) |
| `R` | Restart |
| `H` | Show / hide the help text |
| `Esc` | Quit |

Prefer `W` = climb? Set `INVERT_PITCH = True` in `sim/config.py`.

## Flying tips

- You start airborne over the runway's start, heading north.
- Banking turns the plane; level the wings by releasing `A`/`D`.
- Climbing bleeds speed. Below stall speed the plane sinks and the nose drops — push `W`
  and add throttle to recover.
- Touch down on the runway, gently (level wings, low speed, slow descent) to **land**.
  Hitting the ground elsewhere, a mountain or a building is a **crash**.

## Layout

```
main.py            game loop, input, view switching, landing/crash rules
sim/config.py      tunable settings (speeds, fog, window size, pitch inversion)
sim/plane.py       flight model + the plane's low-poly mesh in world space
sim/camera.py      1st-person and chase cameras, projection
sim/world.py       runway and chunked procedural world with collisions
sim/renderer.py    projection, near/screen clipping, fog, painter's algorithm
sim/meshes.py      box / cone / airplane shape builders
sim/hud.py         flight data, throttle bar, cockpit frame
tests/             logic tests (no display needed)
```

## Tests

```bash
python3 -m unittest discover -s tests
```
