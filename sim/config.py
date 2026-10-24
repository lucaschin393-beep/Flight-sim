"""Tunable settings for the simulator."""

WINDOW_SIZE = (1100, 700)
FPS = 60
FOV_DEGREES = 70

# W = nose down (push the stick forward), S = nose up (pull back).
# Set to True if you prefer W = climb.
INVERT_PITCH = False

# Flight model (units: metres, seconds)
STALL_SPEED = 25.0
MAX_SPEED = 100.0      # level-flight speed at full throttle
MIN_SPEED = 30.0       # level-flight speed at idle throttle
DRAG = 0.0005          # deceleration per speed^2
IDLE_THRUST = DRAG * MIN_SPEED ** 2    # m/s^2 of thrust at idle / full throttle,
MAX_THRUST = DRAG * MAX_SPEED ** 2     # chosen so the speeds above hold in level flight
GEAR_DRAG = 0.25       # extra drag fraction with the gear fully down
GEAR_TIME = 2.0        # seconds for the gear to move up / down
MAX_GROUND_SPEED = 300 / 3.6   # 300 km/h, in m/s
WING_LOSS_ROLL = 1.0    # rad/s the plane rolls toward the side whose wing is missing
WING_LOSS_AILERON = 0.5  # aileron effectiveness left with a wing missing
WING_LOSS_SINK = 3.0    # m/s of extra sink from the lift lost with a wing
GROUND_FRICTION = 0.5  # m/s^2 rolling resistance while on the ground
WHEEL_BRAKE = 8.0      # m/s^2 extra deceleration from the brake key on the ground
TAXI_TURN_RATE = 0.6   # rad/s nose-wheel steering
BRAKE_DRAG = 6.0       # air brake multiplies drag by (1 + this)
BRAKE_RATE = 2.0       # how fast the air brake deploys / retracts (1/s)
INDUCED_DRAG = 2.0     # extra deceleration when pulling g in a steep bank
PITCH_RATE = 0.8       # rad/s at full elevator
ROLL_RATE = 1.6        # rad/s at full aileron
CONTROL_LAG = 5.0      # how quickly control surfaces follow the keys (1/s)
CONTROL_SPEED = 55.0   # speed at which controls reach full authority
BANK_NOSE_DROP = 0.4   # rad/s of nose drop per unit of (1 - cos(bank))
TURN_FACTOR = 2.0      # >1 makes turns tighter than physically exact
MAX_TURN_RATE = 0.9    # rad/s
THROTTLE_RATE = 0.4    # per second
MAX_PITCH = 1.3        # rad (~75 degrees)
MAX_ROLL = 1.35        # rad (~77 degrees)

START_POSITION = (0.0, 140.0, -900.0)
START_SPEED = 65.0

# Landing limits (the landing speed itself is per aircraft, see sim/aircraft.py)
LAND_MAX_ATTITUDE = 0.2    # rad of pitch / roll
LAND_MAX_SINK = 6.0        # m/s

# Rendering
FOG_START = 1400.0
FOG_END = 3600.0
FOG_COLOR = (190, 214, 232)
SKY_TOP = (70, 120, 200)
SKY_HORIZON = FOG_COLOR
GROUND_FAR = (126, 160, 118)
