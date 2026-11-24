"""PC simulation of main.py: runs the real firmware loop against fake Pico
hardware (pins, PWM, ADC, DS18B20) and a simulated clock, then checks what the
fans and LED do through a heating cycle, LEARN, reset and the override switch.

    python3 test_sim.py        (needs only Python 3, no Pico)
"""
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


# ---- simulated world --------------------------------------------------------
class World:
    now = 0            # ms
    duct = 20.0        # deg C at the probe
    probe = True
    pot = 0.5          # trimpot 0..1
    learn = 1          # 1 = released, 0 = pressed
    sw_on = 1          # 1 = open, 0 = closed to GND
    sw_off = 1
    duty = 0
    led = 0
    events = []        # (time_ms, fn)
    stop_at = 0


class StopSim(Exception):
    pass


def sim_sleep(ms):
    World.now += ms
    while World.events and World.events[0][0] <= World.now:
        World.events.pop(0)[1]()
    if World.now >= World.stop_at:
        raise StopSim


# ---- fake MicroPython modules -------------------------------------------------
class Pin:
    IN, OUT, PULL_UP = 0, 1, 2

    def __init__(self, n, mode=None, pull=None, value=None):
        self.n = n
        if value is not None:
            self.value(value)

    def value(self, v=None):
        if v is None:
            return {12: World.learn, 18: World.sw_on, 17: World.sw_off}.get(self.n, 0)
        if self.n == 10:
            World.led = v

    def toggle(self):
        if self.n == 10:
            World.led ^= 1


class PWM:
    def __init__(self, pin):
        pass

    def freq(self, f):
        assert f == 40_000

    def duty_u16(self, d):
        World.duty = d


class ADC:
    def __init__(self, n):
        assert n == 26

    def read_u16(self):
        return int(World.pot * 65535)


class WDT:
    def __init__(self, timeout):
        pass

    def feed(self):
        pass


class DS18X20:
    def __init__(self, ow):
        pass

    def scan(self):
        return [b"probe"] if World.probe else []

    def convert_temp(self):
        if not World.probe:
            raise OSError("no presence")

    def read_temp(self, rom):
        if not World.probe:
            raise OSError("crc")
        return World.duct


sys.modules["machine"] = types.SimpleNamespace(Pin=Pin, PWM=PWM, ADC=ADC, WDT=WDT, reset=lambda: None)
sys.modules["onewire"] = types.SimpleNamespace(OneWire=lambda pin: object())
sys.modules["ds18x20"] = types.SimpleNamespace(DS18X20=DS18X20)

import main  # noqa: E402  (the firmware under test)

main.ticks_ms = lambda: World.now
main.ticks_diff = lambda a, b: a - b
main.sleep_ms = sim_sleep


def at(seconds, fn):
    World.events.append((int(seconds * 1000), fn))
    World.events.sort(key=lambda e: e[0])


def run_until(seconds):
    World.stop_at = int(seconds * 1000)
    try:
        main.run()
    except StopSim:
        pass


# ---- scenario ----------------------------------------------------------------
checks = []


def check(name, cond):
    checks.append((name, bool(cond)))


def level(pot):
    return main.MIN_LEVEL + (1 - main.MIN_LEVEL) * pot


def snap(name, fn):
    at(name, fn)


os.chdir(tempfile.mkdtemp())          # settings.json goes here, not into the repo
LEVEL = int(level(0.5) * 65535)

