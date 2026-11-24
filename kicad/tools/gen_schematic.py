#!/usr/bin/env python3
"""Generate the KiCad 7 project for the vent-fan controller.

Writes, next to this tools/ folder:
  vent_fans.kicad_pro, vent_fans.kicad_sch, sym-lib-table, fp-lib-table,
  lib/vent_fans.kicad_sym, lib/vent_fans.pretty/RaspberryPi_PicoW_THT.kicad_mod

Every part is defined once in PARTS below (symbol, footprint, value and the
net on each pin). gen_pcb.py reads the same table, so schematic and board
cannot drift apart. Re-run both after editing PARTS.
"""
import os, re, uuid, json

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
SYMDIR = "/usr/share/kicad/symbols"
NAME = "vent_fans"

# --------------------------------------------------------------------------
# Pico W pinout (pin number -> name). Physical pins 1-20 down the left side
# (USB at the top), 21-40 up the right side.
PICO = {1: "GP0", 2: "GP1", 3: "GND", 4: "GP2", 5: "GP3", 6: "GP4", 7: "GP5",
        8: "GND", 9: "GP6", 10: "GP7", 11: "GP8", 12: "GP9", 13: "GND",
        14: "GP10", 15: "GP11", 16: "GP12", 17: "GP13", 18: "GND", 19: "GP14",
        20: "GP15", 21: "GP16", 22: "GP17", 23: "GND", 24: "GP18", 25: "GP19",
        26: "GP20", 27: "GP21", 28: "GND", 29: "GP22", 30: "RUN", 31: "GP26",
        32: "GP27", 33: "AGND", 34: "GP28", 35: "ADC_VREF", 36: "3V3",
        37: "3V3_EN", 38: "GND", 39: "VSYS", 40: "VBUS"}

PICO_NETS = {n: "GND" for n, nm in PICO.items() if nm in ("GND", "AGND")}
# GP18 (pin 24) sits above GP17 (pin 22), so GP18 = ON and GP17 = OFF keeps the
# override wires straight on the schematic.
# Power comes from the board's USB-C socket into VSYS through D2 (the Pico
# datasheet's recommended way); VBUS (pin 40) is left to the Pico's own
# micro-USB, so the Pico can be plugged into a PC while the charger is in.
PICO_NETS.update({39: "VSYS", 36: "+3V3", 20: "FAN_PWM", 21: "ONEWIRE", 24: "OVR_ON", 22: "OVR_OFF",
                  # standalone (set-and-forget) controls; the Home Assistant firmware ignores them
                  31: "SPEED_POT", 14: "LED", 16: "LEARN"})

FAN_X = [132.08, 149.86, 167.64, 185.42]   # fan columns between the +5V and FAN- rails
RAIL_5V, RAIL_FANM, SW_Y = 48.26, 86.36, 101.6

def _fan(n, opt=""):
    return (f"{NAME}:Fan_Header", f"Fan {n}{opt}", "Connector:FanPinHeader_1x03_P2.54mm_Vertical",
            (FAN_X[n - 1], 71.12), 0, {1: "FAN-", 2: "+5V"},
            "Fan header. Pin 1 = black (-), pin 2 = red (+5V), pin 3 = tach (unused).")

