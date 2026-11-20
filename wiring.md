# Wiring

## Circuit (what's on the PCB)

```
 USB-C charger ══ USB-C cable ══▶ J7 (USB-C socket on the board)

 J7 VBUS ──[F1 PTC]── +5V            J7 CC1 ──[R6 5.1k]── GND
                                     J7 CC2 ──[R7 5.1k]── GND   (makes the charger turn on 5 V)
 +5V ──▶|── D2 1N5819 ── Pico pin 39 VSYS     (Pico pin 40 VBUS: not connected)

 +5V rail ─────────────────┬──────────┬───────────────────┬───────────────┬────────────┐
                           │          │                   │               │            │
                       C1 100µF+  C2 10µF        fan red (J1–J4 pin 2)  C3 100µF+   D1 SS24
                           │          │         3-4 fans in parallel      │       (stripe/cathode
                          GND        GND         fan black (pin 1)        │         at the top)
                                                          │               │            │
                                                          └──── FAN- ─────┘            │
                                                                │                      │
                                                            L1 100µH                   │
                                                                │                      │
                                                                └──────── SW ──────────┘
                                                                           │
                                                                     Q1 AO3400A drain
 GP15 (Pico pin 20) ──[R1 100Ω]──┬──────────────────────────────▶ Q1 gate
                                 │                               Q1 source
                             [R2 10k]                                      │
                                GND                                       GND

 Duct probe (DS18B20):  3V3 (Pico pin 36) ──[R3 4.7k]──┬── GP16 (Pico pin 21)
                                                       └── J5 pin 2 (DQ);  J5 pin 3 = 3V3,  J5 pin 1 = GND

 Override switch:  GP18 (Pico pin 24) ──[R4 1k]── J6 pin 1 ── switch "ON" lug
                                                  J6 pin 2 ── switch centre (common) lug ── GND
                   GP17 (Pico pin 22) ──[R5 1k]── J6 pin 3 ── switch "OFF" lug
                   (internal pull-ups; centre position = neither pin grounded = AUTO)
```

How it works: Q1 switches at 40 kHz. While it's on, current ramps up through the
fans' C3/L1 path. While it's off, L1 keeps the current flowing back to +5V
through D1. C3 smooths the result, so the fans see steady DC ≈ duty × 5 V. That
is a buck converter with the switch on the low side.

## Connectors

**Fan headers J1–J4** (J4 = optional 4th fan) (2.54 mm, keyed, pin 1 marked with a square pad):

| Pin | Net | Fan wire |
|---|---|---|
| 1 | FAN- | black |
| 2 | +5V | red |
| 3 | — (not connected) | yellow/blue tach, if present |

- 2-wire fans with a 2-pin 2.54 mm plug go on pins 1–2.
- Fans with a JST-PH (2.0 mm) plug or bare leads: crimp a 2.54 mm
  KF2510/Dupont housing, or cut and solder an extension.
- **FAN- is not ground**: don't connect it to the duct, the Pico or GND.

**J5, DS18B20 duct probe**: 1 = GND (black), 2 = DQ (yellow), 3 = 3V3 (red).
Crimp a 3-pin 2.54 mm (Dupont/KF2510) housing on the probe's leads. Some probes
use other colours: on those, the odd-coloured wire is usually data. The cable can
be extended to several metres with any 3-core wire.

**J6, override switch**: use an ON-OFF-ON (centre-off) SPDT toggle.

```
   toggle, back view          J6
   ┌───────────────┐
   │  ○ lug A ─────┼──────── pin 1  ON    (switch flipped toward lug B = force ON)
   │  ○ centre ────┼──────── pin 2  GND   (common)
   │  ○ lug B ─────┼──────── pin 3  OFF
   └───────────────┘
```

A toggle connects the centre lug to the lug on the *opposite* side from the
lever. If ON and OFF come out backwards, swap the wires on pins 1 and 3. It's
3.3 V at well under 1 mA, so any thin 3-core cable (alarm or thermostat wire) up
to several metres is fine. Positions: up = force on, middle = AUTO (HA
decides), down = force off.

**Power, J7 (USB-C)**: plug any USB-C phone charger (5 V, ≥ 2 A) into the
board's USB-C socket. R6/R7 (5.1 kΩ on CC1/CC2) are what make a USB-C charger
switch its 5 V on; without them you get 0 V. The board draws about 0.5 A with 3
fans and up to about 1 A with 4. F1 is a resettable fuse: if it trips, unplug
for a minute and it resets.

The Pico is fed through D2 into VSYS, and its own micro-USB port is left free.
To flash it, plug the micro-USB into your PC. The charger can stay plugged in:
D2 and the Pico's own diode keep the two supplies apart. With only the PC
connected, the Pico runs but the fans don't, because the fans only run from J7.

## In the wall

```
        room                               wall cavity / box
  ┌──────────────┐ printed frame + wire mesh (replaces the grille)
  │ ▓ fan ▓ fan ▓ fan ▓ │◀── blows into room
  └──────┬───────┘
         │ 3-4 fan leads + probe lead, through a grommet in the boot
         ▼
   ┌──────────────┐        USB-C charger in a nearby outlet
   │ carrier PCB  │◀═══════ USB-C cable into J7
   │  + Pico W    │────── 3-core cable ──▶ ON/AUTO/OFF toggle (wall plate or box)
   └──────────────┘   keep the Pico W antenna end (opposite the USB) away
                      from the metal duct for good Wi-Fi
```
