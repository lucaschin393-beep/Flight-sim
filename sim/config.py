"""Tunable settings for the simulator."""

WINDOW_SIZE = (1100, 700)
FPS = 60
FOV_DEGREES = 70

# W = nose down (push the stick forward), S = nose up (pull back).
# Set to True if you prefer W = climb.
INVERT_PITCH = False

# Flight model (units: metres, seconds)
MIN_SPEED = 30.0       # speed at idle throttle
MAX_SPEED = 100.0      # speed at full throttle
STALL_SPEED = 25.0
PITCH_RATE = 0.9       # rad/s
ROLL_RATE = 1.8        # rad/s
THROTTLE_RATE = 0.5    # per second
MAX_PITCH = 1.3        # rad (~75 degrees)
MAX_ROLL = 1.35        # rad (~77 degrees)

START_POSITION = (0.0, 140.0, -900.0)
START_SPEED = 65.0

# Rendering
FOG_START = 1400.0
FOG_END = 3600.0
FOG_COLOR = (190, 214, 232)
SKY_TOP = (70, 120, 200)
SKY_HORIZON = FOG_COLOR
GROUND_FAR = (126, 160, 118)