# ref: (lib_id, value, footprint, (x, y) on schematic, rotation, {pin: net}, description)
PARTS = {
    "U1": (f"{NAME}:RaspberryPi_PicoW", "Pico W", f"{NAME}:RaspberryPi_PicoW_THT",
           (63.5, 100.33), 0, PICO_NETS,
           "Raspberry Pi Pico W on 2x20 female headers. Powered by its own micro-USB."),
    "J7": ("Connector:USB_C_Receptacle_USB2.0_16P", "USB-C power",
           "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal",
           (22.86, 63.5), 0, {**{p: "VBUS_IN" for p in ("A4", "A9", "B4", "B9")},
                              **{p: "GND" for p in ("A1", "A12", "B1", "B12", "S1")},
                              "A5": "CC1", "B5": "CC2"},
           "USB-C receptacle GCT USB4105-GF-A (16-pin, Mouser 640-USB4105-GF-A). Power only: "
           "D+/D-/SBU unconnected. Phone charger input, 5 V."),
    "R6": ("Device:R", "5.1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
           (53.34, 64.77), 0, {1: "CC1", 2: "GND"},
           "CC1 pull-down: tells a USB-C charger to turn on 5 V. Must be 5.1k."),
    "R7": ("Device:R", "5.1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
           (43.18, 67.31), 0, {1: "CC2", 2: "GND"},
           "CC2 pull-down (the plug can go in either way up). Must be 5.1k."),
    "F1": ("Device:Polyfuse", "PTC 2A hold", "Fuse:Fuse_Bourns_MF-RHT200",
           (52.07, 48.26), 90, {1: "VBUS_IN", 2: "+5V"},
           "Resettable fuse, 1.5-2 A hold, radial, 5.1 mm leads (e.g. Bourns MF-RHT200 / MF-R160)."),
    "D2": ("Device:D_Schottky", "1N5819", "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
           (86.36, 62.23), 90, {1: "VSYS", 2: "+5V"},
           "Feeds the Pico's VSYS from the board 5 V rail; blocks back-feed when the Pico's micro-USB is plugged into a PC."),
    "C1": ("Device:C_Polarized", "100uF", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm",
           (99.06, 62.23), 0, {1: "+5V", 2: "GND"},
           "Input bulk, 5 V rail. 100 uF 10 V+ low-ESR electrolytic."),
    "C2": ("Device:C", "10uF X7R", "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
           (111.76, 62.23), 0, {1: "+5V", 2: "GND"},
           "Input ceramic 10 uF 16 V X7R, right next to Q1/D1 on the PCB."),
    "J1": _fan(1), "J2": _fan(2), "J3": _fan(3), "J4": _fan(4, " opt."),
    "C3": ("Device:C_Polarized", "100uF 10V", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm",
           (200.66, 72.39), 0, {1: "+5V", 2: "FAN-"},
           "Output cap ACROSS the fans (buck output)."),
    "L1": ("Device:L", "100uH Isat>=1.5A", "Inductor_SMD:L_Bourns_SRR1260",
           (215.9, 92.71), 0, {1: "FAN-", 2: "SW"},
           "Buck inductor, shielded, Isat >= 1.5 A, DCR <= 0.3 ohm (4 fans = up to 1 A)."),
    "D1": ("Device:D_Schottky", "SS24", "Diode_SMD:D_SMA",
           (233.68, 77.47), 270, {1: "+5V", 2: "SW"},
           "Freewheel diode, 2 A 40 V Schottky (SS24; SS14 also OK). Cathode stripe to +5V."),
    "Q1": ("Device:Q_NMOS_GSD", "SI2302CDS", "Package_TO_SOT_SMD:SOT-23",
           (213.36, 111.76), 0, {1: "GATE", 2: "GND", 3: "SW"},
           "Vishay SI2302CDS-T1-GE3 (Mouser): logic-level N-MOSFET, 20 V 2.9 A, 75 mOhm max at 2.5 V gate. AO3400A also fits."),
    "R1": ("Device:R", "100", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
           (194.31, 111.76), 90, {1: "FAN_PWM", 2: "GATE"},
           "Gate series resistor."),
    "R2": ("Device:R", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
           (203.2, 115.57), 0, {1: "GATE", 2: "GND"},
           "Gate pull-down: fans stay off while the Pico boots or is unplugged."),
    "R4": ("Device:R", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
           (95.25, 116.84), 270, {1: "OVR_ON_J", 2: "OVR_ON"}, "Series protection for off-board switch wire."),
    "R5": ("Device:R", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
           (95.25, 121.92), 270, {1: "OVR_OFF_J", 2: "OVR_OFF"}, "Series protection for off-board switch wire."),
    "J6": ("Connector_Generic:Conn_01x03", "Override", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
           (116.84, 119.38), 0, {1: "OVR_ON_J", 2: "GND", 3: "OVR_OFF_J"},
           "ON-OFF-ON toggle: 1 = ON lug, 2 = common (centre lug), 3 = OFF lug. Centre position = AUTO."),
    "SW1": ("Switch:SW_SPDT_MSM", "ON-OFF-ON toggle", "",
            (144.78, 119.38), 180, {3: "OVR_ON_J", 1: "OVR_OFF_J", 2: "GND"},
            "OFF-BOARD. SPDT centre-off toggle (e.g. MTS-103) on the wall plate or a small box, "
            "3-core cable to J6. Centre lug = common (J6 pin 2)."),
    "R3": ("Device:R", "4.7k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
           (101.6, 143.51), 0, {1: "+3V3", 2: "ONEWIRE"},
           "1-Wire pull-up for the DS18B20 duct probe."),
    "J5": ("Connector_Generic:Conn_01x03", "DS18B20 probe",
           "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
           (134.62, 147.32), 0, {1: "GND", 2: "ONEWIRE", 3: "+3V3"},
           "Duct temperature probe: 1 = GND (black), 2 = DQ (yellow), 3 = 3V3 (red)."),
    # ---- standalone controls: speed trimpot, LEARN button, status LED ----
    "RV1": ("Device:R_Potentiometer_Trim", "10k SPEED", "Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical",
            (95.25, 99.06), 180, {1: "GND", 2: "SPEED_POT", 3: "+3V3"},
            "Fan speed for the standalone firmware. Multi-turn trimmer, e.g. Bourns 3296W-1-103LF."),
    "C4": ("Device:C", "100nF", "Capacitor_THT:C_Disc_D3.0mm_W1.6mm_P2.50mm",
           (88.9, 102.87), 0, {1: "SPEED_POT", 2: "GND"},
           "Smooths the trimpot reading."),
    "SW2": ("Switch:SW_Push", "LEARN", "Button_Switch_THT:SW_PUSH_6mm",
            (35.56, 114.3), 0, {1: "GND", 2: "LEARN"},
            "Standalone firmware: press while heating or cooling runs to learn the threshold; hold 5 s to reset."),
    "R8": ("Device:R", "330", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
           (36.83, 109.22), 270, {1: "LED", 2: "LED_A"},
           "Status LED resistor (~4 mA)."),
    "D3": ("Device:LED", "STATUS", "LED_THT:LED_D3.0mm",
           (26.67, 109.22), 0, {1: "GND", 2: "LED_A"},
           "Status LED: on = fans running, blinks to confirm LEARN."),
    "H1": ("Mechanical:MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3",
           (25.4, 182.88), 0, {}, "Mounting hole."),
    "H2": ("Mechanical:MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3",
           (38.1, 182.88), 0, {}, "Mounting hole."),
}

