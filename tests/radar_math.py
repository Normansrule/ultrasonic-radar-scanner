"""
Reference implementation of every equation in docs/EQUATIONS.md.

The integer maths deliberately mirrors firmware/Radar_V5/Radar_V5.ino (C
integer division truncates), so the tests can check the firmware formulas and
the documentation numbers against one source.
"""
from __future__ import annotations

# ---- values mirrored from the firmware / wiring (checked by test_sync.py) ----
SWEEP_MIN_DEG = 30
SWEEP_MAX_DEG = 150
SWEEP_STEP_DEG = 3
SETTLE_MS = 70
MAX_RANGE_CM = 200.0
AIR_TEMP_C = 20.0
SERVO_FREQ_HZ = 50
SERVO_RES_BITS = 16
SERVO_US_AT_0 = 1000
SERVO_US_AT_180 = 2000
SERVO_US_GUARD_MIN = 900
SERVO_US_GUARD_MAX = 2100
TFT_SPI_HZ = 15_000_000
SCREEN_W, SCREEN_H = 160, 128

R1_OHM = 2200.0
R2_OHM = 3300.0
ESP32_VDD = 3.3
ESP32_VIH = 0.75 * ESP32_VDD      # input-high threshold, ESP32 datasheet DC characteristics
ESP32_VIN_ABS_MAX = ESP32_VDD + 0.3

# ---- ESTIMATES (not measurements) used only for the sweep-cadence figure ----
FRAME_PUSH_MS = SCREEN_W * SCREEN_H * 16 / TFT_SPI_HZ * 1000   # full-frame SPI transfer
DRAW_EST_MS = 3.0                                             # canvas drawing, rough guess
ECHO_TYP_MS = 6.0                                             # ~1 m target round trip
OVERHEAD_EST_MS = FRAME_PUSH_MS + DRAW_EST_MS + ECHO_TYP_MS


def speed_of_sound_mps(temp_c: float = AIR_TEMP_C) -> float:
    """Dry air, linear approximation: v ~= 331.3 + 0.606*T  (T in deg C)."""
    return 331.3 + 0.606 * temp_c


def cm_per_us(temp_c: float = AIR_TEMP_C) -> float:
    return speed_of_sound_mps(temp_c) / 10_000.0


def distance_cm(echo_us: float, temp_c: float = AIR_TEMP_C) -> float:
    """d = v * t / 2  (the pulse goes out AND back)."""
    return echo_us * cm_per_us(temp_c) / 2.0


def echo_time_us(d_cm: float, temp_c: float = AIR_TEMP_C) -> float:
    return 2.0 * d_cm / cm_per_us(temp_c)


def echo_timeout_us(max_cm: float = MAX_RANGE_CM, temp_c: float = AIR_TEMP_C) -> int:
    """Same expression as echoTimeoutUs() in the firmware (float -> uint32 truncation)."""
    return int(2.0 * (max_cm * 1.1) / cm_per_us(temp_c)) + 1000


def divider_vout(vin: float, r1: float = R1_OHM, r2: float = R2_OHM) -> float:
    return vin * r2 / (r1 + r2)


def divider_worst_case(vin: float, tol: float):
    """(low, high) output for resistor tolerance `tol` (0.01 = 1 %)."""
    lo = divider_vout(vin, R1_OHM * (1 + tol), R2_OHM * (1 - tol))
    hi = divider_vout(vin, R1_OHM * (1 - tol), R2_OHM * (1 + tol))
    return lo, hi


def period_us(freq_hz: int = SERVO_FREQ_HZ) -> int:
    return 1_000_000 // freq_hz


def pulse_to_duty(us: int, bits: int = SERVO_RES_BITS, freq_hz: int = SERVO_FREQ_HZ) -> int:
    """Firmware: (uint64)us * (2^bits - 1) / period_us, integer."""
    return us * ((1 << bits) - 1) // period_us(freq_hz)


def angle_to_us(deg: int, us0: int = SERVO_US_AT_0, us180: int = SERVO_US_AT_180,
                reverse: bool = False) -> int:
    deg = max(0, min(180, deg))
    if reverse:
        deg = 180 - deg
    us = us0 + (us180 - us0) * deg // 180
    return max(SERVO_US_GUARD_MIN, min(SERVO_US_GUARD_MAX, us))


def readings_per_pass(step: int = SWEEP_STEP_DEG) -> int:
    return (SWEEP_MAX_DEG - SWEEP_MIN_DEG) // step + 1


def steps_one_way(step: int = SWEEP_STEP_DEG) -> int:
    """Moves between readings on one pass (30 -> 150 is 40 moves of 3 deg)."""
    return (SWEEP_MAX_DEG - SWEEP_MIN_DEG) // step


def step_time_ms(settle_ms: float = SETTLE_MS, overhead_ms: float = OVERHEAD_EST_MS) -> float:
    return settle_ms + overhead_ms


def sweep_one_way_s(step: int = SWEEP_STEP_DEG, settle_ms: float = SETTLE_MS,
                    overhead_ms: float = OVERHEAD_EST_MS) -> float:
    return steps_one_way(step) * step_time_ms(settle_ms, overhead_ms) / 1000.0


def sweep_round_trip_s(step: int = SWEEP_STEP_DEG, settle_ms: float = SETTLE_MS,
                       overhead_ms: float = OVERHEAD_EST_MS) -> float:
    return 2 * sweep_one_way_s(step, settle_ms, overhead_ms)


def display_refresh_hz(settle_ms: float = SETTLE_MS, overhead_ms: float = OVERHEAD_EST_MS) -> float:
    """One full frame is drawn per reading."""
    return 1000.0 / step_time_ms(settle_ms, overhead_ms)


def servo_travel_time_ms(step_deg: float = SWEEP_STEP_DEG, s_per_60deg: float = 0.10) -> float:
    """SG90 datasheet speed ~0.1 s/60 deg (unloaded, 4.8 V)."""
    return step_deg / 60.0 * s_per_60deg * 1000.0
