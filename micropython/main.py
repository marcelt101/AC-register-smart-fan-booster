# Vent booster fans - standalone "set and forget" firmware (MicroPython)
#
# Runs on any Raspberry Pi Pico (Pico, Pico W, Pico 2, Pico 2 W) on the
# vent_fans PCB. No Wi-Fi, no Home Assistant, nothing to compile: put the
# MicroPython .uf2 on the Pico once, then copy this file onto it as main.py.
#
# How it decides:
#   The DS18B20 probe in the duct watches the supply air.
#   Fans ON  when the air is hotter than the heating threshold (furnace) or
#            colder than the cooling threshold (AC) for ON_DELAY_S seconds.
#   Fans OFF when it has been back between them (minus HYSTERESIS) for
#            OFF_DELAY_S seconds. The fans can't fool this: they move air but
#            can't make it hot or cold.
#
# Set-up, once:
#   SPEED : override switch to ON, turn the SPEED trimpot until the fans are
#           quiet enough, switch back to the centre (AUTO).
#   LEARN : while the furnace is heating, press LEARN (LED blinks 3x).
#           In summer, while the AC is cooling, press LEARN (LED blinks 2x).
#           Each sets that threshold halfway between the duct's resting
#           temperature and the current one, saved in settings.json.
#           Hold LEARN 5 s to go back to the defaults (5 blinks).
#           10 blinks = not hot/cold enough to learn yet (or no probe).
#
# Status LED: off = idle, on = fans running, slow blink = no probe found.
#
# To edit this file later: hold LEARN while plugging the Pico in. The program
# then doesn't start (LED flashes 3x), so Thonny can connect.

import json

try:  # MicroPython
    from time import ticks_ms, ticks_diff, sleep_ms
except ImportError:  # CPython, for the PC simulation in test_sim.py
    import time as _time

    def ticks_ms():
        return int(_time.monotonic() * 1000)

    def ticks_diff(a, b):
        return a - b

    def sleep_ms(ms):
        _time.sleep(ms / 1000)

# ---- Settings you may want to change --------------------------------------
HEAT_DEFAULT = 32.0      # deg C (90 F) until you press LEARN while heating
COOL_DEFAULT = 16.0      # deg C (61 F) until you press LEARN while cooling
HYSTERESIS = 2.0         # deg C margin before turning off again
ON_DELAY_S = 20          # seconds past a threshold before the fans start
OFF_DELAY_S = 60         # seconds back to normal before the fans stop
MIN_LEVEL = 0.55         # lowest PWM (~2.7 V on the fans) so they always start
PWM_FREQ = 40_000        # Hz; the L1/C3 filter on the board is sized for this
SLEW_PER_TICK = 0.02     # soft start: 2 % per 20 ms (0 -> 100 % in 1 s)
LEARN_HEAT_MIN = 5.0     # duct must be this much above resting to learn heating
LEARN_COOL_MIN = 4.0     # ... or this much below resting to learn cooling
IDLE_TAU_S = 1800        # resting temperature follows slowly (~30 min)
LOG_EVERY_S = 30         # print status to the USB serial console
SETTINGS_FILE = "settings.json"

# ---- Pins (same on Pico, Pico W, Pico 2, Pico 2 W) --------------------------
PIN_FAN_PWM = 15         # Q1 gate (low-side buck)
PIN_ONEWIRE = 16         # J5, DS18B20 duct probe
PIN_SW_OFF = 17          # J6 pin 3, override switch "force off" (to GND)
PIN_SW_ON = 18           # J6 pin 1, override switch "force on" (to GND)
PIN_LEARN = 12           # SW2 LEARN button (to GND)
PIN_LED = 10             # D3 status LED
PIN_POT = 26             # RV1 speed trimpot wiper (ADC0)


def load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            s = json.load(f)
        return {"heat": float(s["heat"]), "cool": float(s["cool"])}
    except Exception:
        return {"heat": HEAT_DEFAULT, "cool": COOL_DEFAULT}


def save_settings(s):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f)


class Controller:
    """All the decisions, with no hardware in it (so it can be tested on a PC)."""

    def __init__(self, heat, cool):
        self.heat = heat
        self.cool = cool
        self.idle = 20.0         # duct resting temperature
        self.idle_ok = False
        self.running = False
        self.on_count = 0
        self.off_count = 0

    def step(self, t, pot, force_on, force_off):
        """Call once a second. t = duct deg C or None, pot = 0..1.
        Returns the fan level 0..1."""
        have = t is not None

        # Track the resting temperature while nothing is running.
        if have and not self.running:
            if not self.idle_ok:
                if self.cool < t < self.heat:
                    self.idle = t
                    self.idle_ok = True
            elif self.cool + HYSTERESIS < t < self.heat - HYSTERESIS:
                self.idle += (t - self.idle) / IDLE_TAU_S

        # Heating / cooling detection with on and off delays.
        if not have:
            self.running = False
            self.on_count = self.off_count = 0
        elif not self.running:
            active = t >= self.heat or t <= self.cool
            self.on_count = self.on_count + 1 if active else 0
            if self.on_count >= ON_DELAY_S:
                self.running = True
                self.off_count = 0
        else:
            back = (self.cool + HYSTERESIS) < t < (self.heat - HYSTERESIS)
            self.off_count = self.off_count + 1 if back else 0
            if self.off_count >= OFF_DELAY_S:
                self.running = False
                self.on_count = 0

        # Speed from the trimpot, then the override switch has the last word.
        pot = 0.6 if pot is None else max(0.0, min(1.0, pot))
        level = MIN_LEVEL + (1.0 - MIN_LEVEL) * pot
        if force_on:
            return level
        if force_off:
            return 0.0
        return level if self.running else 0.0

    def learn(self, t):
        """LEARN pressed. Returns ("heat"|"cool", new value) or (None, reason)."""
        if t is None:
            return None, "no probe"
        if not self.idle_ok:
            return None, "resting temperature not known yet"
        if t >= self.idle + LEARN_HEAT_MIN:
            self.heat = (self.idle + t) / 2
            return "heat", self.heat
        if t <= self.idle - LEARN_COOL_MIN:
            self.cool = (self.idle + t) / 2
            return "cool", self.cool
        return None, "duct %.1f C too close to resting %.1f C" % (t, self.idle)


