# Bill of materials (per vent)

Quantities are for **one vent** (one controller board + one frame). Multiply
for more vents. The same list is in [`bom.csv`](bom.csv) for a spreadsheet.

**🛒 = buy.** Resistors and capacitors are at the bottom; you already have
those.

## To buy

| 🛒 | Ref | Qty | Part | Spec / example | Notes |
|---|---|---|---|---|---|
| **Controller** ||||||
| 🛒 | U1 | 1 | Raspberry Pi Pico W | Pico **WH** (headers pre-soldered) is easiest | Must be the W (Wi-Fi) version |
| 🛒 | — | 2 | Female header 1×20, 2.54 mm | straight | Socket for the Pico |
| **Power stage** ||||||
| 🛒 | Q1 | 1 | AO3400A N-MOSFET | SOT-23 (SMD) | Buy a 10-pack |
| 🛒 | D1 | 1 | SS24 Schottky, 2 A 40 V | SMA (SMD) | SS14 OK for 3 fans. Not a 1N4148 |
| 🛒 | L1 | 1 | 100 µH shielded inductor, Isat ≥ 1.5 A, DCR ≤ 0.3 Ω | 12 × 12 mm SMD, e.g. Bourns SRR1260-101M | Check Isat on the datasheet |
| **Power input** ||||||
| 🛒 | J7 | 1 | USB-C receptacle, power-only 6-pin | GCT USB4125-GF-A or equivalent | Fine tip + flux for the 1 mm pads |
| 🛒 | F1 | 1 | Resettable fuse (PTC), 1.5–2 A hold | radial, 5.1 mm leads (MF-R160 / MF-RHT200) | |
| 🛒 | D2 | 1 | 1N5819 Schottky | DO-41 through-hole | |
| 🛒 | — | 1 | USB-C phone charger | 5 V, **≥ 2 A** | |
| 🛒 | — | 1 | USB-C cable | length to suit | |
| **Connectors** ||||||
| 🛒 | J1–J4 | 4 | Fan header, 3-pin 2.54 mm | KF2510 / Molex KK style, vertical | J4 only for a 4th fan |
| 🛒 | J5, J6 | 2 | Pin header 1×3, 2.54 mm | break from a 40-pin strip | Probe and switch |
| 🛒 | — | 1 kit | KF2510 / Dupont 3-pin housings + crimp pins | | For fans, probe and switch cable |
| **Fans, sensor, switch** ||||||
| 🛒 | — | 3 (+1) | 80 mm fan, **5 V DC** | 80×80×25 mm, ~1700 rpm, ~25 dB, ≤ 0.25 A | +1 spare or 4th fan |
| 🛒 | — | 1 | DS18B20 waterproof probe | stainless tube, 1–3 m cable | |
| 🛒 | SW1 | 1 | Toggle switch ON-OFF-ON (SPDT centre-off) | e.g. MTS-103 | Off-board |
| 🛒 | — | as needed | 3-core cable, 22–26 AWG | alarm / thermostat wire | Switch to J6 |
| **Frame** ||||||
| 🛒 | — | 1 | Wire mesh, **¼" (6 mm) openings or smaller** | hardware cloth (wall) or expanded metal 1–1.5 mm (floor) | Cut to size: 264 × 98 mm nominal |
| 🛒 | — | 10 | M3 × 8 countersunk screws | stainless | 8 for 3 fans, 10 for 4 |
| 🛒 | — | 4 | M3 × 10 screws + nuts | | Split frame only |
| 🛒 | — | 1 | 3D print, PETG or ASA | base + bezel (+ tabs) | Not PLA |
| optional | — | 12 | Rubber fan grommets / foam washers | | Quieter |
| optional | — | 1 | Thin foam weatherstrip | 3–6 mm, adhesive | Seals the flange |
| **PCB** ||||||
| 🛒 | — | 1 | PCB fab, 80 × 60 mm, 2-layer, 1.6 mm | JLCPCB / PCBWay etc. | Minimum order is usually 5 |
| optional | — | 1 | Crimp tool (e.g. SN-28B) | | Only if you don't have one |

## Already have (resistors and capacitors)

| Ref | Qty | Part | Spec | Notes |
|---|---|---|---|---|
| R1 | 1 | 100 Ω | ¼ W axial | Gate series |
| R2 | 1 | 10 kΩ | ¼ W axial | Gate pull-down |
| R3 | 1 | 4.7 kΩ | ¼ W axial | 1-Wire pull-up |
| R4, R5 | 2 | 1 kΩ | ¼ W axial | Switch line protection |
| R6, R7 | 2 | **5.1 kΩ** | ¼ W axial | USB-C CC pull-downs. **Must be 5.1k**; check your kit has it |
| C1, C3 | 2 | 100 µF electrolytic | 10 V+, low-ESR, radial 6.3 mm / 2.5 mm | Watch polarity |
| C2 | 1 | 10 µF **ceramic** | 16 V+, X7R/X5R, radial, 5 mm leads | Check it's ceramic, not electrolytic |

Two to double-check in your stock: **5.1 kΩ** (many kits only have 4.7k and
5.6k, and USB-C chargers won't turn on without 5.1k) and a **10 µF ceramic** with
leads (many kits only have small ceramics, ≤ 1 µF). If either is missing,
add it to the order.
