"""
Radar V6 "Mini" — CadQuery model of record for the Ultrasonic Radar Scanner.

Three electronic modules, four printed parts, no screws beyond the ones that
come with the servo:

  01_shell    console body: tilted screen opening, roof with the turret hole,
              engraved angle scale, USB hole. Printed roof-down, no supports.
  02_bezel    screen frame that slides into the shell; the Cheap Yellow Display
              (CYD) presses onto four printed pegs on its back. Printed face-down.
  03_base     bottom plate: press-fits into the shell and locks the bezel.
  04_head     "two-eye" sensor head with neck and horn foot. Printed face-down.
  05_fit_coupon  print FIRST: peg, transducer-hole, servo-hole and pilot tests.

Coordinates (assembled, mm): origin at the centre of the footprint on the table.
  +X right (seen from the screen side), +Y towards the scan side (the sensor
  looks along +Y at 90 degrees), +Z up. The screen faces -Y (towards you).

Every dimension is a named variable. VERIFY marks values that depend on the
modules you bought — measure them and print 05_fit_coupon first.
Nothing here has been printed or fitted yet — see docs/VALIDATION.md.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import cadquery as cq

# ============================================================================
# 0. PRINT ALLOWANCES
# ============================================================================
FIT = 0.20                 # general sliding clearance per side
PEG_D = 2.90               # CYD mounting-hole pegs (holes are 3.2 mm). VERIFY with coupon
PILOT_D = 1.80             # pilot for the servo's own self-tapping mounting screws. VERIFY with coupon
CAN_HOLE_D = 16.20         # transducer press-fit holes. VERIFY with coupon (cans are ~16 mm)

# ============================================================================
# 1. PURCHASED MODULES (all VERIFY)
# ============================================================================
# ESP32-2432S028R "Cheap Yellow Display" (landscape, display facing +lz)
CYD_L, CYD_H = 86.6, 50.0          # PCB (community drawing: 86 x 50, holes 78 x 42 apart)
CYD_PCB_T = 1.6
CYD_HOLE_DX, CYD_HOLE_DY = 39.0, 21.0
CYD_HOLE_D = 3.2
CYD_DISP_W, CYD_DISP_H = 69.0, 50.0  # display module on the front
CYD_GLASS_TOP = 5.1                # front of the glass above the PCB back (lz)
CYD_STANDOFF = 3.6                 # bezel back -> PCB front at the holes (glass top 3.5 above PCB front + 0.1)
CYD_VIEW_W, CYD_VIEW_H = 58.0, 43.6  # 2.8" active area 57.6 x 43.2 + margin
CYD_VIEW_DX = -2.5                 # active-area centre vs PCB centre (community STEP model). VERIFY
CYD_BACK_DEPTH = 4.8               # tallest part behind the PCB (connectors)
CYD_USB_LY, CYD_USB_LZ = -9.3, -1.5  # micro-USB at the +X edge (local), VERIFY
USB_HOLE_W, USB_HOLE_H = 15.0, 10.0  # side-wall opening; fits micro-USB and the USB-C of CYD2USB boards

# SG90-size positional servo (TowerPro envelope)
SERVO_BODY_L, SERVO_BODY_W = 22.2, 11.8
SERVO_FLANGE_L, SERVO_FLANGE_T = 32.2, 2.5
SERVO_FLANGE_BELOW = 15.9          # body bottom -> flange underside
SERVO_CASE_ABOVE = 6.8             # flange underside -> top of rectangular case
SERVO_BOSS_ABOVE = 10.8            # flange underside -> top of round gear boss
SERVO_SPLINE_ABOVE = 15.1          # flange underside -> top of output spline
SERVO_BOSS_D = 11.8
SERVO_HOLE_PITCH = 27.5
SERVO_SHAFT_OFFSET = 5.5           # shaft -> body centre along the long axis
HORN_LEN, HORN_ARM_W, HORN_ARM_T = 34.0, 6.2, 1.5
HORN_COLLAR_D = 7.2
HORN_ARM_BELOW_SPLINE = 0.5        # arms sit this far below the spline top

# RCWL-1601 / HC-SR04P ultrasonic sensor (HC-SR04 footprint)
SR04_PCB_L, SR04_PCB_W, SR04_PCB_T = 45.0, 20.0, 1.6
SR04_CAN_D, SR04_CAN_H, SR04_CAN_PITCH = 16.0, 12.0, 26.0
SR04_HEADER_W = 11.0

# ============================================================================
# 2. 01_SHELL
# ============================================================================
W, D, H = 104.0, 96.0, 62.0        # width, depth, height
TILT_DEG = 20.0                    # screen leans back from vertical
WALL, TOP = 2.4, 2.4
R_REAR = 12.0                      # rounded rear corners (plan)
R_FRONT = 5.0                      # front corners
CH_ROOF = 3.5                      # 45-degree roof chamfer (prints on the bed without overhang)
CH_BOTTOM = 0.8
Y_TURRET = 16.0                    # turret axis
TURRET_HOLE_D = 13.0               # gear boss + spline pass through, nothing else shows
SERVO_BOSS_H = 6.0                 # bosses under the roof; servo hangs from them
SERVO_BOSS_DIA = 4.6                # must clear the servo case (hole pitch/2 - case/2 = 2.65 mm)
WIRE_SLOT = (12.0, 5.5)            # sensor cable pass-through
WIRE_SLOT_R = 27.0                 # distance from the turret axis towards the screen
TICK_R0, TICK_R1 = 30.5, 36.0      # engraved angle scale on the roof
ENGRAVE = 0.6

# ============================================================================
# 3. 02_BEZEL
# ============================================================================
RECESS = 3.0                       # bezel sits this far behind the shell front edge (a deep frame)
BEZEL_T = 2.4
GROOVE_D, GROOVE_CLR = 1.0, 0.25   # side-wall grooves the bezel slides into
BEZEL_BOTTOM_Z = 2.6               # bezel bottom edge rests on the base plate
BEZEL_TOP_GAP = 0.2
WINDOW_CHAMFER = 1.2
CYD_V_OFFSET = 4.0                 # board centre above the bezel's mid-height (leaves a chin for the label)

# ============================================================================
# 4. 03_BASE
# ============================================================================
BASE_T = 2.4
BASE_CLR = 0.15
BASE_RIM_H, BASE_RIM_T = 5.0, 1.6
BASE_RIM_SIDE_FROM_Y = -8.0        # side rims start here (clear of the screen area)

# ============================================================================
# 5. 04_HEAD
# ============================================================================
HEAD_W, HEAD_H = 56.0, 30.0
HEAD_R = 9.0
HEAD_DEPTH = 15.0                  # open-backed visor
HEAD_FACE_T = 2.4
HEAD_AXIS_BEHIND_FACE = 10.0       # rotation axis sits this far behind the face (towards you)
NECK = 10.0                        # square neck
NECK_GAP = 5.0                     # foot top -> head bottom
FOOT_L, FOOT_D, FOOT_T = 36.0, 20.0, 4.5
HORN_SLOT_CLR = 0.15               # tight: the horn is pressed into the foot. VERIFY

# ============================================================================
# 6. 05_FIT_COUPON
# ============================================================================
COUPON_W, COUPON_D, COUPON_T = 92.0, 42.0, 3.0
COUPON_PEGS = (2.8, 2.9, 3.0)
COUPON_CANS = (16.0, 16.2, 16.4)
COUPON_PILOTS = (1.6, 1.8, 2.0)

# ============================================================================
# DERIVED
# ============================================================================
T = math.radians(TILT_DEG)
Y_FRONT0 = -D / 2                  # front edge on the table
Z_ROOF_IN = H - TOP
Z_FLANGE_TOP = Z_ROOF_IN - SERVO_BOSS_H
Z_FLANGE_BOT = Z_FLANGE_TOP - SERVO_FLANGE_T
Z_SPLINE_TOP = Z_FLANGE_BOT + SERVO_SPLINE_ABOVE
Z_HORN_ARM0 = Z_SPLINE_TOP - HORN_ARM_BELOW_SPLINE
Z_FOOT0 = Z_HORN_ARM0
Z_FOOT1 = Z_FOOT0 + FOOT_T
Z_HEAD0 = Z_FOOT1 + NECK_GAP
Y_FACE = Y_TURRET + HEAD_AXIS_BEHIND_FACE
SERVO_CY = Y_TURRET + SERVO_SHAFT_OFFSET  # servo long axis runs along Y

PART_NAMES = ["01_shell", "02_bezel", "03_base", "04_head", "05_fit_coupon"]
REQUIRED_PARTS = PART_NAMES[:4]


# ============================================================================
# helpers
# ============================================================================
def box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def cyl_z(x, y, z0, h, d) -> cq.Workplane:
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(d / 2).extrude(h)


def cyl_y(x, z, y0, length, d) -> cq.Workplane:
    return cq.Workplane("XZ", origin=(0, y0, 0)).center(x, z).circle(d / 2).extrude(-length)


def cyl_x(y, z, x0, length, d) -> cq.Workplane:
    return cq.Workplane("YZ", origin=(x0, 0, 0)).center(y, z).circle(d / 2).extrude(length)


def front_y(z: float, inset: float = 0.0) -> float:
    """Y of the (outer) front face at height z, moved `inset` mm inwards along its normal."""
    return Y_FRONT0 + z * math.tan(T) + inset / math.cos(T)


def to_screen_frame(wp: cq.Workplane, inset: float) -> cq.Workplane:
    """Map a solid built in the screen frame — X across, +Y up the slope, +Z out of the
    screen — onto the tilted plane that lies `inset` mm inside the front face."""
    return (wp.rotate((0, 0, 0), (1, 0, 0), 90 - TILT_DEG)
              .translate((0, front_y(0, inset), 0)))


def bezel_v_range():
    """Slope coordinate (v) of the bezel's bottom and top edges."""
    v0 = (BEZEL_BOTTOM_Z + BEZEL_T * math.sin(T)) / math.cos(T)
    v1 = (Z_ROOF_IN - BEZEL_TOP_GAP) / math.cos(T)
    return v0, v1