# Reference/Value text offsets that differ from the default (right of the part).
TEXT = {
    "U1": ((0, -29.21), (0, 29.21), ""),
    "R1": ((0, -2.54), (0, 2.54), ""),
    "R4": ((0, -2.54), (0, 2.54), ""),
    "R5": ((0, 2.54), (0, 5.08), ""),
    "R2": ((-2.54, -1.27), (-2.54, 1.27), " (justify right)"),
    "J6": ((0, -6.35), (0, 6.35), ""),
    "J7": ((0, -22.86), (0, -20.32), ""),
    "RV1": ((3.81, -1.27), (3.81, 1.27), " (justify right)"),  # flipped by the 180 deg rotation
    "C4": ((-2.54, -1.27), (-2.54, 1.27), " (justify right)"),
    "SW2": ((0, 3.81), (0, 6.35), ""),
    "R8": ((0, -2.54), (0, -5.08), ""),
    "D3": ((0, -2.54), (0, -5.08), ""),
    "F1": ((0, -2.54), (0, 2.54), ""),
    "D2": ((2.54, -1.27), (2.54, 1.27), " (justify right)"),  # flipped by the 90 deg rotation
    "SW1": ((0, -6.35), (0, 12.7), ""),
    "Q1": ((5.08, -1.27), (5.08, 1.27), " (justify left)"),
    **{f"J{i}": ((1.27, 8.89), (1.27, 11.43), " (justify left)") for i in (1, 2, 3, 4)},
    "D1": ((2.54, -1.27), (2.54, 1.27), " (justify right)"),  # flipped by the 270 deg rotation
}

POWER_NETS = {"+5V": "power:+5V", "GND": "power:GND", "+3V3": "power:+3V3"}

# --------------------------------------------------------------------------
# tiny s-expression reader / writer
def parse(s):
    tok = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+', s)
    stack, cur = [], []
    for t in tok:
        if t == "(":
            stack.append(cur); cur = []
        elif t == ")":
            done = cur; cur = stack.pop(); cur.append(done)
        else:
            cur.append(t)
    return cur

def dump(e, ind=0):
    if not isinstance(e, list):
        return e
    if all(not isinstance(x, list) for x in e):
        return "(" + " ".join(e) + ")"
    out, pad = "(", "  " * (ind + 1)
    seen_list = False
    for i, x in enumerate(e):
        if isinstance(x, list):
            out += "\n" + pad + dump(x, ind + 1); seen_list = True
        else:
            out += ("" if i == 0 else (" " if not seen_list else "\n" + pad)) + x
    return out + "\n" + "  " * ind + ")"

def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'

def uid():
    return str(uuid.uuid4())

_libcache = {}
def lib_symbol(lib_id):
    """Return the symbol definition (as a parsed list) renamed to lib_id."""
    lib, name = lib_id.split(":")
    if lib == NAME:
        tree = parse(open(os.path.join(PROJ, "lib", f"{NAME}.kicad_sym")).read())
    else:
        if lib not in _libcache:
            _libcache[lib] = parse(open(f"{SYMDIR}/{lib}.kicad_sym").read())
        tree = _libcache[lib]
    root = tree[0]
    syms = {x[1].strip('"'): x for x in root if isinstance(x, list) and x[0] == "symbol"}
    sym = [y for y in syms[name]]
    ext = [x for x in sym if isinstance(x, list) and x[0] == "extends"]
    if ext:  # flatten "extends": take parent's graphics/pins, child's properties
        parent = lib_symbol(f"{lib}:{ext[0][1].strip(chr(34))}")
        props = [x for x in sym if isinstance(x, list) and x[0] == "property"]
        body = [x for x in parent[2:] if not (isinstance(x, list) and x[0] == "property")]
        sym = ["symbol", q(name)] + props + body
        pname = parent[1].strip('"').split(":")[-1]
        sym = rename_units(sym, pname, name)
    sym = list(sym)
    sym[1] = q(lib_id)
    return sym

