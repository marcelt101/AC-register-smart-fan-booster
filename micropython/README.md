# Standalone firmware (MicroPython)

Set-and-forget firmware for the vent fan board: no Wi-Fi, no Home Assistant,
nothing to compile. It's one file, [`main.py`](main.py), and the settings are
plain numbers at the top of it.

Works on any Pico that fits the socket: **Pico / Pico H** (cheapest), Pico W,
Pico 2 or Pico 2 W. The pins it uses are the same on all of them.

## Install (once per Pico)

1. **Put MicroPython on the Pico.** Download the `.uf2` for your board from
   micropython.org:
   - Pico / Pico H: <https://micropython.org/download/RPI_PICO/>
   - Pico W / WH: <https://micropython.org/download/RPI_PICO_W/>
   - Pico 2: <https://micropython.org/download/RPI_PICO2/>
   - Pico 2 W: <https://micropython.org/download/RPI_PICO2_W/>

   Hold the Pico's **BOOTSEL** button while plugging its micro-USB into your
   PC. It appears as a USB drive (`RPI-RP2` or `RP2350`). Drag the `.uf2` onto
   it. It reboots into MicroPython.
2. **Copy the program.** Install [Thonny](https://thonny.org) (free). Open
   `main.py`, then choose *File → Save as… → Raspberry Pi Pico* and save it as
   **`main.py`**. Unplug and replug the Pico: it runs automatically from then on.

Do the install with the Pico plugged into the PC, on or off the board. On the
board, the charger and the PC can both be plugged in at once (D2 keeps them
apart).

## Set up (once per vent)

1. **Speed:** override switch to **ON**. Turn the **SPEED** trimpot until the
   fans are as quiet as you like while still moving air. Switch back to the
   centre (**AUTO**).
2. **Heating:** in winter, while the furnace is heating, press **LEARN** once.
   The LED blinks 3×.
3. **Cooling:** in summer, while the AC is cooling, press **LEARN** once. The
   LED blinks 2×.

Each press sets that threshold halfway between the duct's resting temperature
and the current one, and saves it to `settings.json` on the Pico. Until then
the defaults are 32 °C (90 °F) heating and 16 °C (61 °F) cooling.

| LED | Meaning |
|---|---|
| off | idle |
| on | fans running |
| slow blink | no probe found (fans stay off in AUTO) |
| 3 / 2 blinks | heating / cooling threshold learned |
| 10 blinks | not hot or cold enough to learn yet (or the board just started); try again in a few minutes |
| 5 blinks | LEARN held 5 s: thresholds back to defaults |

## Changing it later

Hold **LEARN** while plugging the Pico in. The program then doesn't start (the
LED flashes 3×), so Thonny can connect. You need this because the program runs
a watchdog that restarts the Pico if anything ever hangs. Edit `main.py`, save
it to the Pico, and replug.

Settings at the top of `main.py`: default thresholds, hysteresis (2 °C), on
delay (20 s), off delay (60 s), lowest fan level, and the soft-start rate.

To see what it's doing, open Thonny's shell with the board running (connect
without holding LEARN, then press **Stop/Restart** once and run `main.py` from
Thonny). It prints the duct, resting and threshold temperatures every 30 s.

## Tested

- `test_sim.py` runs the real `main.py` loop on a PC against simulated pins,
  probe, trimpot, button and clock: `python3 test_sim.py` (19 checks: on and
  off delays, both LEARN cases, refusal at rest, reset, override ON/OFF, lost
  probe, soft start).
- `main.py` compiles with MicroPython's `mpy-cross` 1.29 for the RP2040.
- Not yet run on a real Pico. Watch the USB log on first power-up.
