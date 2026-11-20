#!/bin/sh
# Export print-ready STLs for one vent.
#   ./make_stl.sh <opening_w_mm> <opening_h_mm> <fan_mm 80|60> <n_fans>
#   ./make_stl.sh 254 101.6 80 3
# Writes stl/<name>_full.stl (one piece) and _half_a/_half_b/_tabs.stl (split),
# then prints each part's footprint so the printer operator can pick one.
set -e
cd "$(dirname "$0")"
W=${1:?opening width mm}; H=${2:?opening height mm}; FAN=${3:-80}; N=${4:-3}
NAME="frame_${N}x${FAN}_${W}x${H}"
mkdir -p stl
for P in full half_a half_b tabs; do
  openscad -q -D "opening_w=$W" -D "opening_h=$H" -D "fan=$FAN" -D "n_fans=$N" \
           -D "part=\"$P\"" -o "stl/${NAME}_$P.stl" frame.scad
done
python3 - "$NAME" <<'PY'
import sys, glob
for f in sorted(glob.glob(f"stl/{sys.argv[1]}_*.stl")):
    xs, ys, zs = [], [], []
    for line in open(f):
        t = line.split()
        if t and t[0] == "vertex":
            xs.append(float(t[1])); ys.append(float(t[2])); zs.append(float(t[3]))
    print(f"{f:45s} {max(xs)-min(xs):6.1f} x {max(ys)-min(ys):6.1f} x {max(zs)-min(zs):5.1f} mm"
          f"   (lowest z = {min(zs):.2f})")
PY
