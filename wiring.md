# Wiring

## Circuit (what's on the PCB)

```
 USB-C charger ══ USB-C→micro-USB cable ══▶ Pico W micro-USB port

 +5V  (Pico pin 40 VBUS) ──┬──────────┬───────────────────┬───────────────┬────────────┐
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

 Optional duct probe:  3V3 (Pico pin 36) ──[R3 4.7k]──┬── GP16 (Pico pin 21)
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

**J5, DS18B20 probe (optional)**: 1 = GND (black), 2 = DQ (yellow), 3 = 3V3 (red).

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

**Power**: only the Pico's own micro-USB port. Use a charger of 5 V, ≥ 2 A.
Fan current flows through the Pico's VBUS pin: about 0.5 A with 3 fans and
up to about 1 A with 4. That is within what the micro-USB connector carries.
Don't also power the board from your PC while the charger is plugged in. For
flashing, unplug the charger and use the PC.

## In the wall

```
        room                               wall cavity / box
  ┌──────────────┐ grille
  │ ▓ fan ▓ fan ▓ fan ▓ │◀── blows into room
  └──────┬───────┘
         │ 3-4 fan leads (+ probe lead, optional), through a grommet in the boot
         ▼
   ┌──────────────┐        USB-C charger in a nearby outlet
   │ carrier PCB  │◀═══════ USB cable
   │  + Pico W    │────── 3-core cable ──▶ ON/AUTO/OFF toggle (wall plate or box)
   └──────────────┘   keep the Pico W antenna end (opposite the USB) away
                      from the metal duct for good Wi-Fi
```
