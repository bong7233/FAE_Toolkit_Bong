"""Remote-IO / PIO interlock channel map.

Models a remote IO block of the kind used to interface AGV/AMR carriers with
equipment load ports: digital inputs (sensors / PIO request lines), digital
outputs (actuators / handshake / light tower), and analog inputs.

Channel naming follows a PIO-style load/unload handshake so the panel mirrors
real interlock checks performed during teaching and commissioning.
"""

from __future__ import annotations

# --- Discrete inputs (read, function 0x02): sensors & PIO request lines ---- #
DI_ES = 0  # emergency-stop healthy (1 = safe)
DI_AREA_CLEAR = 1  # safety area / light curtain clear
DI_L_REQ = 2  # load request
DI_U_REQ = 3  # unload request
DI_READY = 4  # equipment ready
DI_HO_AVBL = 5  # handoff available
DI_CS0 = 6  # carrier present at stage
DI_TR_REQ = 7  # transfer request
DI_BUSY = 8  # equipment busy
DI_COMPT = 9  # transfer complete
DI_COUNT = 16
DI_NAMES = [
    "ES_OK",
    "AREA_CLEAR",
    "L_REQ",
    "U_REQ",
    "READY",
    "HO_AVBL",
    "CS_0",
    "TR_REQ",
    "BUSY",
    "COMPT",
    *(f"DI{n}" for n in range(10, DI_COUNT)),
]

# --- Coils / digital outputs (read 0x01, write 0x05): actuators & lamps ---- #
DO_VALID = 0
DO_LOAD_CLAMP = 1
DO_LIFT_UP = 2
DO_LIFT_DOWN = 3
DO_CONVEYOR = 4
DO_LAMP_RED = 5
DO_LAMP_AMBER = 6
DO_LAMP_GREEN = 7
DO_BUZZER = 8
DO_COUNT = 16
DO_NAMES = [
    "VALID",
    "LOAD_CLAMP",
    "LIFT_UP",
    "LIFT_DOWN",
    "CONVEYOR",
    "LAMP_RED",
    "LAMP_AMBER",
    "LAMP_GREEN",
    "BUZZER",
    *(f"DO{n}" for n in range(9, DO_COUNT)),
]

# Outputs that physically move the machine and must respect the interlock.
MOTION_OUTPUTS = (DO_LOAD_CLAMP, DO_LIFT_UP, DO_LIFT_DOWN, DO_CONVEYOR)
# Lamps are driven by the controller, not the operator.
LAMP_OUTPUTS = (DO_LAMP_RED, DO_LAMP_AMBER, DO_LAMP_GREEN)

# --- Analog inputs (read, function 0x04) ----------------------------------- #
AI_DISTANCE = 0
AI_PRESSURE = 1
AI_WEIGHT = 2
AI_TEMP = 3
AI_COUNT = 4
AI_NAMES = ["distance", "pressure", "load_weight", "panel_temp"]
AI_UNITS = ["mm", "kPa", "kg", "℃"]
AI_SCALE = 0.1  # all analog channels transmit in 0.1-unit steps