# 0-60 s: duct resting at 20 C -> fans off
snap(59, lambda: check("idle: fans off", World.duty == 0))
snap(59.1, lambda: check("idle: LED off", World.led == 0))
# 60 s: furnace starts, duct jumps to 45 C
at(60, lambda: setattr(World, "duct", 45.0))
snap(75, lambda: check("heating: still off before the 20 s on-delay", World.duty == 0))
snap(85, lambda: check("heating: fans at trimpot speed after ~20 s", abs(World.duty - LEVEL) < 700))
snap(85.1, lambda: check("heating: LED on", World.led == 1))
# 120 s: LEARN while heating -> heat threshold halfway between 20 and 45 = 32.5
at(120, lambda: setattr(World, "learn", 0))
at(120.3, lambda: setattr(World, "learn", 1))
snap(121, lambda: check("LEARN heating saved 32.5", main.load_settings()["heat"] == 32.5))
# 200 s: furnace off, duct back to 21 C -> fans stop ~60 s later
at(200, lambda: setattr(World, "duct", 21.0))
snap(250, lambda: check("after heating: still running during the 60 s off-delay", World.duty > 0))
snap(265, lambda: check("after heating: fans off", World.duty == 0))
# 300 s: AC, duct 13 C -> on; LEARN -> cool threshold (20+13)/2 = 16.5
at(300, lambda: setattr(World, "duct", 13.0))
snap(325, lambda: check("cooling: fans on", World.duty > 0))
at(330, lambda: setattr(World, "learn", 0))
at(330.2, lambda: setattr(World, "learn", 1))
snap(331, lambda: check("LEARN cooling saved 16.5", main.load_settings()["cool"] == 16.5))
at(340, lambda: setattr(World, "duct", 20.0))
snap(405, lambda: check("after cooling: fans off", World.duty == 0))
# 420 s: LEARN at rest -> refused, nothing changes
at(420, lambda: setattr(World, "learn", 0))
at(420.2, lambda: setattr(World, "learn", 1))
snap(421, lambda: check("LEARN at rest is refused", main.load_settings() == {"heat": 32.5, "cool": 16.5}))
# 450 s: hold LEARN 6 s -> defaults
at(450, lambda: setattr(World, "learn", 0))
at(456, lambda: setattr(World, "learn", 1))
snap(457, lambda: check("hold LEARN 5 s resets defaults",
                        main.load_settings() == {"heat": main.HEAT_DEFAULT, "cool": main.COOL_DEFAULT}))
# 480 s: override ON with the trimpot at max -> full speed; OFF beats a hot duct
at(480, lambda: (setattr(World, "sw_on", 0), setattr(World, "pot", 1.0)))
snap(490, lambda: check("override ON: full speed at trimpot max", World.duty >= 65000))
at(500, lambda: (setattr(World, "sw_on", 1), setattr(World, "sw_off", 0), setattr(World, "duct", 45.0)))
snap(540, lambda: check("override OFF: fans off even while heating", World.duty == 0))
# 560 s: back to AUTO, then the probe falls off -> fans stop, LED slow-blinks
at(560, lambda: setattr(World, "sw_off", 1))
snap(590, lambda: check("AUTO again while hot: fans on", World.duty > 0))
at(600, lambda: setattr(World, "probe", False))
snap(610, lambda: check("probe lost: fans off", World.duty == 0))


leds = []
for k in range(10):                      # sample the LED over 2 s while the loop runs
    at(612 + k * 0.2, lambda: leds.append(World.led))
snap(614.1, lambda: check("probe lost: LED slow blink", 0 < sum(leds) < len(leds)))

# soft start: from off to full takes ~1 s, never a jump
ramp = []
at(620, lambda: (setattr(World, "probe", True), setattr(World, "sw_on", 0)))
for k in range(1, 31):                   # sample every 0.1 s for 3 s
    at(620 + k * 0.1, lambda: ramp.append(World.duty))
snap(623.2, lambda: check("soft start ramps up over ~1 s instead of jumping",
                          all(b >= a for a, b in zip(ramp, ramp[1:]))       # never goes down
                          and ramp[-1] >= 65000                             # ends at full speed
                          and sum(1 for d in ramp if 0 < d < 65000) >= 5    # >= 0.5 s spent ramping
                          and max(b - a for a, b in zip(ramp, ramp[1:])) <= 0.25 * 65535))  # no big jumps

run_until(630)

width = max(len(n) for n, _ in checks)
for name, ok in checks:
    print(("PASS  " if ok else "FAIL  ") + name.ljust(width))
failed = [n for n, ok in checks if not ok]
print("\n%d/%d passed" % (len(checks) - len(failed), len(checks)))
sys.exit(1 if failed else 0)
