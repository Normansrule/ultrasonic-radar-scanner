"""
Radar V5.1 — CadQuery model of record for the Ultrasonic Radar Scanner.

Everything printable is generated from THIS file. STL / STEP / 3MF files in
cad/ are build products: regenerate them with `python scripts/render_cad.py`
instead of editing them by hand.

Coordinate system (assembly, millimetres)
-----------------------------------------
  origin = centre of the body footprint, on the table (body underside, z = 0)
  +X     = to the viewer's right when they face the LCD
  +Y     = away from the viewer (the direction the sensor looks at 90 degrees)
  +Z     = up
  The LCD fascia is on the -Y face; the charging USB-C is on the +Y face.

Every dimension is a named variable below. A comment containing VERIFY marks
a value that depends on a real, purchased module (servo, horn, sensor, LCD,
breakout boards) and must be measured with calipers before printing the
full set. Print 08_fit_test_coupon first.

Nothing in this file has been physically printed or fitted yet — see
docs/VALIDATION.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cadquery as cq

# ============================================================================
# 0. GLOBAL PRINT / HARDWARE ALLOWANCES
# ============================================================================
M2_PILOT_D = 1.70        # printed pilot for M2 thread-forming / hand tap. VERIFY with coupon
M2_CLEAR_D = 2.25        # printed clearance hole for M2 shank. VERIFY with coupon
M2_HEAD_CB_D = 4.40      # counterbore for M2 pan/socket head
M2_NUT_AF = 4.00         # M2 hex nut across flats (ISO 4032)
M2_NUT_POCKET_AF = 4.35  # printed pocket across flats (nut + 0.35). VERIFY with coupon
M2_NUT_T = 1.60          # M2 nut thickness
FIT = 0.20               # general sliding clearance per side
PRINT_LAYER = 0.20       # reference layer height (Bambu A1 mini, 0.4 nozzle)

# ============================================================================
# 1. PURCHASED-MODULE REFERENCE DIMENSIONS  (all VERIFY)
# ============================================================================
# SG90-size positional micro servo (TowerPro-style envelope)
SERVO_BODY_L = 22.2          # VERIFY body length (datasheet: 22.2 x 11.8 x 31)
SERVO_BODY_W = 11.8          # VERIFY body width
SERVO_FLANGE_L = 32.2        # VERIFY tab-to-tab length
SERVO_FLANGE_T = 2.5         # VERIFY flange thickness
SERVO_FLANGE_BELOW = 15.9    # VERIFY body bottom -> flange underside
SERVO_CASE_ABOVE = 6.8       # VERIFY flange underside -> top of rectangular case
SERVO_BOSS_ABOVE = 10.8      # VERIFY flange underside -> top of round gear boss
SERVO_SPLINE_ABOVE = 15.1    # VERIFY flange underside -> top of output spline
SERVO_HOLE_PITCH = 27.5      # VERIFY flange screw-hole spacing
SERVO_SHAFT_OFFSET = 5.5     # VERIFY shaft centre -> body centre along length
SERVO_CUTOUT_CLR = 0.30      # clearance per side around servo body in roof

# Factory double-arm horn (keep the factory spline!)
HORN_LEN = 34.0              # VERIFY tip-to-tip length of the double arm
HORN_ARM_W = 6.2             # VERIFY widest arm width near the hub
HORN_ARM_T = 1.5             # VERIFY arm thickness
HORN_COLLAR_D = 7.2          # VERIFY hub collar diameter (top face)
HORN_SCREW_R = 12.0          # VERIFY radius of the arm holes used for 2x M2x6
HUB_BOTTOM_ABOVE_ROOF = 13.0 # VERIFY roof top -> underside of horn arms when seated

# HC-SR04 ultrasonic module
SR04_PCB_L = 45.0            # VERIFY
SR04_PCB_W = 20.0            # VERIFY
SR04_PCB_T = 1.6
SR04_CAN_D = 16.0            # VERIFY transducer diameter
SR04_CAN_H = 12.0            # VERIFY transducer height above PCB
SR04_CAN_PITCH = 26.0        # VERIFY transducer centre spacing
SR04_HOLE_X = 21.0           # VERIFY half-spacing of mounting holes along length
SR04_HOLE_Y = 8.5            # VERIFY half-spacing of mounting holes along width
SR04_HEADER_W = 11.0         # 4-pin header + female housings

# Waveshare 1.8" ST7735S LCD module (landscape)
LCD_PCB_L = 56.5             # Waveshare wiki: 56.5 x 34 mm. VERIFY your revision
LCD_PCB_H = 34.0
LCD_AA_W = 35.04             # active area (160 px direction)
LCD_AA_H = 28.03             # active area (128 px direction)
LCD_AA_OFFSET_X = 0.0        # VERIFY active-area centre vs PCB centre (Waveshare 2D drawing)
LCD_AA_OFFSET_Z = 0.0        # VERIFY
LCD_CENTER_X = -10.0         # placement on the front (assembly X)
LCD_CENTER_Z = 25.0          # placement on the front (assembly Z)

# 12 mm latching push switch
SWITCH_PANEL_D = 12.2        # VERIFY panel hole for a 12 mm switch
SWITCH_NUT_CLR_D = 17.0      # VERIFY clearance for the M12 nut behind the fascia
SWITCH_X = 38.0
SWITCH_Z = 25.0

# Adafruit 4090 USB-C breakout (20.4 x 14.2 x 5.0 mm)
USBC_PCB_L = 20.4            # along X
USBC_PCB_D = 14.2            # along Y
USBC_PCB_T = 1.6             # VERIFY
USBC_RECEPT_H = 3.3          # VERIFY receptacle height above PCB
USBC_OPEN_W = 12.5           # VERIFY clearance for the cable over-mould
USBC_OPEN_H = 7.0            # VERIFY
USBC_X = 44.0
USBC_OPEN_CENTER_Z = 12.0

# ESP32-WROOM-32 DevKit (classic 30-pin)
ESP32_L = 51.5               # VERIFY board length
ESP32_W = 28.4               # VERIFY board width
ESP32_BAY_X = -44.0          # bay centre X
ESP32_BAY_Y = -6.0           # bay centre Y (board long axis runs along Y)
ESP32_BAY_H = 24.0           # board underside height above body underside
ESP32_SUPPORT_LEN = 5.0      # length of each end support along Y (clear of header rows)

# 18650 single-cell wired holder
CELL_HOLDER_L = 77.0         # VERIFY
CELL_HOLDER_W = 21.0         # VERIFY
CELL_HOLDER_X = -8.0
CELL_HOLDER_Y = 33.0
ZIPTIE_W = 5.0               # tunnel width for a 3.6 mm tie
ZIPTIE_H = 2.2

# ============================================================================
# 2. PART 01 — BODY  (128 x 96 x 52)
# ============================================================================
BODY_W = 128.0
BODY_D = 96.0
BODY_H = 52.0
BODY_WALL = 2.4
BODY_FLOOR = 2.4
BODY_CORNER_R = 4.0
TOP_FRAME_T = 5.0            # solid top frame that carries the roof pocket
ROOF_POCKET_CLR = 0.30       # per side
DECK_CHAMFER_DEPTH = 12.6    # 45-degree self-supporting deck under the top frame
OPENING_X = 58.0             # half-width of the through-opening under the roof
OPENING_Y = 35.0             # half-depth of the through-opening under the roof
BOSS_NOTCH_X = 49.0          # corner gussets for the roof screws start here
BOSS_NOTCH_Y = 26.0
ROOF_SCREW_X = 55.0
ROOF_SCREW_Y = 32.0
PILOT_DEPTH = 9.0
FASCIA_SCREW_X = 55.0
FASCIA_SCREW_Z_LOW = 4.0
FASCIA_SCREW_Z_HIGH = 48.0
FASCIA_PILLAR_W = 11.6
FASCIA_PILLAR_D = 7.6
FASCIA_PILLAR_H = 9.0
VENT_SLOT_W = 3.0
VENT_SLOT_H = 18.0
VENT_SLOT_Z = 12.0
VENT_PITCH = 8.0
VENT_COUNT = 7
LCD_NEST_RIB = 1.6
LCD_NEST_CLR = 0.4
LCD_RELIEF_DEPTH = 10.0      # room behind the front wall for the LCD PCB + connector
KEY_KNOCKOUT_D = 7.0         # optional rear access for the DFR1026 KEY (see WIRING open issue)
KEY_KNOCKOUT_X = 26.0
KEY_KNOCKOUT_Z = 31.0          # above the cell holder
KNOCKOUT_SKIN = 0.45         # one perimeter, push out with a screwdriver if needed

# ============================================================================
# 3. PART 02 — FRONT PANEL / FASCIA (118 x 52 x 2.6)
# ============================================================================
FASCIA_W = 118.0
FASCIA_H = 52.0
FASCIA_T = 2.6
FASCIA_AA_MARGIN = 0.5       # around the LCD active area
FASCIA_AA_CHAMFER = 1.0
LCD_NEST_H = 4.0             # corner locators behind the fascia
LCD_NEST_LEG = 8.0

# ============================================================================
# 4. PART 03 — ROOF (120 x 74 x 3)
# ============================================================================
ROOF_W = 120.0
ROOF_D = 74.0
ROOF_T = 3.0
ROOF_BOSS_D = 5.2
ROOF_BOSS_H = 5.0
ROOF_VENT_W = 2.5
ROOF_VENT_L = 20.0
ROOF_VENT_XS = (34.0, 38.5, 43.0, 47.5)
WIRE_SLOT_L = 12.0
WIRE_SLOT_W = 4.5
WIRE_SLOT_Y = -31.5          # behind the head's open back (the head faces +Y)
KEEPER_SCREW_OFFSET = 21.0   # keeper screws at (-21,-21) and (+21,+21)

# ============================================================================
# 5. PART 04 — ROTOR HUB (~38 x 38 x 15)
# ============================================================================
HUB_FLANGE_D = 38.0
HUB_FLANGE_T = 4.0
HUB_BODY_D = 26.0
HUB_BODY_H = 11.0
HUB_HORN_SLOT_DEPTH = 2.0    # >= HORN_ARM_T + 0.5
HUB_HORN_SLOT_CLR = 0.3
HUB_SCREW_ACCESS_D = 5.5     # screwdriver reaches the factory horn screw through here
MAST_SIZE = 9.6              # square mast on the sensor head
MAST_KEY_CHAMFER = 2.5       # one chamfered corner = one-way key
MAST_LEN = 10.0
SOCKET_CLR = 0.20            # per side
CROSSBOLT_Z_IN_SOCKET = 5.0  # M2x20 cross-bolt height above socket floor
CROSSBOLT_CB_DEPTH = 4.0     # head counterbore depth
CROSSBOLT_NUT_DEPTH = 4.5    # nut pocket depth

# ============================================================================
# 6. PART 05 — TURRET KEEPER (~54 x 54 x 20)
# ============================================================================
KEEPER_W = 54.0
KEEPER_H = 20.0
KEEPER_CORNER_R = 6.0
KEEPER_BORE_D = HUB_FLANGE_D + 1.0
KEEPER_AXIAL_PLAY = 0.4      # hub flange top -> lip underside; adjust with 07 shim
KEEPER_LIP_ID = HUB_BODY_D + 1.0
KEEPER_FOOT_T = 3.0          # material under the screw counterbores
KEEPER_RELIEF_H = 4.6        # servo flange + screw heads under the keeper
KEEPER_RELIEF_CLR = 0.8
KEEPER_TOP_CHAMFER = 1.2
TICK_DEPTH = 0.6
TICK_W = 0.8

# ============================================================================
# 7. PART 06 — SENSOR HEAD (~53 x 39 x 10, printed face-down)
# ============================================================================
HEAD_W = 53.0                # along X
HEAD_H = 29.0                # along Z (in use), without the mast
HEAD_DEPTH = 10.0            # along Y (print height)
HEAD_FACE_T = 2.4
HEAD_STANDOFF_H = 5.0
HEAD_STANDOFF_D = 5.0
HEAD_CAN_CLR = 0.4           # radial clearance around each transducer
# the rotation axis sits HEAD_AXIS_BEHIND_FACE behind the outer face
HEAD_AXIS_BEHIND_FACE = MAST_SIZE / 2

# ============================================================================
# 8. PART 07 / 08 — SHIM, COUPON
# ============================================================================
SHIM_T = 0.4
COUPON_W = 66.0
COUPON_D = 28.0
COUPON_T = 3.0

# ============================================================================
# 9. DERIVED ASSEMBLY HEIGHTS
# ============================================================================
ROOF_TOP_Z = BODY_H                         # roof sits flush in its pocket
TURRET_Z0 = ROOF_TOP_Z                      # keeper / servo flange sit here
HUB_Z0 = TURRET_Z0 + HUB_BOTTOM_ABOVE_ROOF  # underside of hub
HUB_TOP_Z = HUB_Z0 + HUB_FLANGE_T + HUB_BODY_H
HEAD_Z0 = HUB_TOP_Z                         # head's lower rim sits on the hub

PART_NAMES = [
    "01_body",
    "02_front_panel",
    "03_roof",
    "04_rotor_hub",
    "05_turret_keeper",
    "06_sensor_head",
    "07_keeper_shim_0p4mm",
    "08_fit_test_coupon",
]
REQUIRED_PARTS = PART_NAMES[:6]


# ============================================================================
# helpers
# ============================================================================
def box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    return (cq.Workplane("XY")
            .box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


def cyl_z(x, y, z0, h, d) -> cq.Workplane:
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(d / 2).extrude(h)


def cyl_y(x, z, y0, length, d) -> cq.Workplane:
    """Cylinder along +Y starting at y0."""
    return (cq.Workplane("XZ", origin=(0, y0, 0)).center(x, z)
            .circle(d / 2).extrude(-length))


def cyl_x(y, z, x0, length, d) -> cq.Workplane:
    return (cq.Workplane("YZ", origin=(x0, 0, 0)).center(y, z)
            .circle(d / 2).extrude(length))


def rounded_rect_prism(w, d, z0, h, r) -> cq.Workplane:
    return (cq.Workplane("XY").workplane(offset=z0)
            .rect(w, d).extrude(h).edges("|Z").fillet(r))


def notched_opening(hx, hy, nx, ny):
    """Rectangle with square notches kept solid at each corner (for screw gussets)."""
    return [(hx, -ny), (hx, ny), (nx, ny), (nx, hy), (-nx, hy), (-nx, ny),
            (-hx, ny), (-hx, -ny), (-nx, -ny), (-nx, -hy), (nx, -hy), (nx, -ny)]


def offset_diag(pts, h):
    return [(x + math.copysign(h, x), y + math.copysign(h, y)) for x, y in pts]


def keyed_square(size, chamfer):
    """Square (centred) with its (+x,+y) corner chamfered — a one-way key."""
    s = size / 2
    return [(-s, -s), (s, -s), (s, s - chamfer), (s - chamfer, s), (-s, s)]


def hex_prism_y(x, z, y0, length, af, vertex_up=True) -> cq.Workplane:
    d = af / math.cos(math.radians(30))
    wp = cq.Workplane("XZ", origin=(0, y0, 0)).center(x, z)
    poly = wp.polygon(6, d)
    if vertex_up:
        poly = wp.transformed(rotate=(0, 0, 30)).polygon(6, d)
    return poly.extrude(-length)


# ============================================================================
# PART BUILDERS (assembly coordinates)
# ============================================================================
def build_body() -> cq.Workplane:
    iw, idp = BODY_W - 2 * BODY_WALL, BODY_D - 2 * BODY_WALL
    z_frame = BODY_H - TOP_FRAME_T

    shell = rounded_rect_prism(BODY_W, BODY_D, 0, BODY_H, BODY_CORNER_R)
    cavity = rounded_rect_prism(iw, idp, BODY_FLOOR, BODY_H, max(BODY_CORNER_R - BODY_WALL, 0.8))
    body = shell.cut(cavity)

    # --- 45-degree self-supporting deck under the top frame -----------------
    top_poly = notched_opening(OPENING_X, OPENING_Y, BOSS_NOTCH_X, BOSS_NOTCH_Y)
    bot_poly = offset_diag(top_poly, DECK_CHAMFER_DEPTH)
    frustum = (cq.Workplane("XY").workplane(offset=z_frame - DECK_CHAMFER_DEPTH)
               .polyline(bot_poly).close()
               .workplane(offset=DECK_CHAMFER_DEPTH)
               .polyline(top_poly).close()
               .loft(ruled=True))
    fill = box(-iw / 2, iw / 2, -idp / 2, idp / 2, z_frame - DECK_CHAMFER_DEPTH, z_frame).cut(frustum)
    body = body.union(fill)
    # top frame: solid slab with the notched opening and the roof pocket
    frame = rounded_rect_prism(BODY_W, BODY_D, z_frame, TOP_FRAME_T, BODY_CORNER_R)
    frame = frame.cut(cq.Workplane("XY").workplane(offset=z_frame - 1)
                      .polyline(top_poly).close().extrude(TOP_FRAME_T + 2))
    body = body.union(frame)
    pocket = box(-(ROOF_W / 2 + ROOF_POCKET_CLR), ROOF_W / 2 + ROOF_POCKET_CLR,
                 -(ROOF_D / 2 + ROOF_POCKET_CLR), ROOF_D / 2 + ROOF_POCKET_CLR,
                 BODY_H - ROOF_T, BODY_H + 1)
    body = body.cut(pocket)

    # roof screw pilots in the corner gussets
    for sx in (-1, 1):
        for sy in (-1, 1):
            body = body.cut(cyl_z(sx * ROOF_SCREW_X, sy * ROOF_SCREW_Y,
                                  BODY_H - ROOF_T - PILOT_DEPTH, PILOT_DEPTH + 0.01, M2_PILOT_D))

    # --- front wall: LCD window + relief, switch nut clearance --------------
    y_front_out = -BODY_D / 2
    y_front_in = -BODY_D / 2 + BODY_WALL
    nest_out_w = LCD_PCB_L + 2 * (LCD_NEST_CLR + LCD_NEST_RIB)
    nest_out_h = LCD_PCB_H + 2 * (LCD_NEST_CLR + LCD_NEST_RIB)
    win_w, win_h = nest_out_w + 0.8, nest_out_h + 0.8
    wx0, wx1 = LCD_CENTER_X - win_w / 2, LCD_CENTER_X + win_w / 2
    wz0, wz1 = LCD_CENTER_Z - win_h / 2, LCD_CENTER_Z + win_h / 2
    body = body.cut(box(wx0, wx1, y_front_out - 1, y_front_in + LCD_RELIEF_DEPTH, wz0, wz1))
    body = body.cut(cyl_y(SWITCH_X, SWITCH_Z, y_front_out - 1, BODY_WALL + 2, SWITCH_NUT_CLR_D))

    # fascia pillars (bottom pair) and pilots (all four)
    for sx in (-1, 1):
        x0 = sx * FASCIA_SCREW_X - FASCIA_PILLAR_W / 2
        x1 = sx * FASCIA_SCREW_X + FASCIA_PILLAR_W / 2
        x0, x1 = max(x0, -BODY_W / 2 + 1), min(x1, BODY_W / 2 - 1)
        body = body.union(box(x0, x1, y_front_in - 0.5, y_front_in + FASCIA_PILLAR_D,
                              BODY_FLOOR - 0.5, FASCIA_PILLAR_H))
        for z in (FASCIA_SCREW_Z_LOW, FASCIA_SCREW_Z_HIGH):
            body = body.cut(cyl_y(sx * FASCIA_SCREW_X, z, y_front_out - 0.01, PILOT_DEPTH, M2_PILOT_D))

    # --- side vents ----------------------------------------------------------
    for sx in (-1, 1):
        xa, xb = sorted((sx * (BODY_W / 2 - BODY_WALL - 1), sx * (BODY_W / 2 + 1)))
        for i in range(VENT_COUNT):
            y = (i - (VENT_COUNT - 1) / 2) * VENT_PITCH
            body = body.cut(box(xa, xb, y - VENT_SLOT_W / 2, y + VENT_SLOT_W / 2,
                                VENT_SLOT_Z, VENT_SLOT_Z + VENT_SLOT_H))

    # --- rear wall: USB-C opening + cradle, KEY knock-out -------------------
    y_rear_in = BODY_D / 2 - BODY_WALL
    usb_open = (cq.Workplane("XZ", origin=(0, BODY_D / 2 + 1, 0))
                .center(USBC_X, USBC_OPEN_CENTER_Z)
                .rect(USBC_OPEN_W, USBC_OPEN_H).extrude(BODY_WALL + 2)
                .edges("|Y").fillet(1.5))
    body = body.cut(usb_open)
    pcb_bottom = USBC_OPEN_CENTER_Z - USBC_RECEPT_H / 2 - USBC_PCB_T
    body = body.union(box(USBC_X - 12, USBC_X + 12, y_rear_in - USBC_PCB_D - 1, y_rear_in + 0.5,
                          BODY_FLOOR - 0.5, pcb_bottom))
    for sx in (-1, 1):  # side guides that locate the breakout
        gx = USBC_X + sx * (USBC_PCB_L / 2 + FIT + 0.8)
        body = body.union(box(gx - 0.8, gx + 0.8, y_rear_in - USBC_PCB_D - 1, y_rear_in + 0.5,
                              pcb_bottom - 0.5, pcb_bottom + 2.4))
    # knock-out: hole through the wall except a thin outer skin
    body = body.cut(cyl_y(KEY_KNOCKOUT_X, KEY_KNOCKOUT_Z, BODY_D / 2 - BODY_WALL - 0.5,
                          BODY_WALL + 0.5 - KNOCKOUT_SKIN, KEY_KNOCKOUT_D))

    # --- ESP32 bay end supports (clear of the header rows) + end lips ---------
    for sy in (-1, 1):
        board_end = ESP32_BAY_Y + sy * ESP32_L / 2
        ya, yb = sorted((board_end - sy * ESP32_SUPPORT_LEN, board_end + sy * 1.8))
        body = body.union(box(ESP32_BAY_X - ESP32_W / 2 - 0.5, ESP32_BAY_X + ESP32_W / 2 + 0.5,
                              ya, yb, BODY_FLOOR - 0.5, ESP32_BAY_H))
        la, lb = sorted((board_end + sy * 0.3, board_end + sy * 1.8))
        body = body.union(box(ESP32_BAY_X - ESP32_W / 2 - 0.5, ESP32_BAY_X + ESP32_W / 2 + 0.5,
                              la, lb, ESP32_BAY_H - 0.01, ESP32_BAY_H + 2.0))

    # --- zip-tie anchors under the cell holder -------------------------------
    for xa in (CELL_HOLDER_X - 20, CELL_HOLDER_X + 20):
        anchor = box(xa - 4.5, xa + 4.5, CELL_HOLDER_Y - 5, CELL_HOLDER_Y + 5,
                     BODY_FLOOR - 0.5, BODY_FLOOR + ZIPTIE_H + 2.0)
        anchor = anchor.cut(box(xa - ZIPTIE_W / 2, xa + ZIPTIE_W / 2,
                                CELL_HOLDER_Y - 6, CELL_HOLDER_Y + 6,
                                BODY_FLOOR, BODY_FLOOR + ZIPTIE_H))
        body = body.union(anchor)

    # --- engraved safety label on the rear wall (reads correctly from behind) --
    try:
        rear = cq.Plane(origin=(0, BODY_D / 2 + 0.01, 0), xDir=(-1, 0, 0), normal=(0, 1, 0))
        label = (cq.Workplane(rear).center(0, 42.0)
                 .text("EDUCATIONAL SONAR - NOT A SAFETY DEVICE", 4.0, -0.5,
                       kind="bold", halign="center", valign="center"))
        body = body.cut(label)
    except Exception:  # fonts differ between machines; the label is cosmetic
        pass
    return body


def build_front_panel() -> cq.Workplane:
    y_back = -BODY_D / 2
    y_front = y_back - FASCIA_T
    p = box(-FASCIA_W / 2, FASCIA_W / 2, y_front, y_back, 0, FASCIA_H)
    p = p.edges("|Y").fillet(3.0)
    # display aperture with a 45-degree chamfer on the viewer side
    ax = LCD_CENTER_X + LCD_AA_OFFSET_X
    az = LCD_CENTER_Z + LCD_AA_OFFSET_Z
    aw, ah = LCD_AA_W + 2 * FASCIA_AA_MARGIN, LCD_AA_H + 2 * FASCIA_AA_MARGIN
    ap = (cq.Workplane("XY").workplane(offset=0)
          .box(aw, FASCIA_T + 2, ah).translate((ax, (y_front + y_back) / 2, az)))
    p = p.cut(ap)
    ch = (cq.Workplane("XZ", origin=(0, y_front - 0.001, 0)).center(ax, az)
          .rect(aw + 2 * FASCIA_AA_CHAMFER, ah + 2 * FASCIA_AA_CHAMFER)
          .workplane(offset=-FASCIA_AA_CHAMFER).rect(aw, ah).loft(ruled=True))
    p = p.cut(ch)
    # switch hole and screw clearances
    p = p.cut(cyl_y(SWITCH_X, SWITCH_Z, y_front - 1, FASCIA_T + 2, SWITCH_PANEL_D))
    for sx in (-1, 1):
        for z in (FASCIA_SCREW_Z_LOW, FASCIA_SCREW_Z_HIGH):
            p = p.cut(cyl_y(sx * FASCIA_SCREW_X, z, y_front - 1, FASCIA_T + 2, M2_CLEAR_D))
    # L-shaped corner locators for the LCD PCB (back side)
    hx = LCD_PCB_L / 2 + LCD_NEST_CLR
    hz = LCD_PCB_H / 2 + LCD_NEST_CLR
    t, leg = LCD_NEST_RIB, LCD_NEST_LEG
    for sx in (-1, 1):
        for sz in (-1, 1):
            cx, cz = LCD_CENTER_X + sx * hx, LCD_CENTER_Z + sz * hz
            xa0, xa1 = sorted((cx, cx + sx * t))
            za0, za1 = sorted((cz - sz * leg, cz + sz * t))
            p = p.union(box(xa0, xa1, y_back - 0.01, y_back + LCD_NEST_H, za0, za1))
            xb0, xb1 = sorted((cx - sx * leg, cx + sx * t))
            zb0, zb1 = sorted((cz, cz + sz * t))
            p = p.union(box(xb0, xb1, y_back - 0.01, y_back + LCD_NEST_H, zb0, zb1))
    # engraved labels on the viewer side (cosmetic)
    try:
        for txt, x, z, size in (("EDU SONAR", LCD_CENTER_X, 47.0, 3.6), ("ON / OFF", SWITCH_X, 12.5, 3.2)):
            lab = (cq.Workplane("XZ", origin=(0, y_front, 0)).center(x, z)
                   .text(txt, size, -0.4, kind="regular", halign="center", valign="center"))
            p = p.cut(lab)
    except Exception:
        pass
    return p


def servo_x_center() -> float:
    return SERVO_SHAFT_OFFSET  # servo body centre, shaft at x = 0


def build_roof() -> cq.Workplane:
    z0, z1 = BODY_H - ROOF_T, BODY_H
    r = rounded_rect_prism(ROOF_W, ROOF_D, z0, ROOF_T, 3.0)
    sxc = servo_x_center()
    servo_holes = [sxc - SERVO_HOLE_PITCH / 2, sxc + SERVO_HOLE_PITCH / 2]
    keeper_pts = [(-KEEPER_SCREW_OFFSET, -KEEPER_SCREW_OFFSET), (KEEPER_SCREW_OFFSET, KEEPER_SCREW_OFFSET)]
    # bosses below the roof for servo + keeper screws
    for x in servo_holes:
        r = r.union(cyl_z(x, 0, z0 - ROOF_BOSS_H, ROOF_BOSS_H + 0.01, ROOF_BOSS_D))
    for x, y in keeper_pts:
        r = r.union(cyl_z(x, y, z0 - ROOF_BOSS_H, ROOF_BOSS_H + 0.01, ROOF_BOSS_D + 0.8))
    # servo body cut-out with cable notches on both ends
    cl, cw = SERVO_BODY_L + 2 * SERVO_CUTOUT_CLR, SERVO_BODY_W + 2 * SERVO_CUTOUT_CLR
    r = r.cut(box(sxc - cl / 2, sxc + cl / 2, -cw / 2, cw / 2, z0 - ROOF_BOSS_H - 1, z1 + 1))
    r = r.cut(box(sxc - cl / 2 - 2.0, sxc + cl / 2 + 2.0, -1.75, 1.75, z0 - ROOF_BOSS_H - 1, z1 + 1))
    for x in servo_holes:
        r = r.cut(cyl_z(x, 0, z0 - ROOF_BOSS_H - 0.01, ROOF_BOSS_H + ROOF_T + 0.02, M2_PILOT_D))
    for x, y in keeper_pts:
        r = r.cut(cyl_z(x, y, z0 - ROOF_BOSS_H - 0.01, ROOF_BOSS_H + ROOF_T + 0.02, M2_PILOT_D))
    # corner clearance holes to the body gussets
    for sx in (-1, 1):
        for sy in (-1, 1):
            r = r.cut(cyl_z(sx * ROOF_SCREW_X, sy * ROOF_SCREW_Y, z0 - 1, ROOF_T + 2, M2_CLEAR_D))
    # vents
    for sx in (-1, 1):
        for x in ROOF_VENT_XS:
            r = r.cut(box(sx * x - ROOF_VENT_W / 2, sx * x + ROOF_VENT_W / 2,
                          -ROOF_VENT_L / 2, ROOF_VENT_L / 2, z0 - 1, z1 + 1))
    # sensor-cable pass-through behind the turret
    slot = (cq.Workplane("XY").workplane(offset=z0 - 1).center(0, WIRE_SLOT_Y)
            .slot2D(WIRE_SLOT_L, WIRE_SLOT_W).extrude(ROOF_T + 2))
    r = r.cut(slot)
    return r


def build_rotor_hub() -> cq.Workplane:
    z0 = HUB_Z0
    h = cyl_z(0, 0, z0, HUB_FLANGE_T, HUB_FLANGE_D)
    h = h.union(cyl_z(0, 0, z0 + HUB_FLANGE_T - 0.01, HUB_BODY_H + 0.01, HUB_BODY_D))
    h = h.faces(">Z").edges().chamfer(0.6)
    # horn nest (double arm lies along X) + collar recess
    sw = HORN_ARM_W + 2 * HUB_HORN_SLOT_CLR
    sl = HORN_LEN + 2 * HUB_HORN_SLOT_CLR
    h = h.cut(box(-sl / 2, sl / 2, -sw / 2, sw / 2, z0 - 1, z0 + HUB_HORN_SLOT_DEPTH))
    h = h.cut(cyl_z(0, 0, z0 - 1, HUB_HORN_SLOT_DEPTH + 1.8, HORN_COLLAR_D + 0.6))
    # screwdriver access to the factory horn screw
    top = HUB_TOP_Z
    sock_floor = top - MAST_LEN - 0.4
    h = h.cut(cyl_z(0, 0, z0 - 1, sock_floor - z0 + 1.01, HUB_SCREW_ACCESS_D))
    # keyed mast socket
    s = MAST_SIZE + 2 * SOCKET_CLR
    sock = (cq.Workplane("XY").workplane(offset=sock_floor)
            .polyline(keyed_square(s, MAST_KEY_CHAMFER - SOCKET_CLR)).close()
            .extrude(top - sock_floor + 1))
    h = h.cut(sock)
    # horn screw pilots (2x M2x6 from below through the horn arms)
    for sx in (-1, 1):
        h = h.cut(cyl_z(sx * HORN_SCREW_R, 0, z0 - 1, HUB_HORN_SLOT_DEPTH + 1 + 5.0, M2_PILOT_D))
    # M2x20 cross-bolt along X: head counterbore on -X, captive nut on +X
    zc = sock_floor + CROSSBOLT_Z_IN_SOCKET
    R = HUB_BODY_D / 2
    h = h.cut(cyl_x(0, zc, -R - 1, 2 * R + 2, M2_CLEAR_D))
    h = h.cut(cyl_x(0, zc, -R - 1, CROSSBOLT_CB_DEPTH + 1, M2_HEAD_CB_D))
    nut = (cq.Workplane("YZ", origin=(R - CROSSBOLT_NUT_DEPTH, 0, 0)).center(0, zc)
           .polygon(6, M2_NUT_POCKET_AF / math.cos(math.radians(30))).extrude(CROSSBOLT_NUT_DEPTH + 1))
    h = h.cut(nut)
    # pointer groove at +Y (the 90-degree direction when the servo is centred)
    h = h.cut(box(-0.5, 0.5, R - 0.6, R + 1, z0 + HUB_FLANGE_T + 1.0, top + 1))
    return h


def build_turret_keeper(shim: float = 0.0) -> cq.Workplane:
    z0 = TURRET_Z0 + shim
    k = rounded_rect_prism(KEEPER_W, KEEPER_W, z0, KEEPER_H, KEEPER_CORNER_R)
    k = k.faces(">Z").edges().chamfer(KEEPER_TOP_CHAMFER)
    lip_under = (HUB_Z0 + HUB_FLANGE_T + KEEPER_AXIAL_PLAY)
    k = k.cut(cyl_z(0, 0, z0 - 1, lip_under - z0 + 1, KEEPER_BORE_D))
    k = k.cut(cyl_z(0, 0, z0 - 1, KEEPER_H + 2, KEEPER_LIP_ID))
    # relief for the servo flange + screw heads
    sxc = servo_x_center()
    rl = SERVO_FLANGE_L + 2 * KEEPER_RELIEF_CLR + 2.0
    rw = SERVO_BODY_W + 2 * KEEPER_RELIEF_CLR + 1.0
    k = k.cut(box(sxc - rl / 2, sxc + rl / 2, -rw / 2, rw / 2, z0 - 1, z0 + KEEPER_RELIEF_H))
    # screws: counterbore from the top down to a 3 mm foot
    for sgn in (-1, 1):
        x = y = sgn * KEEPER_SCREW_OFFSET
        k = k.cut(cyl_z(x, y, z0 - 1, KEEPER_H + 2, M2_CLEAR_D))
        k = k.cut(cyl_z(x, y, z0 + KEEPER_FOOT_T, KEEPER_H, M2_HEAD_CB_D + 0.6))
    # engraved angle ticks on the top face: majors every 30 deg, minors every 15 deg (30..150)
    ztop = z0 + KEEPER_H
    for deg in range(30, 151, 15):
        major = deg % 30 == 0
        r0 = KEEPER_LIP_ID / 2 + 1.8 if major else KEEPER_LIP_ID / 2 + 3.5
        r1 = KEEPER_BORE_D / 2 + 4.5
        L = r1 - r0
        a = math.radians(deg)
        tick = (cq.Workplane("XY").workplane(offset=ztop - TICK_DEPTH)
                .center(0, 0).rect(L, TICK_W).extrude(TICK_DEPTH + 1)
                .translate(((r0 + r1) / 2, 0, 0))
                .rotate((0, 0, 0), (0, 0, 1), deg))
        k = k.cut(tick)
    return k


def build_sensor_head() -> cq.Workplane:
    """Built with the face toward +Y and the rotation axis at x = y = 0."""
    y_face = HEAD_AXIS_BEHIND_FACE            # outer face plane
    y_back = y_face - HEAD_DEPTH
    z0, z1 = HEAD_Z0, HEAD_Z0 + HEAD_H
    zc = (z0 + z1) / 2
    shell = box(-HEAD_W / 2, HEAD_W / 2, y_back, y_face, z0, z1).edges("|Y").fillet(3.0)
    inner_w = SR04_PCB_L + 2 * 0.5
    inner_h = SR04_PCB_W + 2 * 0.5
    head = shell.cut(box(-inner_w / 2, inner_w / 2, y_back - 1, y_face - HEAD_FACE_T,
                         zc - inner_h / 2, zc + inner_h / 2))
    # standoffs + clearance holes for 4x M2x12 with nuts on the back
    for sx in (-1, 1):
        for sz in (-1, 1):
            x, z = sx * SR04_HOLE_X, zc + sz * SR04_HOLE_Y
            head = head.union(cyl_y(x, z, y_face - HEAD_FACE_T - HEAD_STANDOFF_H - 0.01,
                                    HEAD_STANDOFF_H + 0.02, HEAD_STANDOFF_D).translate((0, 0, 0)))
    # transducer windows
    for sx in (-1, 1):
        head = head.cut(cyl_y(sx * SR04_CAN_PITCH / 2, zc, y_back - 1, HEAD_DEPTH + 2,
                              SR04_CAN_D + 2 * HEAD_CAN_CLR))
    for sx in (-1, 1):
        for sz in (-1, 1):
            head = head.cut(cyl_y(sx * SR04_HOLE_X, zc + sz * SR04_HOLE_Y, y_back - 1,
                                  HEAD_DEPTH + 2, M2_CLEAR_D))
    # header notch in the TOP rim (sensor mounted header-up so the mast is free)
    head = head.cut(box(-SR04_HEADER_W / 2, SR04_HEADER_W / 2, y_back - 1, y_face - HEAD_FACE_T,
                        zc + inner_h / 2 - 0.5, z1 + 1))
    # keyed mast below the head (lies flat on the bed when printed face-down)
    mast = (cq.Workplane("XY").workplane(offset=z0 - MAST_LEN)
            .polyline(keyed_square(MAST_SIZE, MAST_KEY_CHAMFER)).close()
            .extrude(MAST_LEN + 1.0))
    mast = mast.edges("<Z").chamfer(0.5)
    head = head.union(mast)
    # cross-bolt hole through the mast (matches the hub)
    sock_floor = HUB_TOP_Z - MAST_LEN - 0.4
    zc_bolt = sock_floor + CROSSBOLT_Z_IN_SOCKET
    head = head.cut(cyl_x(0, zc_bolt, -MAST_SIZE, 2 * MAST_SIZE, M2_CLEAR_D))
    return head


def build_keeper_shim() -> cq.Workplane:
    z0 = TURRET_Z0
    s = rounded_rect_prism(KEEPER_W, KEEPER_W, z0, SHIM_T, KEEPER_CORNER_R)
    s = s.cut(cyl_z(0, 0, z0 - 1, SHIM_T + 2, KEEPER_BORE_D))
    sxc = servo_x_center()
    rl = SERVO_FLANGE_L + 2 * KEEPER_RELIEF_CLR + 2.0
    rw = SERVO_BODY_W + 2 * KEEPER_RELIEF_CLR + 1.0
    s = s.cut(box(sxc - rl / 2, sxc + rl / 2, -rw / 2, rw / 2, z0 - 1, z0 + SHIM_T + 1))
    for sgn in (-1, 1):
        s = s.cut(cyl_z(sgn * KEEPER_SCREW_OFFSET, sgn * KEEPER_SCREW_OFFSET, z0 - 1, SHIM_T + 2, M2_CLEAR_D))
    return s


COUPON_PILOTS = (1.60, 1.70, 1.80)
COUPON_CLEARS = (2.15, 2.25, 2.35)


def build_fit_test_coupon() -> cq.Workplane:
    """Flat coupon (printed as-is). Tests: M2 pilots, M2 clearances, the SG90
    roof cut-out + flange pilots, the 12 mm switch hole, and an M2 nut pocket."""
    c = (cq.Workplane("XY").rect(COUPON_W, COUPON_D).extrude(COUPON_T)
         .edges("|Z").fillet(2.0))
    x_servo = -COUPON_W / 2 + 18.5
    cl, cw = SERVO_BODY_L + 2 * SERVO_CUTOUT_CLR, SERVO_BODY_W + 2 * SERVO_CUTOUT_CLR
    c = c.cut(box(x_servo - cl / 2, x_servo + cl / 2, -cw / 2, cw / 2, -1, COUPON_T + 1))
    for sx in (-1, 1):
        c = c.cut(cyl_z(x_servo + sx * SERVO_HOLE_PITCH / 2, 0, -1, COUPON_T + 2, M2_PILOT_D))
    x_sw = x_servo + 25.5
    c = c.cut(cyl_z(x_sw, 0, -1, COUPON_T + 2, SWITCH_PANEL_D))
    x_col = x_sw + 11.5
    for i, d in enumerate(COUPON_PILOTS):
        c = c.cut(cyl_z(x_col, -8.5 + 8.5 * i, -1, COUPON_T + 2, d))
    for i, d in enumerate(COUPON_CLEARS):
        c = c.cut(cyl_z(x_col + 6.5, -8.5 + 8.5 * i, -1, COUPON_T + 2, d))
    # nut pocket (1.8 deep) beside the servo cut-out
    nut = (cq.Workplane("XY").workplane(offset=COUPON_T - 1.8).center(x_servo, 10.3)
           .polygon(6, M2_NUT_POCKET_AF / math.cos(math.radians(30))).extrude(2))
    c = c.cut(nut).cut(cyl_z(x_servo, 10.3, -1, COUPON_T + 2, M2_CLEAR_D))
    try:
        lab = (cq.Workplane("XY").workplane(offset=COUPON_T).center(x_sw, -10.2)
               .text("V5 FIT", 3.0, -0.4, kind="bold", halign="center", valign="center"))
        c = c.cut(lab)
    except Exception:
        pass
    return c


# ============================================================================
# REFERENCE ENVELOPES (not printed; used for fit checks and renders)
# ============================================================================
def ref_servo() -> cq.Workplane:
    sxc = servo_x_center()
    z_fl = TURRET_Z0
    b = box(sxc - SERVO_BODY_L / 2, sxc + SERVO_BODY_L / 2, -SERVO_BODY_W / 2, SERVO_BODY_W / 2,
            z_fl - SERVO_FLANGE_BELOW, z_fl + SERVO_CASE_ABOVE)
    b = b.union(box(sxc - SERVO_FLANGE_L / 2, sxc + SERVO_FLANGE_L / 2,
                    -SERVO_BODY_W / 2, SERVO_BODY_W / 2, z_fl, z_fl + SERVO_FLANGE_T))
    b = b.union(cyl_z(0, 0, z_fl + SERVO_CASE_ABOVE - 0.01, SERVO_BOSS_ABOVE - SERVO_CASE_ABOVE, 11.6))
    b = b.union(cyl_z(0, 0, z_fl + SERVO_BOSS_ABOVE - 0.01, SERVO_SPLINE_ABOVE - SERVO_BOSS_ABOVE - 1.4, 4.8))
    return b


def ref_horn() -> cq.Workplane:
    z = HUB_Z0
    return (box(-HORN_LEN / 2, HORN_LEN / 2, -HORN_ARM_W / 2 + 0.6, HORN_ARM_W / 2 - 0.6, z, z + HORN_ARM_T)
            .union(cyl_z(0, 0, z - 2.4, 2.4 + HORN_ARM_T, HORN_COLLAR_D)))


def ref_sr04() -> cq.Workplane:
    y_face = HEAD_AXIS_BEHIND_FACE
    y_pcb_front = y_face - HEAD_FACE_T - HEAD_STANDOFF_H
    zc = HEAD_Z0 + HEAD_H / 2
    p = box(-SR04_PCB_L / 2, SR04_PCB_L / 2, y_pcb_front - SR04_PCB_T, y_pcb_front,
            zc - SR04_PCB_W / 2, zc + SR04_PCB_W / 2)
    for sx in (-1, 1):
        p = p.union(cyl_y(sx * SR04_CAN_PITCH / 2, zc, y_pcb_front - 0.01, SR04_CAN_H, SR04_CAN_D))
    return p


def ref_lcd() -> cq.Workplane:
    y0 = -BODY_D / 2
    return (box(LCD_CENTER_X - LCD_PCB_L / 2, LCD_CENTER_X + LCD_PCB_L / 2, y0 + 2.2, y0 + 3.8,
                LCD_CENTER_Z - LCD_PCB_H / 2, LCD_CENTER_Z + LCD_PCB_H / 2)
            .union(box(LCD_CENTER_X - LCD_AA_W / 2 - 1.5, LCD_CENTER_X + LCD_AA_W / 2 + 1.5, y0 + 0.05, y0 + 2.2,
                       LCD_CENTER_Z - LCD_AA_H / 2 - 2.5, LCD_CENTER_Z + LCD_AA_H / 2 + 1.5)))


def ref_esp32() -> cq.Workplane:
    return box(ESP32_BAY_X - ESP32_W / 2, ESP32_BAY_X + ESP32_W / 2,
               ESP32_BAY_Y - ESP32_L / 2, ESP32_BAY_Y + ESP32_L / 2, ESP32_BAY_H, ESP32_BAY_H + 1.6)


def ref_cell_holder() -> cq.Workplane:
    z0 = BODY_FLOOR + ZIPTIE_H + 2.0
    return box(CELL_HOLDER_X - CELL_HOLDER_L / 2, CELL_HOLDER_X + CELL_HOLDER_L / 2,
               CELL_HOLDER_Y - CELL_HOLDER_W / 2, CELL_HOLDER_Y + CELL_HOLDER_W / 2, z0, z0 + 20.0)


def ref_usbc() -> cq.Workplane:
    y_in = BODY_D / 2 - BODY_WALL
    pcb_bottom = USBC_OPEN_CENTER_Z - USBC_RECEPT_H / 2 - USBC_PCB_T
    return (box(USBC_X - USBC_PCB_L / 2, USBC_X + USBC_PCB_L / 2, y_in - USBC_PCB_D, y_in - 0.1,
                pcb_bottom, pcb_bottom + USBC_PCB_T)
            .union(box(USBC_X - 4.5, USBC_X + 4.5, y_in - 7.4, y_in - 0.1,
                       pcb_bottom + USBC_PCB_T, pcb_bottom + USBC_PCB_T + USBC_RECEPT_H)))


REFERENCE_BUILDERS = {
    "ref_servo_sg90": ref_servo,
    "ref_servo_horn": ref_horn,
    "ref_hc_sr04": ref_sr04,
    "ref_lcd_st7735s": ref_lcd,
    "ref_esp32_devkit": ref_esp32,
    "ref_18650_holder": ref_cell_holder,
    "ref_usbc_breakout": ref_usbc,
}


# ============================================================================
# PRINT ORIENTATION
# ============================================================================
@dataclass
class PrintPose:
    rot_axis: tuple
    rot_deg: float
    note: str


PRINT_POSES = {
    "01_body": PrintPose((1, 0, 0), 0, "floor on the plate; 45-degree deck needs no supports"),
    "02_front_panel": PrintPose((1, 0, 0), 90, "viewer face on the plate; locators up"),
    "03_roof": PrintPose((1, 0, 0), 180, "top face on the plate; bosses up"),
    "04_rotor_hub": PrintPose((1, 0, 0), 0, "flange on the plate; horn nest bridges"),
    "05_turret_keeper": PrintPose((1, 0, 0), 180, "lip/top face on the plate"),
    "06_sensor_head": PrintPose((1, 0, 0), -90, "face-down; mast lies on the plate"),
    "07_keeper_shim_0p4mm": PrintPose((1, 0, 0), 0, "flat; two layers at 0.2 mm"),
    "08_fit_test_coupon": PrintPose((1, 0, 0), 0, "flat; print this first"),
}

PART_BUILDERS = {
    "01_body": build_body,
    "02_front_panel": build_front_panel,
    "03_roof": build_roof,
    "04_rotor_hub": build_rotor_hub,
    "05_turret_keeper": build_turret_keeper,
    "06_sensor_head": build_sensor_head,
    "07_keeper_shim_0p4mm": build_keeper_shim,
    "08_fit_test_coupon": build_fit_test_coupon,
}

PLATES = {
    "P1": ["01_body", "02_front_panel"],
    "P2": ["03_roof", "04_rotor_hub", "05_turret_keeper", "06_sensor_head", "08_fit_test_coupon"],
}
OPTIONAL_PLATE = {"P3_optional_shim": ["07_keeper_shim_0p4mm"]}
# Build-stage plates (see hardware/diagrams/build_flow.svg): print these first,
# check the fit, adjust VERIFY variables, then print P1 + P2.
STAGE_PLATES = {
    "S1_fit_coupon": ["08_fit_test_coupon"],
    "S2_servo_fit_subset": ["03_roof", "04_rotor_hub", "05_turret_keeper"],
}

A1_MINI_BED = (180.0, 180.0, 180.0)


def tight_bbox(shape) -> tuple:
    """(xmin, xmax, ymin, ymax, zmin, zmax) from a fine tessellation. OCC's
    BoundingBox() can be loose after transforms, which would lift a part off the
    plate; the mesh never is."""
    shp = shape.val() if isinstance(shape, cq.Workplane) else shape
    verts, _ = shp.tessellate(0.02, 0.1)
    xs, ys, zs = [v.x for v in verts], [v.y for v in verts], [v.z for v in verts]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


def to_print_pose(name: str, shape: cq.Workplane) -> cq.Workplane:
    pose = PRINT_POSES[name]
    s = shape
    if pose.rot_deg:
        s = s.rotate((0, 0, 0), pose.rot_axis, pose.rot_deg)
    x0, x1, y0, y1, z0, _ = tight_bbox(s)
    return s.translate((-(x0 + x1) / 2, -(y0 + y1) / 2, -z0))


def build_all() -> dict:
    return {n: f() for n, f in PART_BUILDERS.items()}


if __name__ == "__main__":
    parts = build_all()
    for n, p in parts.items():
        bb = p.val().BoundingBox()
        print(f"{n:24s} {bb.xlen:7.1f} x {bb.ylen:7.1f} x {bb.zlen:7.1f}  valid={p.val().isValid()}")