def cyd_center_v():
    v0, v1 = bezel_v_range()
    return (v0 + v1) / 2 + CYD_V_OFFSET


def rounded_slab(w, h, t, r) -> cq.Workplane:
    return cq.Workplane("XY").rect(w, h).extrude(t).edges("|Z").fillet(r)


# ============================================================================
# 01 SHELL
# ============================================================================
def outer_body() -> cq.Workplane:
    y_ft = front_y(H)
    prof = (cq.Workplane("YZ").polyline([(Y_FRONT0, 0), (D / 2, 0), (D / 2, H), (y_ft, H)]).close()
            .extrude(W / 2, both=True))
    s = prof.val()
    rear, front = [], []
    for e in s.Edges():
        c = e.Center()
        p0, p1 = e.startPoint(), e.endPoint()
        if abs(abs(c.x) - W / 2) > 1e-3 or abs(p0.z - p1.z) < 1e-6:
            continue  # only the side-face edges that are not horizontal
        (rear if c.y > 0 else front).append(e)
    s = s.fillet(R_REAR, rear)
    s = s.fillet(R_FRONT, front)
    wp = cq.Workplane("XY").add(s)
    wp = wp.faces(">Z").edges().chamfer(CH_ROOF)
    wp = wp.faces("<Z").edges().chamfer(CH_BOTTOM)
    return wp


