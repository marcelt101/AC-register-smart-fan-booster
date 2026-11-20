// Fan frame + mesh cover for a 4" x 10" register opening (replaces the grille).
//
//            bezel (printed, chamfered edge)   <- screws down through the mesh
//   ===========[ wire mesh ]===========        <- coarse steel/aluminium mesh
//   ___________________________________        <- base: flange on the floor,
//        |  plate in the opening  |               plate drops into the hole
//        [fan][fan][fan]  hang under the plate, blowing up into the room
//
//   3 x 80 mm fans  (default; best airflow for a 10" opening)
//   4 x 60 mm fans  (fan = 60, n_fans = 4; 4 x 80 mm cannot fit in 10")
//
// z = 0 is the floor (or wall) surface. Print in PETG or ASA, not PLA:
// supply air in heating mode reaches ~50-60 C.
// Needs boot depth >= fan thickness + plate (about 30 mm for 25 mm fans).
// Measure the actual hole in the boot and set opening_w / opening_h.

/* [Opening: measure the hole in the floor/wall] */
opening_w = 254;     // 10"
opening_h = 101.6;   // 4"
fit_gap   = 1.0;     // clearance per side so the plate drops in
mount     = "floor"; // "floor" (rests by gravity) or "wall" (4 screws through the flange)

/* [Fans] */
fan    = 80;         // 80 or 60
n_fans = 3;          // 3 (or 4 with 60 mm fans)
fan_screw = (fan == 80) ? 71.5 : (fan == 60 ? 50 : 32); // hole spacing
screw_d   = (fan == 80) ? 4.3 : 3.6;                     // through-hole for fan screws
fan_gap   = 2;       // minimum gap between fans
spokes    = true;    // printed cross over each fan hole: holds the mesh up when stepped on

/* [Base and cover] */
plate_t  = 3;        // plate below the floor surface, inside the opening
base_t   = 2;        // flange thickness on top of the floor
flange_w = 15;       // visible border around the opening (covers a rough floor cut)
mesh_t   = 1.0;      // mesh thickness: ~0.7-1 hardware cloth, ~1.5 expanded metal
bezel_t  = 2.5;      // top ring thickness above the mesh
mesh_margin = 8;     // mesh overlap under the bezel on every side

/* [Printing] */
// What to render:
//   "assembly"                   as installed (mesh shown grey)
//   "base_full", "bezel_full"    one-piece parts, print orientation
//   "base_a", "base_b", "bezel_a", "bezel_b", "tabs"   split parts for normal beds
part = "assembly";

$fn = 64;
eps = 0.01;

inner_w = opening_w - 2 * fit_gap;
inner_h = opening_h - 2 * fit_gap;
outer_w = opening_w + 2 * flange_w;
outer_h = opening_h + 2 * flange_w;
pitch   = fan + fan_gap;
span    = n_fans * pitch - fan_gap;
assert(span <= inner_w - 4, str(n_fans, " x ", fan, " mm fans need ", span + 4,
        " mm but the opening only has ", inner_w, " mm"));
assert(fan <= inner_h - 4, "fans taller than the opening");

function fan_x(i) = -span / 2 + fan / 2 + i * pitch;

// window in the bezel = the air path; the mesh is clamped around it
win_w  = span + 4;
win_h  = min(fan + 2, inner_h - 14);
mesh_w = win_w + 2 * mesh_margin;
mesh_h = win_h + 2 * mesh_margin;
top_z  = base_t + mesh_t + bezel_t;       // height of the finished cover above the floor

// bezel screws (M3 countersunk) go down through the mesh into the plate, in the
// solid band between the fan holes and the edge of the opening
band_y = (win_h / 2 + inner_h / 2) / 2;
screw_xs = concat([-(span / 2 - 10)], [for (i = [0 : n_fans - 2]) fan_x(i) + pitch / 2], [span / 2 - 10]);
bezel_screws = [for (x = screw_xs, sy = [-1, 1]) [x, sy * band_y]];
wall_screws = [for (sx = [-1, 1], sy = [-1, 1]) [sx * (outer_w / 2 - flange_w / 2), sy * (outer_h / 2 - flange_w / 2)]];

module rounded_rect(w, h, r) {
    offset(r) square([w - 2 * r, h - 2 * r], center = true);
}

// ---- base -----------------------------------------------------------------
module base_2d_plate() {
    difference() {
        rounded_rect(inner_w, inner_h, 3);
        for (i = [0 : n_fans - 1])
            translate([fan_x(i), 0]) difference() {
                circle(d = fan - 3);                                   // air hole
                if (spokes) for (a = [45, 135]) rotate(a) square([fan, 3], center = true);
            }
        for (i = [0 : n_fans - 1], sx = [-1, 1], sy = [-1, 1])        // fan screws
            translate([fan_x(i) + sx * fan_screw / 2, sy * fan_screw / 2]) circle(d = screw_d);
    }
}

