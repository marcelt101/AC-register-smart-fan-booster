# AC register smart fan booster

Three quiet 80 mm 5 V fans (four 60 mm fans also fit) in each 4" × 10"
supply register. The original grille is replaced by a 3D-printed frame with a
coarse wire-mesh cover, for maximum airflow. The fans run only while the furnace/AC blower runs. Home Assistant
watches your HomeKit thermostat and switches them through a Pico W on a small
carrier PCB, one board per vent. A wall toggle switch gives manual ON / OFF /
AUTO. One USB-C phone charger powers each board.

```
vent-fans/
├── README.md                  ← you are here: design, BOM, install, tuning
├── wiring.md                  ← schematic in ASCII, connector pinouts, field wiring
├── esphome/vent-fans.yaml     ← Pico W firmware (validated with ESPHome 2026.11)
├── homeassistant/automation.yaml
├── frame/                     ← 3D-printable fan frame: frame.scad, make_stl.sh, stl/, README
├── sim/                       ← ngspice models, ./run_all.sh, plot.py, results.txt, plots
└── kicad/                     ← KiCad 7 project: schematic, placed board, custom Pico W part
    └── tools/                 ← generators (gen_schematic.py, gen_pcb.py, check_netlist.py)
```

## What changed from the original spec, and why

| # | Original spec | v1 | Why (evidence in `sim/`) |
|---|---|---|---|
| 1 | 100 µF across the fans, no inductor | Add **one 100 µH inductor** between the fans and the MOSFET. That makes a proper low-side buck converter. | A capacitor across a low-side-switched load gets recharged to 5 V on every PWM pulse, so the fans saw nearly full voltage at any setting: **30 % duty still gave 89 % fan current**. With the inductor the fans get smooth DC ≈ duty × 5 V (30 % → 28 %, 60 % → 56 %, ripple ≈ 80 mV). See `plot_speed_vs_duty.png`. |
| 2 | Cap only across the fans | 100 µF + 10 µF **on the 5 V rail** (input) as well | Moving caps alone (no inductor) made it worse: every pulse recharged the fans' internal capacitors through the FET with **13–19 A spikes**. The buck version peaks at **0.4 A**. See `plot_waveforms_60pct.png`. |
| 3 | 25 kHz PWM | 40 kHz | Still inaudible. A 100 µH inductor is enough at this frequency (ripple ≈ 0.15 A). |
| 4 | Speed jumps instantly | **Soft-start in firmware**: 2 % every 20 ms | Going straight from 0 to 60 % rings the LC filter: **2.1 A** inductor peak. With the slew limiter it's **0.44 A**, so a small 1 A inductor never saturates. See `plot_powerup.png`. |
| 5 | IRLZ44N / AO3400 | **SI2302CDS** (Vishay, SOT-23; AO3400A also fits) | Fully on from the Pico's 3.3 V gate drive (75 mΩ max at 2.5 V). The simulations used an AO3400A model (~32 mΩ); the SI2302CDS's higher resistance still means under 50 mW even with 4 fans at full speed, so no heatsink. Chosen because Mouser stocks it. The IRLZ44N is only specified from 4 V gate drive and is huge. |
| 6 | Breadboard wiring | **Carrier PCB, 80 × 60 mm**, through-hole resistors and capacitors, **USB-C power socket**: Pico W socketed, 4 keyed fan headers, override-switch header, DS18B20 duct-probe header | Fewer loose joints in a dusty, warm, vibrating spot. Fans unplug for cleaning. |
| 7 | Automation used `delay` + `trigger.to_state` | `for:` on the triggers, re-sync on HA restart and when the board reconnects | The old version could leave fans running after an HA restart. `for:` doesn't drop a pending off when the thermostat chatters. |
| 8 | ESPHome reboots when HA is down | `reboot_timeout: 0s`, plus an on-board fallback from the duct probe | The fans keep working (or stay safely off) with HA down. |
| 9 | 3 fans | **Header for a 4th fan**; inductor spec raised to Isat ≥ 1.5 A, diode to SS24 | Four worst-case 0.25 A fans at full speed draw 0.84 A in simulation; the 5 V rail stays ≥ 4.87 V and the FET dissipates 23 mW. |
| 10 | No manual control | **ON-OFF-ON toggle** on J6, plus a **Mode** select (Auto / Force on / Force off) and **Manual speed** in HA | The switch wins over everything. Centre position = AUTO. Works with HA down, since it is read by the Pico. |

What stayed the same: Pico W, 5 V fans, one USB charger, HA in charge, 20 s
start delay, 30 s run-on, fans **off** if anything is unplugged or the Pico is
booting (10 k gate pull-down).