def build_shell() -> cq.Workplane:
    body = outer_body()
    # cavity: open bottom and open front (the bezel closes the front)
    ix, iy = W / 2 - WALL, D / 2 - WALL
    cav = (cq.Workplane("XY").workplane(offset=-1)
           .center(0, (iy + Y_FRONT0 - 20) / 2).rect(2 * ix, iy - (Y_FRONT0 - 20)).extrude(Z_ROOF_IN + 1)
           .edges("|Z and >Y").fillet(R_REAR - WALL))
    body = body.cut(cav)
    # bezel grooves in the side walls (open at the bottom)
    v0, v1 = bezel_v_range()
    for sx in (-1, 1):
        xa, xb = sorted((sx * (ix - 1.0), sx * (ix + GROOVE_D)))
        g = box(xa, xb, -10, v1 + 10, -BEZEL_T - GROOVE_CLR, GROOVE_CLR)
        body = body.cut(to_screen_frame(g, RECESS).intersect(box(-W, W, -D, D, -1, Z_ROOF_IN)))
    # turret hole, servo bosses (hang from the roof), wire slot
    body = body.cut(cyl_z(0, Y_TURRET, Z_ROOF_IN - 1, TOP + 2, TURRET_HOLE_D))
    for sy in (-1, 1):
        yb = SERVO_CY + sy * SERVO_HOLE_PITCH / 2
        body = body.union(cyl_z(0, yb, Z_FLANGE_TOP, SERVO_BOSS_H + 0.01, SERVO_BOSS_DIA))
        body = body.cut(cyl_z(0, yb, Z_FLANGE_TOP - 0.01, SERVO_BOSS_H - 0.6, PILOT_D))
    slot = (cq.Workplane("XY").workplane(offset=Z_ROOF_IN - 1).center(0, Y_TURRET - WIRE_SLOT_R)
            .slot2D(WIRE_SLOT[0], WIRE_SLOT[1]).extrude(TOP + 2))
    body = body.cut(slot)
    # engraved angle scale: ticks every 15 deg (major every 30) for the commanded 30..150 deg
    for deg in range(30, 151, 15):
        major = deg % 30 == 0
        r0 = TICK_R0 if major else TICK_R0 + 2.0
        tick = (cq.Workplane("XY").workplane(offset=H - ENGRAVE).rect(TICK_R1 - r0, 0.9 if major else 0.7)
                .extrude(ENGRAVE + 1).translate(((TICK_R1 + r0) / 2, 0, 0))
                .rotate((0, 0, 0), (0, 0, 1), deg).translate((0, Y_TURRET, 0)))
        body = body.cut(tick)
    try:
        for deg in (30, 90, 150):
            a = math.radians(deg)
            r = TICK_R1 + 4.2
            t = (cq.Workplane("XY").workplane(offset=H).center(r * math.cos(a), Y_TURRET + r * math.sin(a))
                 .text(str(deg), 3.6, -ENGRAVE, kind="bold", halign="center", valign="center"))
            body = body.cut(t)
        rear = cq.Plane(origin=(0, D / 2 + 0.01, 0), xDir=(-1, 0, 0), normal=(0, 1, 0))
        for txt, z, size in (("ULTRASONIC RADAR SCANNER", 40.0, 4.2), ("educational sonar - not a safety device", 32.0, 3.2)):
            body = body.cut(cq.Workplane(rear).center(0, z).text(txt, size, -ENGRAVE, kind="regular",
                                                                    halign="center", valign="center"))
    except Exception:  # fonts differ between machines; engraving is cosmetic
        pass
    # USB opening in the right side wall, in line with the CYD's USB socket
    ux, uy, uz = cyd_to_world(CYD_L / 2, CYD_USB_LY, CYD_USB_LZ)
    hole = (cq.Workplane("YZ", origin=(W / 2 - WALL - 1, 0, 0)).center(uy, uz)
            .rect(USB_HOLE_W, USB_HOLE_H).extrude(WALL + 2).edges("|X").fillet(2.5))
    body = body.cut(hole)
    return body