module base() {
    difference() {
        union() {
            // plate in the opening, top flush with the flange top
            translate([0, 0, -plate_t]) linear_extrude(plate_t + base_t) base_2d_plate();
            // flange on the floor
            linear_extrude(base_t) difference() {
                rounded_rect(outer_w, outer_h, 6);
                rounded_rect(inner_w - 2, inner_h - 2, 2);
            }
            // ribs between fans keep the long plate stiff
            for (i = [0 : n_fans - 2])
                translate([fan_x(i) + pitch / 2, 0, -plate_t - 6])
                    linear_extrude(6 + eps) square([1.6, fan - 2], center = true);
        }
        // pilot holes for the M3 bezel screws (self-tap into PETG, or 4.0 mm for heat-set inserts)
        for (p = bezel_screws) translate([p[0], p[1], -plate_t - 1]) cylinder(d = 2.6, h = 20);
        if (mount == "wall") for (p = wall_screws) translate([p[0], p[1], -1]) cylinder(d = 4, h = 20);
    }
}

// ---- bezel (top ring that clamps the mesh) ----------------------------------
module bezel() {
    h = mesh_t + bezel_t;
    difference() {
        // chamfered outer edge so it is not a trip edge
        hull() {
            translate([0, 0, base_t]) linear_extrude(eps) rounded_rect(outer_w, outer_h, 6);
            translate([0, 0, top_z - eps]) linear_extrude(eps) rounded_rect(outer_w - 2 * bezel_t, outer_h - 2 * bezel_t, 6 - bezel_t / 2);
        }
        translate([0, 0, base_t - 1]) linear_extrude(h + 2) rounded_rect(win_w, win_h, 3);          // air window
        translate([0, 0, base_t - eps]) linear_extrude(mesh_t + eps) rounded_rect(mesh_w + 1, mesh_h + 1, 1); // mesh pocket
        for (p = bezel_screws) translate([p[0], p[1], 0]) {
            cylinder(d = 3.4, h = 20);                                      // M3 clearance
            translate([0, 0, top_z - 1.7]) cylinder(d1 = 3.4, d2 = 6.6, h = 1.7 + eps); // countersink
        }
        if (mount == "wall") for (p = wall_screws) translate([p[0], p[1], 0]) {
            cylinder(d = 4, h = 20);
            translate([0, 0, top_z - 2]) cylinder(d1 = 4, d2 = 8, h = 2 + eps);
        }
    }
}

module mesh_preview(pitch = 6.35, wire = 0.8) {   // 1/4" hardware cloth, for the picture only
    color("silver") translate([0, 0, base_t]) linear_extrude(mesh_t) intersection() {
        rounded_rect(mesh_w, mesh_h, 1);
        union() {
            for (x = [-mesh_w / 2 : pitch : mesh_w / 2]) translate([x, 0]) square([wire, mesh_h], center = true);
            for (y = [-mesh_h / 2 : pitch : mesh_h / 2]) translate([0, y]) square([mesh_w, wire], center = true);
        }
    }
}

// ---- splitting for normal-size printer beds --------------------------------
// The base splits on the rib between fans 1 and 2; the bezel splits between the
// last two fans, so each bezel piece bridges the base joint. Two splice tabs
// under the plate (M3 x 10) join the base halves.
cut_base  = fan_x(0) + pitch / 2;
cut_bezel = fan_x(n_fans - 1) - pitch / 2;
tab_y = inner_h / 2 - 4.5;
splice_holes = [for (sx = [-6, 6], sy = [-1, 1]) [cut_base + sx, sy * tab_y]];

module with_splice_holes() {
    difference() {
        children();
        for (p = splice_holes) translate([p[0], p[1], -20]) cylinder(d = 3.4, h = 40);
    }
}
module tabs() {
    difference() {
        for (sy = [-1, 1]) translate([cut_base, sy * tab_y, -plate_t - 3])
            linear_extrude(3) square([24, 7], center = true);
        for (p = splice_holes) translate([p[0], p[1], -20]) cylinder(d = 3.4, h = 40);
        for (p = bezel_screws) translate([p[0], p[1], -20]) cylinder(d = 2.6, h = 40);  // bezel screw bites into the tab too
    }
}

big = 1000;
module left_of(x)  { intersection() { children(); translate([x - big, -big / 2, -big / 2]) cube(big); } }
module right_of(x) { intersection() { children(); translate([x, -big / 2, -big / 2]) cube(big); } }

// Print orientation: base upside down (flat top face on the bed, ribs up);
// bezel upside down too (flat top on the bed, mesh pocket facing up).
module print_base()  { translate([0, 0, base_t]) rotate([180, 0, 0]) children(); }
module print_bezel() { translate([0, 0, top_z]) rotate([180, 0, 0]) children(); }

if (part == "assembly") { base(); mesh_preview(); bezel(); }
else if (part == "base_full")  print_base() base();
else if (part == "base_a")     print_base() with_splice_holes() left_of(cut_base) base();
else if (part == "base_b")     print_base() with_splice_holes() right_of(cut_base) base();
else if (part == "bezel_full") print_bezel() bezel();
else if (part == "bezel_a")    print_bezel() left_of(cut_bezel) bezel();
else if (part == "bezel_b")    print_bezel() right_of(cut_bezel) bezel();
else if (part == "tabs")       translate([0, 0, plate_t + 3]) tabs();
else assert(false, str("unknown part: ", part));

echo(str("FRAME: outer ", outer_w, " x ", outer_h, " mm, ", top_z, " mm above the floor; ",
         "cut the mesh to ", mesh_w, " x ", mesh_h, " mm; ",
         len(bezel_screws), " x M3 x 8 countersunk screws"));