def rename_units(e, old, new):
    if isinstance(e, list):
        return [rename_units(x, old, new) for x in e]
    if e.startswith('"' + old + "_"):
        return '"' + new + e[len(old) + 1:]
    return e

def pins_of(sym):
    """{pin_number: (x, y, angle)} in symbol coordinates (y up)."""
    res = {}
    def walk(e):
        for x in e:
            if isinstance(x, list):
                if x[0] == "pin":
                    at = next(y for y in x if isinstance(y, list) and y[0] == "at")
                    num = next(y for y in x if isinstance(y, list) and y[0] == "number")[1].strip('"')
                    if num not in res:  # feed-through header: same number on both sides
                        res[num] = (float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0)
                else:
                    walk(x)
    walk(sym)
    return res

def xform(px, py, rot):
    """symbol coords (y up) -> schematic offset (y down), symbol rotated CCW by rot."""
    import math
    r = math.radians(rot)
    x = px * math.cos(r) - py * math.sin(r)
    y = px * math.sin(r) + py * math.cos(r)
    return round(x, 4), round(-y, 4)

def outward(angle, rot):
    a = (angle + rot) % 360  # pin direction (toward body), in symbol coords
    return {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[int(a)]

# --------------------------------------------------------------------------
def write_pico_symbol():
    os.makedirs(os.path.join(PROJ, "lib"), exist_ok=True)
    pins = []
    for n, nm in PICO.items():
        if n <= 20:
            x, y, a = -15.24, 24.13 - 2.54 * (n - 1), 0
        else:
            x, y, a = 15.24, -24.13 + 2.54 * (n - 21), 180
        if nm in ("VBUS", "3V3"):
            typ = "power_out"
        elif nm in ("GND", "AGND", "VSYS", "ADC_VREF"):
            typ = "passive"
        else:
            typ = "bidirectional"
        pins.append(f'      (pin {typ} line (at {x} {y} {a}) (length 2.54)\n'
                    f'        (name {q(nm)} (effects (font (size 1.27 1.27))))\n'
                    f'        (number {q(n)} (effects (font (size 1.27 1.27)))))')
    fan_sym = """  (symbol "Fan_Header" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
    (property "Reference" "J" (at -3.81 -1.27 0) (effects (font (size 1.27 1.27)) (justify right)))
    (property "Value" "Fan" (at -3.81 1.27 0) (effects (font (size 1.27 1.27)) (justify right)))
    (property "Footprint" "Connector:FanPinHeader_1x03_P2.54mm_Vertical" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (symbol "Fan_Header_0_1"
      (circle (center 0 0) (radius 5.08) (stroke (width 0.254) (type default)) (fill (type background)))
      (arc (start 0 0) (mid 2.6 1.9) (end 3.6 -0.6) (stroke (width 0.254) (type default)) (fill (type none)))
      (arc (start 0 0) (mid -2.9 1.3) (end -1.3 3.5) (stroke (width 0.254) (type default)) (fill (type none)))
      (arc (start 0 0) (mid 0.3 -3.2) (end -2.3 -2.9) (stroke (width 0.254) (type default)) (fill (type none)))
      (text "+" (at 1.27 6.35 0) (effects (font (size 1.27 1.27))))
    )
    (symbol "Fan_Header_1_1"
      (pin passive line (at 0 -7.62 90) (length 2.54)
        (name "-" (effects (font (size 1.27 1.27))))
        (number "1" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 0 7.62 270) (length 2.54)
        (name "+" (effects (font (size 1.27 1.27))))
        (number "2" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 7.62 0 180) (length 2.54)
        (name "TACH" (effects (font (size 1.27 1.27))))
        (number "3" (effects (font (size 1.27 1.27)))))
    )
  )
"""
    txt = f'''(kicad_symbol_lib (version 20220914) (generator vent_fans_gen)
  (symbol "RaspberryPi_PicoW" (pin_names (offset 0.762)) (in_bom yes) (on_board yes)
    (property "Reference" "U" (at 0 27.94 0) (effects (font (size 1.27 1.27))))
    (property "Value" "RaspberryPi_PicoW" (at 0 -27.94 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "{NAME}:RaspberryPi_PicoW_THT" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Datasheet" "https://datasheets.raspberrypi.com/picow/pico-w-datasheet.pdf" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (symbol "RaspberryPi_PicoW_0_1"
      (rectangle (start -12.7 26.67) (end 12.7 -26.67) (stroke (width 0.254) (type default)) (fill (type background)))
      (text "USB" (at 0 24.13 0) (effects (font (size 1.27 1.27))))
    )
    (symbol "RaspberryPi_PicoW_1_1"
{chr(10).join(pins)}
    )
  )
{fan_sym})
'''
    open(os.path.join(PROJ, "lib", f"{NAME}.kicad_sym"), "w").write(txt)

def write_pico_footprint():
    d = os.path.join(PROJ, "lib", f"{NAME}.pretty")
    os.makedirs(d, exist_ok=True)
    pads = []
    for n in range(1, 41):
        if n <= 20:
            x, y = -8.89, -24.13 + 2.54 * (n - 1)
        else:
            x, y = 8.89, 24.13 - 2.54 * (n - 21)
        shape = "rect" if n == 1 else "oval"
        pads.append(f'  (pad "{n}" thru_hole {shape} (at {x} {y}) (size 1.7 1.7) (drill 1.02) '
                    f'(layers "*.Cu" "*.Mask") (tstamp {uid()}))')
    txt = f'''(footprint "RaspberryPi_PicoW_THT" (version 20221018) (generator vent_fans_gen)
  (layer "F.Cu")
  (descr "Raspberry Pi Pico W, through-hole on 2x20 2.54 mm headers (socketed). USB end at -Y, Wi-Fi antenna end at +Y: keep copper out from under the antenna.")
  (tags "RP2040 Pico W")
  (attr through_hole)
  (fp_text reference "REF**" (at 0 -27.2) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))) (tstamp {uid()}))
  (fp_text value "RaspberryPi_PicoW_THT" (at 0 27.2) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))) (tstamp {uid()}))
  (fp_text user "USB" (at 0 -23.5) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))) (tstamp {uid()}))
  (fp_text user "ANTENNA - keep clear" (at 0 21.5) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))) (tstamp {uid()}))
  (fp_rect (start -10.5 -25.5) (end 10.5 25.5) (stroke (width 0.12) (type default)) (fill none) (layer "F.SilkS") (tstamp {uid()}))
  (fp_rect (start -10.5 -25.5) (end 10.5 25.5) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab") (tstamp {uid()}))
  (fp_rect (start -10.75 -27.0) (end 10.75 25.75) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd") (tstamp {uid()}))
  (fp_rect (start -4 -26.6) (end 4 -25.5) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab") (tstamp {uid()}))
{chr(10).join(pads)}
)
'''
    open(os.path.join(d, "RaspberryPi_PicoW_THT.kicad_mod"), "w").write(txt)

# --------------------------------------------------------------------------
def build_schematic():
    """Draw the schematic the way a person would: parts placed in functional
    groups, nets drawn as wires, GND / +5V / +3V3 as power symbols."""
    root_uuid = uid()
    used = {}
    for ref, (lib_id, *_r) in PARTS.items():
        used[lib_id] = lib_symbol(lib_id)
    for p in POWER_NETS.values():
        used[p] = lib_symbol(p)
    used["power:PWR_FLAG"] = lib_symbol("power:PWR_FLAG")

    items, wires, pins_at = [], [], []   # pins_at: every symbol pin point (for splitting/junctions)
    counter = {"pwr": 0, "flg": 0}
    G = lambda v: round(v, 2)

    def P(ref, num):
        lib_id, _v, _f, (sx, sy), rot, _n, _d = PARTS[ref]
        px, py, _a = pins_of(used[lib_id])[str(num)]
        ox, oy = xform(px, py, rot)
        return (G(sx + ox), G(sy + oy))

    def poly(*pts):
        for a, b in zip(pts, pts[1:]):
            wires.append(((G(a[0]), G(a[1])), (G(b[0]), G(b[1]))))

    def power(net, x, y, direction=None):
        """power symbol whose pin sits at (x, y); direction = where it points."""
        lib = POWER_NETS[net] if net in POWER_NETS else "power:PWR_FLAG"
        if direction is None:
            direction = (0, 1) if net == "GND" else (0, -1)
        base = (0, 1) if net == "GND" else (0, -1)
        rot = {((0, 1), (0, 1)): 0, ((0, 1), (0, -1)): 180, ((0, 1), (1, 0)): 90, ((0, 1), (-1, 0)): 270,
               ((0, -1), (0, -1)): 0, ((0, -1), (0, 1)): 180, ((0, -1), (-1, 0)): 90, ((0, -1), (1, 0)): 270}[(base, direction)]
        if lib == "power:PWR_FLAG":
            counter["flg"] += 1; ref = f"#FLG0{counter['flg']}"; val = "PWR_FLAG"; rot = 0
        else:
            counter["pwr"] += 1; ref = f"#PWR{counter['pwr']:02d}"; val = net
        tx, ty = x + 4.2 * direction[0], y + 4.2 * direction[1]
        if direction[1] == 0:
            ty -= 0.0
        items.append(f'''  (symbol (lib_id {q(lib)}) (at {x} {y} {rot}) (unit 1)
    (in_bom yes) (on_board yes) (dnp no) (uuid {uid()})
    (property "Reference" {q(ref)} (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide))
    (property "Value" {q(val)} (at {G(tx)} {G(ty)} 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "" (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide))
    (pin "1" (uuid {uid()}))
    (instances (project {q(NAME)} (path "/{root_uuid}" (reference {q(ref)}) (unit 1))))
  )''')
        pins_at.append((G(x), G(y)))

    def stub_power(ref, num, net, direction):
        """short wire out of a pin, then a power symbol pointing the same way."""
        x, y = P(ref, num)
        ex, ey = G(x + 2.54 * direction[0]), G(y + 2.54 * direction[1])
        poly((x, y), (ex, ey))
        power(net, ex, ey, direction)

    def label(net, x, y):
        items.append(f'  (label {q(net)} (at {x} {y} 0) (fields_autoplaced)\n'
                     f'    (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid {uid()}))')

    def text(x, y, t, size=1.5):
        items.append(f'  (text {q(t)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left bottom)) (uuid {uid()}))')

    # ---- symbols -------------------------------------------------------------
    for ref, (lib_id, value, fp, (sx, sy), rot, nets, desc) in PARTS.items():
        sym = used[lib_id]
        pins = pins_of(sym)
        rdx, vdx, just = TEXT.get(ref, ((3.81, -1.27), (3.81, 1.27), " (justify left)"))
        pin_entries = "\n".join(f'    (pin {q(n)} (uuid {uid()}))' for n in pins)
        fa = rot if rot in (90, 270) else 0
        onb = "yes" if fp else "no"
        items.append(f'''  (symbol (lib_id {q(lib_id)}) (at {sx} {sy} {rot}) (unit 1)
    (in_bom yes) (on_board {onb}) (dnp no) (uuid {uid()})
    (property "Reference" {q(ref)} (at {G(sx + rdx[0])} {G(sy + rdx[1])} {fa}) (effects (font (size 1.27 1.27)){just}))
    (property "Value" {q(value)} (at {G(sx + vdx[0])} {G(sy + vdx[1])} {fa}) (effects (font (size 1.27 1.27)){just}))
    (property "Footprint" {q(fp)} (at {sx} {sy} 0) (effects (font (size 1.27 1.27)) hide))
    (property "Description" {q(desc)} (at {sx} {sy} 0) (effects (font (size 1.27 1.27)) hide))
{pin_entries}
    (instances (project {q(NAME)} (path "/{root_uuid}" (reference {q(ref)}) (unit 1))))
  )''')
        for num in pins:
            pt = P(ref, num)
            pins_at.append(pt)
            if not ((num.isdigit() and int(num) in nets) or num in nets):
                items.append(f'  (no_connect (at {pt[0]} {pt[1]}) (uuid {uid()}))')

    # ---- Pico W --------------------------------------------------------------
    for n in (3, 8, 13, 18):
        stub_power("U1", n, "GND", (-1, 0))
    for n in (23, 28, 33, 38):
        stub_power("U1", n, "GND", (1, 0))
    stub_power("U1", 36, "+3V3", (1, 0))

    # USB-C input: VBUS -> F1 -> +5V rail; CC1/CC2 -> 5.1k -> GND
    poly(P("J7", "A9"), P("F1", 1))
    label("VBUS_IN", 41.91, RAIL_5V)
    poly(P("F1", 2), (P("D1", 1)[0], RAIL_5V))
    power("+5V", 63.5, RAIL_5V)
    power("FLAG", 71.12, RAIL_5V)
    cc1, cc2 = P("J7", "A5"), P("J7", "B5")
    poly(cc1, (P("R6", 1)[0], cc1[1]), P("R6", 1))
    poly(cc2, (P("R7", 1)[0], cc2[1]), P("R7", 1))
    power("GND", *P("R6", 2)); power("GND", *P("R7", 2))
    power("GND", *P("J7", "A12")); power("GND", *P("J7", "S1"))
    # +5V rail -> D2 -> Pico VSYS
    poly((P("D2", 2)[0], RAIL_5V), P("D2", 2))
    vsys = P("U1", 39)
    poly(P("D2", 1), (P("D2", 1)[0], vsys[1]), vsys)
    label("+5V", 125.73, RAIL_5V)

    # input caps
    for c in ("C1", "C2"):
        x, y = P(c, 1)
        poly((x, RAIL_5V), (x, y))
        x2, y2 = P(c, 2)
        power("GND", x2, y2)

    # fans hang between the +5V rail and the FAN- rail
    for i in range(4):
        j = f"J{i + 1}"
        poly((P(j, 2)[0], RAIL_5V), P(j, 2))
        poly(P(j, 1), (P(j, 1)[0], RAIL_FANM))
    lx = P("L1", 1)[0]
    poly((FAN_X[0], RAIL_FANM), (lx, RAIL_FANM), (lx + 7.62, RAIL_FANM))
    label("FAN-", 205.74, RAIL_FANM)
    power("FLAG", G(lx + 7.62), RAIL_FANM)                 # FAN- is driven through L1 only
    poly((P("C3", 1)[0], RAIL_5V), P("C3", 1))
    poly(P("C3", 2), (P("C3", 2)[0], RAIL_FANM))

    # buck: L1 -> SW node -> Q1 drain, D1 back up to +5V
    poly((lx, RAIL_FANM), P("L1", 1))
    poly(P("L1", 2), (lx, SW_Y))
    dx = P("D1", 1)[0]
    poly((dx, RAIL_5V), P("D1", 1))
    poly(P("D1", 2), (dx, SW_Y), (lx, SW_Y))
    poly(P("Q1", 3), (lx, SW_Y))
    label("SW", 226.06, SW_Y)
    power("FLAG", 222.25, SW_Y)
    s = P("Q1", 2)
    poly(s, (s[0], s[1] + 5.08))
    power("GND", s[0], G(s[1] + 5.08))

    # gate drive
    poly(P("R1", 2), P("Q1", 1))
    power("GND", *P("R2", 2))
    label("GATE", 199.39, 111.76)
    g15 = P("U1", 20)
    poly(g15, (45.72, g15[1]), (45.72, 162.56), (187.96, 162.56), (187.96, 111.76), P("R1", 1))
    label("FAN_PWM", 152.4, 162.56)

    # override switch: GP18 -> R4 -> J6 pin 1 (ON), GP17 -> R5 -> J6 pin 3 (OFF)
    poly(P("U1", 24), P("R4", 2)); poly(P("R4", 1), P("J6", 1))
    poly(P("U1", 22), P("R5", 2)); poly(P("R5", 1), P("J6", 3))
    stub_power("J6", 2, "GND", (-1, 0))
    # 3-core cable from J6 to the off-board switch: ON over the top of J6, OFF
    # underneath, common to GND (in the cable it is J6 pin 2)
    j1, j3 = P("J6", 1), P("J6", 3)
    on, off, com = P("SW1", 3), P("SW1", 1), P("SW1", 2)
    poly(j1, (j1[0], 109.22), (134.62, 109.22), (134.62, on[1]), on)
    poly(j3, (j3[0], 129.54), (134.62, 129.54), (134.62, off[1]), off)
    poly(com, (G(com[0] + 2.54), com[1]), (G(com[0] + 2.54), G(com[1] + 2.54)))
    power("GND", G(com[0] + 2.54), G(com[1] + 2.54))
    # dashed box: this part is not on the PCB
    bx0, by0, bx1, by1 = 129.54, 104.14, 160.02, 134.62
    items.append(f'  (polyline (pts (xy {bx0} {by0}) (xy {bx1} {by0}) (xy {bx1} {by1}) (xy {bx0} {by1}) (xy {bx0} {by0}))\n'
                 f'    (stroke (width 0) (type dash)) (uuid {uid()}))')
    text(129.54, 102.87, "OFF-BOARD: on the wall plate / grille", 1.27)
    text(129.54, 137.16, "3-core cable to J6; common = J6 pin 2", 1.27)
    text(135.89, 115.57, "ON", 1.0)
    text(135.89, 125.73, "OFF", 1.0)
    text(146.05, 115.57, "centre = AUTO", 1.0)

    # DS18B20: GP16 -> DQ with the 4.7k pull-up to 3V3
    g16 = P("U1", 21)
    poly(g16, (83.82, g16[1]), (83.82, P("J5", 2)[1]), P("J5", 2))
    poly(P("R3", 2), (P("R3", 2)[0], P("J5", 2)[1])) if P("R3", 2)[1] != P("J5", 2)[1] else None
    power("+3V3", *P("R3", 1))
    stub_power("J5", 1, "GND", (-1, 0))
    stub_power("J5", 3, "+3V3", (-1, 0))
    label("ONEWIRE", 86.36, P("J5", 2)[1])

    # standalone controls
    poly(P("U1", 31), P("RV1", 2))                      # GP26 -> trimpot wiper (C4 taps the same wire)
    power("+3V3", *P("RV1", 3)); power("GND", *P("RV1", 1)); power("GND", *P("C4", 2))
    poly(P("U1", 14), P("R8", 1)); poly(P("R8", 2), P("D3", 2))   # GP10 -> R8 -> LED anode
    k = P("D3", 1); poly(k, (k[0], G(k[1] + 2.54))); power("GND", k[0], G(k[1] + 2.54))
    poly(P("U1", 16), P("SW2", 2))                      # GP12 -> LEARN button -> GND
    b = P("SW2", 1); poly(b, (b[0], G(b[1] + 2.54))); power("GND", b[0], G(b[1] + 2.54))
    text(12.7, 101.6, "Standalone controls", 1.27)
    text(99.06, 93.98, "Speed trimpot", 1.0)

    # GND needs a flag (the Pico's GND pins are passive)
    power("FLAG", 25.4, 160.02)
    poly((25.4, 160.02), (25.4, 165.1))
    power("GND", 25.4, 165.1)

    # ---- tidy the wires: split at every point where something connects, add dots
    pts = set(pins_at)
    for a, b in wires:
        pts.add(a); pts.add(b)
    def on_seg(p, a, b):
        if a[0] == b[0] == p[0]:
            return min(a[1], b[1]) < p[1] < max(a[1], b[1])
        if a[1] == b[1] == p[1]:
            return min(a[0], b[0]) < p[0] < max(a[0], b[0])
        return False
    final = []
    for a, b in wires:
        if a == b:
            continue
        cuts = sorted([p for p in pts if on_seg(p, a, b)], key=lambda p: abs(p[0] - a[0]) + abs(p[1] - a[1]))
        chain = [a] + cuts + [b]
        final += list(zip(chain, chain[1:]))
    count = {}
    for a, b in final:
        count[a] = count.get(a, 0) + 1; count[b] = count.get(b, 0) + 1
    for p in pins_at:
        if p in count:
            count[p] += 1
    for (x, y) in final:
        items.append(f'  (wire (pts (xy {x[0]} {x[1]}) (xy {y[0]} {y[1]})) (stroke (width 0) (type default)) (uuid {uid()}))')
    for p, c in count.items():
        if c >= 3:
            items.append(f'  (junction (at {p[0]} {p[1]}) (diameter 0) (color 0 0 0 0) (uuid {uid()}))')

    # ---- notes ---------------------------------------------------------------
    text(25.4, 25.4, "AC register fan booster - Pico W + low-side buck: the fans get smooth DC = duty x 5 V", 2)
    text(129.54, 33.02, "POWER STAGE: Q1 switches at 40 kHz, L1 + C3 filter it to DC across the fans.")
    text(129.54, 38.1, "FAN- is NOT ground. Never tie a fan's black wire to GND or to the metal duct.")
    text(129.54, 43.18, "3 fans fitted; J4 is optional (4 x 0.25 A fans = 1 A max).", 1.27)
    text(88.9, 157.48, "DS18B20 duct probe: HA sensor + fallback when HA is down", 1.27)

    libs = "\n".join("    " + dump(s, 2) for s in used.values())
    sch = f'''(kicad_sch (version 20230121) (generator eeschema)
  (uuid {root_uuid})
  (paper "A4")
  (title_block
    (title "AC register smart fan booster - controller")
    (rev "1.1")
    (comment 1 "Pico W + SI2302CDS low-side buck, 3-4x 5 V fans (up to 1 A total)")
    (comment 2 "Generated by tools/gen_schematic.py - simulated in ../sim (ngspice)")
  )
  (lib_symbols
{libs}
  )
{chr(10).join(items)}
  (sheet_instances (path "/" (page "1")))
)
'''
    open(os.path.join(PROJ, f"{NAME}.kicad_sch"), "w").write(sch)

def write_project_files():
    open(os.path.join(PROJ, "sym-lib-table"), "w").write(
        f'(sym_lib_table\n  (lib (name "{NAME}")(type "KiCad")(uri "${{KIPRJMOD}}/lib/{NAME}.kicad_sym")(options "")(descr "Project symbols"))\n)\n')
    open(os.path.join(PROJ, "fp-lib-table"), "w").write(
        f'(fp_lib_table\n  (lib (name "{NAME}")(type "KiCad")(uri "${{KIPRJMOD}}/lib/{NAME}.pretty")(options "")(descr "Project footprints"))\n)\n')
    pro = {"meta": {"filename": f"{NAME}.kicad_pro", "version": 1},
           "board": {"design_settings": {"rules": {"min_clearance": 0.2, "min_track_width": 0.25},
                                          "defaults": {}}},
           "net_settings": {"classes": [
               {"name": "Default", "clearance": 0.2, "track_width": 0.3, "via_diameter": 0.8, "via_drill": 0.4},
               {"name": "Power", "clearance": 0.25, "track_width": 0.8, "via_diameter": 1.0, "via_drill": 0.5}],
               "netclass_patterns": [{"netclass": "Power", "pattern": n} for n in ("VBUS_IN", "+5V", "GND", "FAN-", "SW")],
               "meta": {"version": 3}},
           "sheets": [], "boards": [], "text_variables": {}}
    path = os.path.join(PROJ, f"{NAME}.kicad_pro")
    json.dump(pro, open(path, "w"), indent=2)

if __name__ == "__main__":
    write_pico_symbol()
    write_pico_footprint()
    build_schematic()
    write_project_files()
    print("schematic written")