# ============================================================================
# 02 BEZEL (+ CYD placement)
# ============================================================================
def cyd_local_to_screen(lx, ly, lz):
    """CYD local (PCB centre, lz = 0 at the PCB back, display towards +lz) -> screen frame."""
    return (lx, cyd_center_v() + ly, -BEZEL_T - CYD_STANDOFF + (lz - CYD_PCB_T))


def cyd_to_world(lx, ly, lz):
    x, v, z = cyd_local_to_screen(lx, ly, lz)
    y0 = front_y(0, RECESS)
    return x, y0 + v * math.sin(T) - z * math.cos(T), v * math.cos(T) + z * math.sin(T)


def build_bezel() -> cq.Workplane:
    v0, v1 = bezel_v_range()
    bw = 2 * (W / 2 - WALL + GROOVE_D - GROOVE_CLR)
    plate = (cq.Workplane("XY").workplane(offset=-BEZEL_T).center(0, (v0 + v1) / 2)
             .rect(bw, v1 - v0).extrude(BEZEL_T))
    vc = cyd_center_v()
    # display window with a 45-degree chamfer on the viewer side
    win = cq.Workplane("XY").workplane(offset=-BEZEL_T - 1).center(CYD_VIEW_DX, vc).rect(CYD_VIEW_W, CYD_VIEW_H).extrude(BEZEL_T + 2)
    win = win.edges("|Z").fillet(1.5)
    plate = plate.cut(win)
    ch = (cq.Workplane("XY").workplane(offset=0.001).center(CYD_VIEW_DX, vc)
          .rect(CYD_VIEW_W + 2 * WINDOW_CHAMFER, CYD_VIEW_H + 2 * WINDOW_CHAMFER)
          .workplane(offset=-WINDOW_CHAMFER).rect(CYD_VIEW_W, CYD_VIEW_H).loft(ruled=True))
    plate = plate.cut(ch)
    # four pegs on the back that the CYD's mounting holes press onto
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * CYD_HOLE_DX, vc + sy * CYD_HOLE_DY
            plate = plate.union(cq.Workplane("XY").workplane(offset=-BEZEL_T - CYD_STANDOFF).center(x, y)
                                .circle(3.2).extrude(CYD_STANDOFF + 0.01))
            plate = plate.union(cq.Workplane("XY").workplane(offset=-BEZEL_T - CYD_STANDOFF - CYD_PCB_T - 0.8)
                                .center(x, y).circle(PEG_D / 2).extrude(CYD_PCB_T + 0.81)
                                .faces("<Z").chamfer(0.35))
    try:  # engraved label on the chin (cosmetic)
        chin = (v0 + vc - CYD_H / 2) / 2
        plate = plate.cut(cq.Workplane("XY").center(0, chin).text("SONAR", 4.2, -0.5, kind="bold",
                                                                    halign="center", valign="center"))
    except Exception:
        pass
    return to_screen_frame(plate, RECESS)