### Simulation summary (`sim/results.txt`, 3 × fans, 5.1 V charger + 1 m cable + the board's fuse)

| Circuit | duty → fan current (% of full) | FET peak (60 %) | 5 V rail min (30 %) |
|---|---|---|---|
| Original spec | 30→89, 60→97, 80→99 | 0.76 A | 4.30 V |
| Caps on rail, no L | 30→76, 60→90, 80→97 | **13.3 A** | 4.49 V |
| **v1 buck** | **30→28, 60→56, 80→78** | **0.39 A** | 5.04 V |
| v1 buck, **4 × 0.25 A fans** | 60 % → 2.74 V, 100 % → 4.63 V on the fans | 0.84 A (at 100 %) | 4.87 V (at 100 %); Pico VSYS 4.59 V |

The models are approximations: the AO3400A is a VDMOS fit to its datasheet, and
each fan is modelled as a reverse diode + 1 µF + 33 Ω + 1 mH. The comparison
between circuits is what matters, not the third digit. To re-run:
`cd sim && ./run_all.sh && python3 plot.py` (needs ngspice, numpy and matplotlib).

## Bill of materials

Shopping list with what to buy marked: [`BOM.md`](BOM.md) (and [`bom.csv`](bom.csv) for a spreadsheet).

| Ref | Qty | Part | Footprint | Notes |
|---|---|---|---|---|
| U1 | 1 | Raspberry Pi Pico W, plus 2× 20-pin female headers | 2×20 THT | Socketed, so it can be swapped or reflashed |
| J7 | 1 | USB-C receptacle, power-only 6-pin (GCT USB4125-GF-A or equivalent) | `USB_C_Receptacle_GCT_USB4125` | Phone-charger input on the left edge. Shell lugs are through-hole; the 6 signal pads are SMD at 1 mm pitch (fine tip + flux). |
| R6, R7 | 2 | 5.1 kΩ ¼ W | THT axial, 7.62 mm | CC1/CC2 pull-downs. **Must be 5.1k**: without them a USB-C charger supplies no power. |
| F1 | 1 | Resettable fuse (PTC), 1.5–2 A hold, radial | 5.1 mm leads (Bourns MF-RHT200 footprint) | Protects the wiring in the wall if something shorts |
| D2 | 1 | 1N5819 Schottky | THT DO-41 | Feeds the Pico's VSYS from the 5 V rail; stops back-feed into your PC when you flash over the Pico's micro-USB |
| Q1 | 1 | SI2302CDS-T1-GE3 N-MOSFET (Vishay; AO3400A also fits) | SOT-23 | Logic-level, 20 V 2.9 A, 75 mΩ at 2.5 V gate. Stocked at Mouser |
| L1 | 1 | 100 µH shielded power inductor, **Isat ≥ 1.5 A, DCR ≤ 0.3 Ω** | Bourns SRR1260 (12.5 mm) | Sized for 4 fans. Check Isat on the datasheet of whatever you buy. |
| D1 | 1 | SS24 Schottky, 2 A 40 V (SS14 is fine for 3 fans) | SMA | Stripe (cathode) to +5 V |
| C1, C3 | 2 | 100 µF 10 V+ low-ESR electrolytic | radial 6.3 mm, 2.5 mm pitch | C1 = input, C3 = across the fans |
| C2 | 1 | 10 µF 16 V X7R ceramic, radial leads | THT, 5 mm lead spacing | Close to Q1/D1 |
| R1 | 1 | 100 Ω ¼ W | THT axial, 7.62 mm (0.3") | gate series resistor |
| R2 | 1 | 10 kΩ ¼ W | THT axial, 7.62 mm | gate pull-down |
| J1–J4 | 3–4 | 3-pin 2.54 mm fan header (KF2510 / Molex KK style) | `FanPinHeader_1x03` | J4 only for a 4th fan. 2-pin fan plugs fit pins 1–2. |
| J5, R3 | 1 + 1 | 3-pin header + 4.7 kΩ ¼ W | THT axial, 7.62 mm | For the DS18B20 probe (R3 is its pull-up) |
| J6, R4, R5 | 1 + 2 | 3-pin header + 1 kΩ ¼ W ×2 | THT axial, 7.62 mm | Override switch. R4/R5 protect the Pico from the off-board wire. |
| SW1 | 1 | ON-OFF-ON (centre-off) SPDT toggle, e.g. MTS-103, + 3-core cable + 3-pin 2.54 mm housing | off-board | Drawn on the schematic in the dashed off-board box. Mount on the wall plate, grille or a small box. Any low-voltage switch works (3.3 V, < 1 mA). |
| — | 3 (or 4) | 80 mm (or 60 mm) **5 V** fans, 25 mm thick, sleeve/hydraulic bearing, ≤ 0.25 A | | Pick the lowest-RPM/dBA listing. Budget generic is fine. |
| — | 1 | USB-C phone charger (5 V, **≥ 2 A**) + USB-C cable | | Plugs into J7 on the board. Any USB-C charger works; the board asks for plain 5 V. |
| — | 1 | Waterproof DS18B20 probe (stainless tube, 1–3 m cable) + 3-pin 2.54 mm housing | | Duct temperature: shown in HA, runs the fans when HA is down |
| — | 1 | Wire mesh, **¼" (6 mm) openings or smaller**: hardware cloth, or expanded metal for a floor vent | | Replaces the grille; cut to the size `frame/make_stl.sh` prints. See [`frame/README.md`](frame/README.md). |
| — | 8–10 | M3 × 8 countersunk screws (+ 4 × M3 × 10 and nuts for the split frame) | | Hold the printed bezel and mesh down |

Total draw per board: ≈ 0.5 A at full speed with 3 typical fans, up to ~1 A with
4 worst-case fans.

**Fans per vent:** 3 × 80 mm uses 240 mm of the 254 mm (10") opening.
**4 × 80 mm (320 mm) cannot fit**; four fans means 60 mm fans (4 × 60 = 240 mm).
Three 80 mm fans move noticeably more air than four 60 mm ones, so 3 × 80 is the
default. The board takes either.

## Build

1. **PCB**: open `kicad/vent_fans.kicad_pro` in KiCad 7 or later. The
   schematic is complete and the board is placed with nets assigned. You do the
   routing; see [Routing the board](#routing-the-board).
2. **Solder** the three surface-mount parts first: Q1 (SOT-23), D1 (SMA) and
   L1. They are all large enough for a normal iron. Then fit the through-hole
   resistors, capacitors, headers and Pico sockets. Bend the resistor leads to
   7.62 mm (0.3").
   Check the polarity of C1/C3 (+) and D1 (stripe toward the +5V side).
3. **Firmware**: in the ESPHome add-on on your Proxmox HA, create a new device
   per vent, paste `esphome/vent-fans.yaml`, change `name` / `friendly_name` at
   the top (e.g. `vent-fans-living`), add the secrets (`esphome/secrets.example.yaml`
   shows the names), plug the Pico W's own micro-USB into your PC and install.
   This is safe with the charger also plugged into J7, thanks to D2. After that,
   updates go over Wi-Fi.
4. **Bench test** before it goes in the wall. Plug the charger into the
   board's USB-C socket (J7) with the fans attached. In HA, turn on `fan.vent_fans`: the fans should ramp up over about
   a second. Measure across a fan connector (pin 2 to pin 1): ≈ 2.7 V at 1 %,
   ≈ 4 V at 60 %, ≈ 4.9 V at 100 %.
5. **Automation**: in HA, go to Developer Tools → States, filter `climate.`, and
   find your thermostat. Check that it has an `hvac_action` attribute that
   changes between `idle` and `heating`/`cooling`. HomeKit Controller thermostats
   normally do. Paste `homeassistant/automation.yaml` into a new automation and
   replace `climate.thermostat` (3 places). List each vent's fan entity in both
   fan lists.
6. **Override switch**: wire the toggle to J6 with 3 conductors: centre lug →
   pin 2 (GND), one outer lug → pin 1 (ON), the other → pin 3 (OFF). Flip it and
   watch the board's **Control source** sensor in HA change. You can also
   override from your phone with the **Mode** select, and set the override speed
   with **Manual speed** (default 100 %).
7. **Frame and mesh cover** (replaces the grille): see
   [`frame/README.md`](frame/README.md). Measure the opening, then
   `frame/make_stl.sh <width> <height> <fan> <count> <floor|wall>` writes
   print-ready STLs (base + bezel, one-piece and split), the mesh cut size and
   the screw count. PETG or ASA, no supports.

## Routing the board

The board in `kicad/vent_fans.kicad_pcb` is 80 × 60 mm and two-layer. It already
has a GND pour on both layers and a copper keep-out under the Pico W antenna.
The `Power` net class (0.8 mm tracks) covers VBUS_IN, +5V, GND, FAN- and SW. Signals
default to 0.3 mm.

1. Open the PCB and press **B** to refill zones. The ratsnest shows the 32
   connections still to route.
2. Route the **switching loop** first and keep it tiny: C2 → D1 cathode, D1
   anode → Q1 drain, Q1 source → GND via next to C2's GND pad. This is the only
   fast-edge loop on the board.
3. SW (Q1 drain / D1 anode / L1 pin 2) is the noisy node. Keep it short and
   on the top layer, with no long runs.
4. Power in: J7 VBUS pads (A9 and B9, tie both) → F1 → +5V. Tie both J7 GND
   pads and the four shell lugs to the GND pour. R6 from CC1 (A5) to GND and R7
   from CC2 (B5) to GND, kept close to the socket.
5. +5V: from F1 to C1 and C2, then on to the fan headers' pin 2 and C3+. Use
   0.8 mm or wider. Also +5V → D2 anode, and D2 cathode → Pico pin 39 (VSYS,
   top-left, second pad from the USB end). Leave Pico pin 40 (VBUS) unconnected.
6. FAN-: from L1 pin 1 to C3−, then to pin 1 of J1–J4.
7. GP15 (bottom-right Pico pad) → R1 → gate. R2 goes from gate to GND.
8. Duct probe: GP16 → J5 pin 2 → R3 → 3V3 (Pico pin 36).
9. Override: GP18 (Pico pin 24) → R4 → J6 pin 1 and GP17 (pin 22) → R5 → J6
   pin 3. Both pads are on the top row next to the antenna end. Route them on
   the bottom layer under the Pico, staying outside the keep-out, or along the
   top edge.
10. Stitch the two GND pours with a few vias, keeping them away from the
   antenna keep-out. Run **Inspect → Design Rules Checker** until it's clean.
11. **File → Fabrication Outputs → Gerbers + Drill**, zip them and order (any
   2-layer, 1.6 mm, HASL service).

`kicad/tools/` regenerates everything from one parts table, if you want to change
a part:
`python3 tools/gen_schematic.py && python3 tools/check_netlist.py && /usr/bin/python3 tools/gen_pcb.py`.
Note that this overwrites any routing you've done, so only use it before you route.

## Tuning

- **Speed**: `speed: 60` in the automation. With smooth DC the fans are much
  quieter at a given speed than with chopped PWM. Try 30–60 %.
- **Fans won't start at low speed**: raise `min_power` (0.55 ≈ 2.7 V) in
  `vent-fans.yaml`.
- **Delays**: the `for:` values in the automation (20 s on, 30 s run-on).
- **Your thermostat only shows `idle`/`heating`** (no `cooling`, or the
  attribute is missing): make the HA automation trigger on the board's
  **Duct temperature** sensor instead (same thresholds as the fallback).
- **Duct-probe fallback thresholds**: `duct_hot`, `duct_cold`, `duct_idle_low`
  and `duct_idle_high` at the top of `vent-fans.yaml`. Watch **Duct
  temperature** in HA for a day of heating or cooling, then set them between
  what you see with the blower running and with it off.

## Safety and install notes

- **FAN- is not ground.** The fans' black wires sit at about 5 V minus the fan
  voltage. Never tie a fan's black wire to GND, the metal duct or the Pico.
- Keep the PCB and charger outside the duct, in the wall cavity or a small box
  next to the boot. Only the fan leads (and the probe) go into the airstream. Use
  plenum-rated cable if your local code requires it for runs inside the duct.
- Keep fans away from electric heat strips. With a heat pump or electric
  furnace, mount the fans at the register end only.
- Mount fans on foam or rubber grommets, seal the frame with foam
  weatherstrip, and have the fans blow into the room.
- **The mesh is the finger guard.** Keep its openings at ¼" (6 mm) or smaller,
  and always screw the bezel down before running the fans.
- If HA is down, the board runs the fans from the duct probe. If the probe is
  unplugged as well, the fans stay off. A Pico crash or unplugged charger also
  means fans off.
- **Duct probe**: drill a 6–7 mm hole in the side of the boot or duct, a few
  inches upstream of the fans. Push the probe tip into the airstream and seal
  the hole with foil HVAC tape. Keep it out of direct contact with the metal.

## Why Wi-Fi and not Zigbee

Your Zigbee network through HA would work, but it doesn't make this simpler.
There is no Pico + Zigbee option, and an ESP32-C6/H2 running Zigbee firmware is
harder to set up than ESPHome over Wi-Fi. It would also give up the
Mode / Manual speed / Control source entities and the on-board fallback.

The one real Zigbee simplification is a different product altogether: a Zigbee
smart plug feeding a USB charger, with the fans wired straight to USB. That
means no PCB, but also no speed control, no soft start and no override switch,
and the fans always run at full 5 V. The PCB design is better for quiet fans.

## Still open

- **Boot depth**: the frame needs about 30 mm below the floor for 25 mm fans.
- **Thermostat model**: to confirm it exposes `hvac_action` through HomeKit.