def run():
    from machine import Pin, PWM, ADC, WDT
    import onewire
    import ds18x20

    led = Pin(PIN_LED, Pin.OUT, value=0)
    learn_btn = Pin(PIN_LEARN, Pin.IN, Pin.PULL_UP)

    # Safe mode: LEARN held at power-up -> don't start (so Thonny can connect).
    if learn_btn.value() == 0:
        print("LEARN held at power-up: safe mode, fan program not started.")
        for _ in range(6):
            led.toggle()
            sleep_ms(150)
        return

    pwm = PWM(Pin(PIN_FAN_PWM))
    pwm.freq(PWM_FREQ)
    pwm.duty_u16(0)
    sw_on = Pin(PIN_SW_ON, Pin.IN, Pin.PULL_UP)
    sw_off = Pin(PIN_SW_OFF, Pin.IN, Pin.PULL_UP)
    pot_adc = ADC(PIN_POT)
    ds = ds18x20.DS18X20(onewire.OneWire(Pin(PIN_ONEWIRE)))

    settings = load_settings()
    ctl = Controller(settings["heat"], settings["cool"])
    print("Vent fans standalone: heat >= %.1f C, cool <= %.1f C" % (ctl.heat, ctl.cool))

    wdt = WDT(timeout=8000)   # if anything ever hangs, the Pico restarts itself

    roms = []
    temp = None
    conv_at = None
    pot = None
    actual = target = 0.0
    blink = 0
    led_n = 0
    btn_state, btn_changed, btn_down_at = 1, ticks_ms(), None
    t_ctrl = t_slew = t_led = ticks_ms()
    log_s = 0

    while True:
        now = ticks_ms()
        wdt.feed()

        # DS18B20: start a conversion, read it ~0.8 s later.
        if conv_at is None:
            try:
                if not roms:
                    roms = ds.scan()
                if roms:
                    ds.convert_temp()
                    conv_at = now
                else:
                    temp = None
            except Exception:
                roms, temp = [], None
        elif ticks_diff(now, conv_at) >= 800:
            try:
                v = ds.read_temp(roms[0])
                if v is not None and v != 85.0 and -55 <= v <= 125:
                    temp = v          # 85.0 is the power-on value, not a reading
            except Exception:
                roms, temp = [], None
            conv_at = None

        # Trimpot, smoothed.
        raw = pot_adc.read_u16() / 65535
        pot = raw if pot is None else pot + (raw - pot) * 0.05

        # LEARN button: short press = learn, hold 5 s = reset to defaults.
        b = learn_btn.value()
        if b != btn_state and ticks_diff(now, btn_changed) > 30:
            btn_state, btn_changed = b, now
            if b == 0:
                btn_down_at = now
            elif btn_down_at is not None:
                held = ticks_diff(now, btn_down_at)
                if 30 <= held <= 1500:
                    kind, value = ctl.learn(temp)
                    if kind:
                        settings[kind] = round(value, 1)
                        save_settings(settings)
                        blink = 6 if kind == "heat" else 4
                        print("LEARN: %s threshold = %.1f C" % (kind, value))
                    else:
                        blink = 20
                        print("LEARN: not learned (%s)" % value)
                elif held >= 5000:
                    ctl.heat, ctl.cool = HEAT_DEFAULT, COOL_DEFAULT
                    settings = {"heat": HEAT_DEFAULT, "cool": COOL_DEFAULT}
                    save_settings(settings)
                    blink = 10
                    print("LEARN: thresholds reset to defaults")

        # Decide, once a second.
        if ticks_diff(now, t_ctrl) >= 1000:
            t_ctrl = now
            target = ctl.step(temp, pot, sw_on.value() == 0, sw_off.value() == 0)
            log_s += 1
            if log_s >= LOG_EVERY_S:
                log_s = 0
                print("duct %s C, resting %.1f C, heat>=%.1f cool<=%.1f, %s, speed %d%%" % (
                    "--" if temp is None else "%.1f" % temp, ctl.idle, ctl.heat, ctl.cool,
                    "RUNNING" if ctl.running else "idle", int((pot or 0) * 100)))

        # Soft start / stop.
        if ticks_diff(now, t_slew) >= 20:
            t_slew = now
            if actual < target:
                actual = min(target, actual + SLEW_PER_TICK)
            elif actual > target:
                actual = max(target, actual - SLEW_PER_TICK)
            pwm.duty_u16(int(actual * 65535))

        # Status LED.
        if ticks_diff(now, t_led) >= 200:
            t_led = now
            if blink > 0:
                blink -= 1
                led.value(blink % 2)
            elif temp is None:
                led_n = (led_n + 1) % 5
                led.value(1 if led_n == 0 else 0)
            else:
                led.value(1 if actual > 0 else 0)

        sleep_ms(5)


if __name__ == "__main__":
    try:
        run()
    except Exception as e:      # never leave the fans in a random state
        try:
            from machine import Pin, reset
            Pin(PIN_FAN_PWM, Pin.OUT, value=0)
            print("Error:", e, "- restarting in 5 s")
            sleep_ms(5000)
            reset()
        except ImportError:
            raise
