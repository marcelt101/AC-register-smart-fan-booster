// Fan frame for a 4" x 10" floor/wall register boot.
//
// A plate that drops into the boot opening under the register grille. Its
// lip rests on the floor/drywall around the opening, and the grille sits on top.
// The fans hang underneath, screwed to the plate, blowing UP/OUT into the room.
//
//   3 x 80 mm fans  (default; best airflow for a 10" opening)
//   4 x 60 mm fans  (set fan = 60, n_fans = 4; 4 x 80 mm cannot fit in 10")
//
// Print in PETG or ASA, not PLA: supply air in heating mode reaches ~50-60 C.
// Needs boot depth >= fan thickness + plate (about 30 mm for 25 mm fans).
// Measure the actual hole (not the grille) and set opening_w / opening_h.

/* [Opening, measure the hole in the floor/wall] */
opening_w = 254;     // 10"
opening_h = 101.6;   // 4"
fit_gap   = 1.0;     // clearance per side so the plate drops in

/* [Fans] */
fan    = 80;         // 80 or 60
n_fans = 3;          // 3 (or 4 with 60 mm fans)
fan_screw = (fan == 80) ? 71.5 : (fan == 60 ? 50 : 32); // hole spacing
screw_d   = (fan == 80) ? 4.3 : 3.6;                     // through-hole for fan screws
fan_gap   = 2;       // minimum gap between fans

/* [Plate] */
plate_t = 3;         // plate thickness inside the opening
lip_w   = 6;         // lip that rests on the floor around the opening
lip_t   = 1.6;       // keep thin so the grille still sits flat
wire_notch = 10;     // notch in one end for the fan leads to reach the PCB

/* [Printing] */
split = true;        // two halves, for beds smaller than the full length (~266 mm)

$fn = 64;
eps = 0.01;

inner_w = opening_w - 2 * fit_gap;
inner_h = opening_h - 2 * fit_gap;
pitch   = fan + fan_gap;
span    = n_fans * pitch - fan_gap;
assert(span <= inner_w - 4, str(n_fans, " x ", fan, " mm fans need ", span + 4,
        " mm but the opening only has ", inner_w, " mm"));
assert(fan <= inner_h - 4, "fans taller than the opening");

function fan_x(i) = -span / 2 + fan / 2 + i * pitch;

module rounded_rect(w, h, r) {
    offset(r) square([w - 2 * r, h - 2 * r], center = true);
}

module plate_2d() {
    difference() {
        rounded_rect(inner_w, inner_h, 3);
        for (i = [0 : n_fans - 1]) {
            translate([fan_x(i), 0]) {
                circle(d = fan - 3);                       // air hole
                for (sx = [-1, 1], sy = [-1, 1])
                    translate([sx * fan_screw / 2, sy * fan_screw / 2]) circle(d = screw_d);
            }
        }
        translate([inner_w / 2 - 2, 0]) square([8, wire_notch], center = true);
    }
}

module frame() {
    // plate that sits inside the opening, top flush with the floor
    translate([0, 0, -plate_t]) linear_extrude(plate_t) plate_2d();
    // lip on top that rests on the floor; same holes and notch
    linear_extrude(lip_t) difference() {
        rounded_rect(opening_w + 2 * lip_w, opening_h + 2 * lip_w, 4);
        rounded_rect(inner_w - 2, inner_h - 2, 2);
        translate([opening_w / 2 + lip_w / 2, 0]) square([lip_w + 2, wire_notch], center = true);
    }
    // ribs between fans keep the long plate stiff
    for (i = [0 : n_fans - 2])
        translate([fan_x(i) + pitch / 2, 0, -plate_t - 6])
            linear_extrude(6 + eps) square([1.6, fan - 2], center = true);  // stays clear of the splice tabs
}

// Split on the rib between the first two fans. The halves join with two small
// splice tabs under the solid bands above and below the fans (clear of the
// fan bodies), each with two M3 x 10 screws or glue.
cut_x = fan_x(0) + pitch / 2;
band_y = inner_h / 2 - 4.5;                 // centre of the solid band beyond the fans
splice_holes = [for (sx = [-6, 6], sy = [-1, 1]) [cut_x + sx, sy * band_y]];

module with_splice_holes() {
    difference() {
        children();
        for (p = splice_holes) translate([p[0], p[1], -20]) cylinder(d = 3.4, h = 40);
    }
}

module splice() {
    difference() {
        for (sy = [-1, 1]) translate([cut_x, sy * band_y, -plate_t - 3])
            linear_extrude(3) square([24, 7], center = true);
        for (p = splice_holes) translate([p[0], p[1], -20]) cylinder(d = 3.4, h = 40);
    }
}

if (split) {
    big = 1000;
    // half A (left of the cut)
    with_splice_holes() intersection() {
        frame();
        translate([cut_x - big, -big / 2, -big / 2]) cube(big);
    }
    // half B, moved apart for printing
    translate([20, 0, 0]) with_splice_holes() intersection() {
        frame();
        translate([cut_x, -big / 2, -big / 2]) cube(big);
    }
    // splice tabs, laid beside the parts
    translate([0, opening_h + lip_w + 20, plate_t + 3]) splice();
} else {
    frame();
}
