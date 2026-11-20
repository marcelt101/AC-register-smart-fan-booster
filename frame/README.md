# Fan frame and mesh cover (3D print)

This replaces the original register grille entirely. Three printed parts and
a sheet of wire mesh:

- **Base**: a plate that drops into the boot opening, with a 15 mm flange on
  the floor around it. The fans screw to its underside and blow up into the
  room. A printed cross over each fan hole holds the mesh up if someone steps
  on it.
- **Mesh**: coarse wire mesh. It's the only thing between fingers and fan
  blades, and it restricts airflow far less than a stamped grille.
- **Bezel**: a ring on top that clamps the mesh, with a chamfered edge so it
  isn't a trip edge. It screws down through the mesh into the base with M3
  countersunk screws.

The finished cover sits about 5.5 mm above the floor, similar to a normal grille.

![3 x 80 mm with 1/4" mesh](preview_3x80.png)

## 1. Measure the vent

Take the grille off and measure the **hole** (the sheet-metal boot opening).
Use mm if you can, to ±1 mm.

| # | What | Why |
|---|---|---|
| A | Opening **width**, inside edge to inside edge (the long side) | `opening_w` |
| B | Opening **height** (the short side) | `opening_h` |
| C | **Depth** from the floor surface down to anything in the way (boot bend, damper, screws) | Fans hang below the plate: 25 mm fans need about **30 mm**, 15 mm slim fans about 20 mm |
| D | How far the **rough cut in the flooring** extends past the boot on each side | The 15 mm flange must cover it (`flange_w` can grow) |
| E | Anything sticking into the opening (screw tabs, a damper) | I'll cut notches |
| F | **Floor, wall or ceiling** register? | Floor rests by gravity; wall/ceiling adds 4 screws through the flange |

## 2. Buy the mesh and screws

**Mesh: ¼" (6 mm) openings or smaller.** That keeps fingers (and kids' and
pets' fingers) out of the blades while staying about 70–80 % open. Any of these work:

- **¼" galvanised hardware cloth** (welded wire, ~0.6–0.9 mm wire). Cheap and
  easy to cut with tin snips. Fine for a wall vent, OK for a floor vent thanks
  to the support crosses.
- **Expanded aluminium or steel sheet**, ¼"–⅜" diamonds, ~1–1.5 mm thick.
  Stiffer and better for a **floor** vent that gets walked on. Set `mesh_t` to
  its thickness.
- **Perforated metal** with ≥ 60 % open area is fine too, though it restricts
  a little more.

Cut the mesh to the size `make_stl.sh` prints (264 × 98 mm for the nominal
vent), and file the cut edges.

**Screws:**
- 8 × **M3 × 8 countersunk** (flat-head) to hold the bezel down (10 for 4 fans).
  They self-tap into the printed pilot holes. For lots of removal, fit M3
  heat-set inserts instead and drill the pilots to 4.0 mm.
- 4 × M3 × 10 + nuts, only for the split base (joins the two halves on the tabs).
- 12 × fan screws (usually included with the fans), plus rubber grommets or
  foam washers if you want to cut vibration noise.

## 3. Make the STLs

Send me the numbers and I'll update and export them, or run it yourself
(needs OpenSCAD):

```sh
./make_stl.sh <A width mm> <B height mm> <fan 80|60> <number of fans> <floor|wall>
./make_stl.sh 254 101.6 80 3 floor
```

It writes these files in `stl/`, and prints each part's size, the mesh size
and the screw count:

| Set | Files | Printer |
|---|---|---|
| One piece | `_base_full`, `_bezel_full` | Bed longer than ~284 mm (Bambu H2D, Prusa XL, Creality K1 Max…) |
| Split | `_base_a`, `_base_b`, `_bezel_a`, `_bezel_b`, `_tabs` | Normal 220–256 mm beds (largest part ~183 × 132 mm for 3 × 80) |

In the split set the base and bezel are cut at **different** places, so each
bezel piece bridges the base joint and the bezel screws pull everything into
one rigid part. The two small tabs under the base joint add more strength.

`make_stl.sh` refuses fan counts that don't fit (for example, 4 × 80 mm in a
10" opening) and says why. The files in `stl/` now are for the **nominal**
4" × 10" opening. **Re-export after measuring.**

## 4. Print settings (for the printer operator)

- **Material: PETG or ASA. Not PLA.** Supply air in heating mode reaches
  50–60 °C, which softens PLA. For a floor vent, PETG is the tougher choice.
- Orientation: as exported (each part's flat top face on the bed). **No supports.**
- 0.2 mm layers, 4–5 walls, 40 % infill (floor vent) or 25 % (wall).
- Colour: the bezel is the visible part. Match the floor or the wall.

## 5. Assemble and install

1. **Split version:** bolt base A and base B together on the two tabs (M3 × 10
   + nuts, from the underside).
2. Screw the fans to the underside of the base, label side **down** (so they
   blow up into the room). Add grommets or foam washers if you have them.
3. Lay the mesh on top of the base. It sits inside the bezel's pocket.
4. Put the bezel on and screw it down through the mesh with the M3
   countersunk screws. With hardware cloth the screws go through the openings;
   with expanded or perforated metal, drill 3.5 mm holes where the screw holes
   land (use the bezel as a template).
5. Feed the fan leads down the boot to the controller (out through a grommet
   in the boot wall).
6. Optional: run thin foam weatherstrip under the flange so it seals and
   doesn't rattle. Drop it into the opening (floor), or screw through the four
   flange holes (wall).