# ============================================================================
# 03 BASE
# ============================================================================
def build_base() -> cq.Workplane:
    ix, iy = W / 2 - WALL - BASE_CLR, D / 2 - WALL - BASE_CLR
    yf = front_y(BASE_T, RECESS) - 0.4    # just under the bezel's front face
    plate = (cq.Workplane("XY").center(0, (iy + yf) / 2).rect(2 * ix, iy - yf).extrude(BASE_T)
             .edges("|Z and >Y").fillet(R_REAR - WALL - BASE_CLR))
    # press-fit rim along the rear and the rear half of the sides
    rim_out = (cq.Workplane("XY").workplane(offset=BASE_T - 0.01).center(0, (iy + BASE_RIM_SIDE_FROM_Y) / 2)
               .rect(2 * ix, iy - BASE_RIM_SIDE_FROM_Y).extrude(BASE_RIM_H).edges("|Z and >Y").fillet(R_REAR - WALL - BASE_CLR))
    rim_in = (cq.Workplane("XY").workplane(offset=BASE_T - 1).center(0, (iy - BASE_RIM_T + BASE_RIM_SIDE_FROM_Y - 5) / 2)
              .rect(2 * (ix - BASE_RIM_T), iy - BASE_RIM_T - (BASE_RIM_SIDE_FROM_Y - 5)).extrude(BASE_RIM_H + 2)
              .edges("|Z and >Y").fillet(max(R_REAR - WALL - BASE_CLR - BASE_RIM_T, 1.0)))
    plate = plate.union(rim_out.cut(rim_in))
    # crush ribs on the rim give the press fit (sand them if it is too tight)
    for sx in (-1, 1):
        xa, xb = sorted((sx * (ix - 0.01), sx * (ix + 0.3)))
        plate = plate.union(box(xa, xb, 10, 14, BASE_T, BASE_T + BASE_RIM_H))
    plate = plate.union(box(-2, 2, iy - 0.01, iy + 0.3, BASE_T, BASE_T + BASE_RIM_H))
    return plate


