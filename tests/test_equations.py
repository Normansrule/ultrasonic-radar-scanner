"""Numerical checks of every equation in docs/EQUATIONS.md.
Run: python -m pytest tests/  (or: python tests/test_equations.py)"""
import math

import radar_math as rm


def close(a, b, tol):
    return abs(a - b) <= tol


# 1. ultrasonic distance ------------------------------------------------------
def test_speed_of_sound_20c():
    assert close(rm.speed_of_sound_mps(20.0), 343.42, 0.01)          # textbook ~343 m/s


def test_speed_of_sound_temperature_dependence():
    # 0 C -> 331.3, 35 C -> ~352.5 m/s: about 6 % change over a room-to-hot-day range
    assert close(rm.speed_of_sound_mps(0.0), 331.3, 1e-9)
    assert close(rm.speed_of_sound_mps(35.0), 352.51, 0.01)


def test_distance_worked_example():
    # docs worked example: 5 823 us echo at 20 C -> 100.0 cm
    assert close(rm.distance_cm(5823, 20.0), 100.0, 0.05)
    assert close(rm.echo_time_us(100.0, 20.0), 5823.8, 0.5)


def test_distance_round_trip_inverse():
    for d in (2, 10, 57.3, 150, 200):
        assert close(rm.distance_cm(rm.echo_time_us(d)), d, 1e-9)


def test_temperature_error_if_uncompensated():
    # an echo measured at 35 C but converted with the 20 C constant reads ~2.6 % short
    t = rm.echo_time_us(100.0, 35.0)
    assert close(rm.distance_cm(t, 20.0), 97.42, 0.05)


def test_echo_timeout_matches_firmware_expression():
    # 2 * 220 cm / 0.034342 cm/us + 1000 us
    assert rm.echo_timeout_us(200.0, 20.0) == 13812


# 2. ECHO level ---------------------------------------------------------------
def test_3v3_sensor_echo_needs_no_divider():
    """Default build: the sensor runs from 3.3 V, so ECHO high is at most 3.3 V."""
    assert rm.SENSOR_VCC <= rm.ESP32_VDD < rm.ESP32_VIN_ABS_MAX
    assert rm.SENSOR_VCC * 0.9 > rm.ESP32_VIH        # even a 10 % weak high reads as HIGH


# fallback only: 5 V HC-SR04 + divider
def test_divider_nominal():
    assert close(rm.divider_vout(5.0), 3.0, 1e-9)


def test_divider_worst_case_stays_safe_and_readable():
    lo, hi = rm.divider_worst_case(5.25, 0.01)       # USB high limit, 1 % parts
    assert hi < rm.ESP32_VIN_ABS_MAX                  # never above ~3.6 V
    lo2, _ = rm.divider_worst_case(4.75, 0.01)       # USB low limit
    assert lo2 > rm.ESP32_VIH                         # still a clean logic HIGH (> 2.475 V)
    assert close(hi, 3.18, 0.01) and close(lo2, 2.82, 0.01)


def test_divider_current_is_small():
    i_ma = 5.0 / (rm.R1_OHM + rm.R2_OHM) * 1000
    assert close(i_ma, 0.909, 0.001)                  # < 1 mA from the HC-SR04 output


# 3. servo timing / LEDC duty ---------------------------------------------------
def test_frame_period():
    assert rm.period_us() == 20_000


def test_duty_counts():
    assert rm.pulse_to_duty(1000) == 3276
    assert rm.pulse_to_duty(1500) == 4915
    assert rm.pulse_to_duty(2000) == 6553
    # duty fraction check: 1.5 ms / 20 ms = 7.5 %
    assert close(rm.pulse_to_duty(1500) / 65535, 0.075, 0.0001)


def test_angle_map_defaults():
    assert rm.angle_to_us(0) == 1000
    assert rm.angle_to_us(30) == 1166
    assert rm.angle_to_us(90) == 1500
    assert rm.angle_to_us(150) == 1833
    assert rm.angle_to_us(180) == 2000
    assert rm.angle_to_us(30, reverse=True) == rm.angle_to_us(150)


def test_guard_clamps_bad_calibration():
    assert rm.angle_to_us(180, us0=500, us180=2500) == rm.SERVO_US_GUARD_MAX
    assert rm.angle_to_us(0, us0=500, us180=2500) == rm.SERVO_US_GUARD_MIN


def test_ledc_resolution_is_possible_at_50hz():
    # ESP32 LEDC: f_max_bits = log2(80 MHz / f). 16 bits at 50 Hz needs <= 1.6M ticks.
    assert (1 << rm.SERVO_RES_BITS) <= 80_000_000 / rm.SERVO_FREQ_HZ
    one_count_us = rm.period_us() / 65535
    assert one_count_us < 0.31                        # finer than the servo's ~10 us dead band


# 4. sweep cadence (estimates, labelled as such in the docs) --------------------
def test_sweep_geometry():
    assert rm.readings_per_pass() == 41
    assert rm.steps_one_way() == 40


def test_servo_moves_within_settle():
    # a 3 deg move at ~0.1 s/60 deg takes ~5 ms, well inside the 70 ms settle
    assert rm.servo_travel_time_ms() < rm.SETTLE_MS / 5


def test_settle_exceeds_hcsr04_recommended_cycle():
    # HC-SR04 guidance: >= 60 ms measurement cycle so old echoes die away
    assert rm.SETTLE_MS + rm.OVERHEAD_EST_MS >= 60


def test_cadence_estimate():
    assert close(rm.FRAME_PUSH_MS, 30.72, 0.01)       # 320 x 240 x 16 bit at 40 MHz
    step = rm.step_time_ms()
    assert 105 < step < 125
    assert close(rm.sweep_one_way_s(), 40 * step / 1000, 1e-9)
    assert 4.2 < rm.sweep_one_way_s() < 5.0
    assert 8 < rm.display_refresh_hz() < 10
    # detections must outlive one full round trip so dots persist until revisited
    assert rm.DETECTION_TTL_MS > rm.sweep_round_trip_s() * 1000


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except AssertionError as e:
                fails += 1
                print("FAIL", name, e)
    raise SystemExit(1 if fails else 0)