# ============================================================================
# 04 HEAD
# ============================================================================
def build_head() -> cq.Workplane:
    zc = Z_HEAD0 + HEAD_H / 2
    face = (cq.Workplane("XZ", origin=(0, Y_FACE, 0)).center(0, zc).rect(HEAD_W, HEAD_H).extrude(HEAD_DEPTH)
            .edges("|Y").fillet(HEAD_R))
    inner = (cq.Workplane("XZ", origin=(0, Y_FACE - HEAD_FACE_T, 0)).center(0, zc)
             .rect(HEAD_W - 2 * HEAD_FACE_T, HEAD_H - 2 * HEAD_FACE_T).extrude(HEAD_DEPTH)
             .edges("|Y").fillet(HEAD_R - HEAD_FACE_T))
    head = face.cut(inner)
    for sx in (-1, 1):
        head = head.cut(cyl_y(sx * SR04_CAN_PITCH / 2, zc, Y_FACE - HEAD_DEPTH - 1, HEAD_DEPTH + 2, CAN_HOLE_D))
    # header notch in the bottom wall, behind the neck
    head = head.cut(box(-SR04_HEADER_W / 2, SR04_HEADER_W / 2, Y_FACE - HEAD_DEPTH - 1, Y_FACE - NECK - 0.5,
                        Z_HEAD0 - 1, Z_HEAD0 + HEAD_FACE_T + 1))
    # neck (coplanar with the face so the part prints face-down without supports)
    head = head.union(box(-NECK / 2, NECK / 2, Y_FACE - NECK, Y_FACE, Z_FOOT1 - 0.01, Z_HEAD0 + 0.5))
    # foot: holds the servo horn, centred on the turret axis
    foot = box(-FOOT_L / 2, FOOT_L / 2, Y_TURRET - FOOT_D / 2, Y_TURRET + FOOT_D / 2, Z_FOOT0, Z_FOOT1)
    foot = foot.edges("|Z").chamfer(2.0)
    hw, hl = HORN_ARM_W + 2 * HORN_SLOT_CLR, HORN_LEN + 2 * HORN_SLOT_CLR
    foot = foot.cut(box(-hl / 2, hl / 2, Y_TURRET - hw / 2, Y_TURRET + hw / 2, Z_FOOT0 - 1, Z_FOOT0 + HORN_ARM_T + 0.3))
    foot = foot.cut(cyl_z(0, Y_TURRET, Z_FOOT0 - 1, HORN_ARM_T + 1.3, HORN_COLLAR_D + 0.4))
    foot = foot.cut(cyl_z(0, Y_TURRET, Z_FOOT0 - 1, FOOT_T + 2, 5.5))  # screwdriver access to the horn screw
    return head.union(foot)


# ============================================================================
# 05 FIT COUPON
# ============================================================================
def build_fit_coupon() -> cq.Workplane:
    c = cq.Workplane("XY").rect(COUPON_W, COUPON_D).extrude(COUPON_T).edges("|Z").fillet(3.0)
    x0 = -COUPON_W / 2
    for i, d in enumerate(COUPON_CANS):          # transducer holes
        c = c.cut(cyl_z(x0 + 12 + i * 19, 8, -1, COUPON_T + 2, d))
    c = c.cut(cyl_z(x0 + 12 + 3 * 19 + 3, 8, -1, COUPON_T + 2, TURRET_HOLE_D))  # turret hole
    for i, d in enumerate(COUPON_PILOTS):        # servo screw pilots
        c = c.cut(cyl_z(x0 + 10 + i * 9, -12, -1, COUPON_T + 2, d))
    for i, d in enumerate(COUPON_PEGS):          # CYD pegs (stand-offs + pins)
        x = x0 + 46 + i * 12
        c = c.union(cyl_z(x, -12, COUPON_T - 0.01, CYD_STANDOFF, 6.4))
        c = c.union(cyl_z(x, -12, COUPON_T + CYD_STANDOFF - 0.01, CYD_PCB_T + 0.8, d).faces(">Z").chamfer(0.35))
    try:
        c = c.cut(cq.Workplane("XY").workplane(offset=COUPON_T).center(x0 + 80, -12)
                  .text("V6", 5, -0.5, kind="bold", halign="center", valign="center"))
    except Exception:
        pass
    return c


# ============================================================================
# REFERENCE ENVELOPES (not printed: fit checks and renders)
# ============================================================================
def ref_cyd() -> cq.Workplane:
    vc = cyd_center_v()

    def sb(x0, x1, y0, y1, z0, z1):  # box in CYD local -> screen frame
        _, v0, s0 = cyd_local_to_screen(0, y0, z0)
        _, v1, s1 = cyd_local_to_screen(0, y1, z1)
        return box(x0, x1, v0, v1, s0, s1)
    pcb = sb(-CYD_L / 2, CYD_L / 2, -CYD_H / 2, CYD_H / 2, 0, CYD_PCB_T)
    for sx in (-1, 1):
        for sy in (-1, 1):
            _, v, s = cyd_local_to_screen(0, sy * CYD_HOLE_DY, 0)
            pcb = pcb.cut(cq.Workplane("XY").workplane(offset=s - 1).center(sx * CYD_HOLE_DX, v)
                          .circle(CYD_HOLE_D / 2).extrude(CYD_PCB_T + 2))
    disp = sb(-CYD_DISP_W / 2, CYD_DISP_W / 2, -CYD_DISP_H / 2, CYD_DISP_H / 2, CYD_PCB_T, CYD_GLASS_TOP - 0.05)
    back = sb(-36, 36, -19, 19, -CYD_BACK_DEPTH, 0.01)
    usb = sb(CYD_L / 2 - 6, CYD_L / 2 + 0.6, CYD_USB_LY - 4, CYD_USB_LY + 4, -3.0, 0.0)
    _ = vc
    return to_screen_frame(pcb.union(disp).union(back).union(usb), RECESS)


def ref_servo() -> cq.Workplane:
    yc = SERVO_CY
    b = box(-SERVO_BODY_W / 2, SERVO_BODY_W / 2, yc - SERVO_BODY_L / 2, yc + SERVO_BODY_L / 2,
            Z_FLANGE_BOT - SERVO_FLANGE_BELOW, Z_FLANGE_BOT + SERVO_CASE_ABOVE)
    b = b.union(box(-SERVO_BODY_W / 2, SERVO_BODY_W / 2, yc - SERVO_FLANGE_L / 2, yc + SERVO_FLANGE_L / 2,
                    Z_FLANGE_BOT, Z_FLANGE_TOP))
    for sy in (-1, 1):  # flange screw holes
        b = b.cut(cyl_z(0, yc + sy * SERVO_HOLE_PITCH / 2, Z_FLANGE_BOT - 1, SERVO_FLANGE_T + 2, 2.4))
    b = b.union(cyl_z(0, Y_TURRET, Z_FLANGE_BOT + SERVO_CASE_ABOVE - 0.01, SERVO_BOSS_ABOVE - SERVO_CASE_ABOVE, SERVO_BOSS_D))
    b = b.union(cyl_z(0, Y_TURRET, Z_FLANGE_BOT + SERVO_BOSS_ABOVE - 0.01, Z_HORN_ARM0 - Z_FLANGE_BOT - SERVO_BOSS_ABOVE, 4.8))
    return b


def ref_horn() -> cq.Workplane:
    arms = box(-HORN_LEN / 2, HORN_LEN / 2, Y_TURRET - HORN_ARM_W / 2 + 0.6, Y_TURRET + HORN_ARM_W / 2 - 0.6,
               Z_HORN_ARM0, Z_HORN_ARM0 + HORN_ARM_T)
    return arms.union(cyl_z(0, Y_TURRET, Z_HORN_ARM0 - 2.4, 2.4 + HORN_ARM_T, HORN_COLLAR_D))


def ref_sensor_parts() -> dict:
    zc = Z_HEAD0 + HEAD_H / 2
    y_pcb_front = Y_FACE - SR04_CAN_H + 0.6
    pcb = box(-SR04_PCB_L / 2, SR04_PCB_L / 2, y_pcb_front - SR04_PCB_T, y_pcb_front, zc - SR04_PCB_W / 2, zc + SR04_PCB_W / 2)
    cans = None
    for sx in (-1, 1):
        c = cyl_y(sx * SR04_CAN_PITCH / 2, zc, y_pcb_front - 0.01, SR04_CAN_H - 0.6 - 0.2, SR04_CAN_D)
        cans = c if cans is None else cans.union(c)
    # 4-pin header pointing down, through the notch in the head's bottom wall
    header = box(-5.1, 5.1, y_pcb_front - SR04_PCB_T - 2.5, y_pcb_front - SR04_PCB_T, zc - SR04_PCB_W / 2 - 8.5,
                 zc - SR04_PCB_W / 2 + 0.01)
    return {"pcb": pcb, "cans": cans, "header": header}


def ref_sensor() -> cq.Workplane:
    p = ref_sensor_parts()
    return p["pcb"].union(p["cans"]).union(p["header"])


REFERENCE_BUILDERS = {
    "ref_cyd": ref_cyd,
    "ref_servo_sg90": ref_servo,
    "ref_servo_horn": ref_horn,
    "ref_sensor": ref_sensor,
}

# ============================================================================
# CHECKS, PRINT POSES, PLATES (used by scripts/render_cad.py)
# ============================================================================
NOMINAL = {  # print-pose bounding boxes the design promises (sorted dims, mm, +/-0.6)
    "01_shell": (W, D - 1.1, H),   # the open front's rounded wall ends sit ~1.1 mm behind the footprint line
    "05_fit_coupon": (COUPON_W, COUPON_D, COUPON_T + CYD_STANDOFF + CYD_PCB_T + 0.8),
}
INTERFERENCE_PAIRS = [
    ("01_shell", "02_bezel"), ("01_shell", "03_base"), ("02_bezel", "03_base"), ("01_shell", "04_head"),
    ("01_shell", "ref_servo_sg90"), ("01_shell", "ref_cyd"), ("03_base", "ref_cyd"), ("03_base", "ref_servo_sg90"),
    ("ref_cyd", "ref_servo_sg90"), ("02_bezel", "ref_servo_sg90"), ("04_head", "ref_sensor"),
    ("04_head", "ref_servo_sg90"), ("04_head", "ref_servo_horn"),
]
# designed press fits: overlap expected up to this volume (mm^3)
INTERFERENCE_ALLOW = {("01_shell", "03_base"): 20.0}   # three 0.3 mm crush ribs on the base rim
# the pegs pass through the CYD's holes; checked separately
PEG_PAIR = ("02_bezel", "ref_cyd")
SWEEP_MOVERS = {"head+sensor": ["04_head", "ref_sensor"], "horn": ["ref_servo_horn"]}
SWEEP_FIXED = ["01_shell", "ref_servo_sg90"]
SWEEP_AXIS = (0.0, Y_TURRET)
SWEEP_MARGIN_DEG = 75


@dataclass
class PrintPose:
    rot_axis: tuple
    rot_deg: float
    note: str


PRINT_POSES = {
    "01_shell": PrintPose((1, 0, 0), 180, "roof on the plate; 45-degree chamfers, no supports"),
    "02_bezel": PrintPose((1, 0, 0), -(90 - TILT_DEG) + 180, "viewer face on the plate; pegs up"),
    "03_base": PrintPose((1, 0, 0), 0, "flat; rim up"),
    "04_head": PrintPose((1, 0, 0), -90, "face on the plate; neck and foot lie flat"),
    "05_fit_coupon": PrintPose((1, 0, 0), 0, "flat; print this first"),
}
PLATES = {"P1": ["01_shell"], "P2": ["02_bezel", "03_base", "04_head"]}
OPTIONAL_PLATE = {}
STAGE_PLATES = {"S1_fit_coupon": ["05_fit_coupon"]}
A1_MINI_BED = (180.0, 180.0, 180.0)

PART_BUILDERS = {
    "01_shell": build_shell,
    "02_bezel": build_bezel,
    "03_base": build_base,
    "04_head": build_head,
    "05_fit_coupon": build_fit_coupon,
}


def tight_bbox(shape) -> tuple:
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
    for n, p in build_all().items():
        x0, x1, y0, y1, z0, z1 = tight_bbox(p)
        print(f"{n:16s} {x1 - x0:7.1f} x {y1 - y0:7.1f} x {z1 - z0:7.1f}  valid={p.val().isValid()} solids={len(p.solids().vals())}")
