#!/bin/sh
# Export print-ready STLs for one vent.
#   ./make_stl.sh <opening_w_mm> <opening_h_mm> <fan_mm 80|60> <n_fans> [floor|wall]
#   ./make_stl.sh 254 101.6 80 3 floor
# Writes stl/<name>_base_full / _bezel_full (one-piece set) and
# _base_a/_base_b/_bezel_a/_bezel_b/_tabs (split set for normal beds), then
# prints each part's size and the mesh size / screw count.
set -e
cd "$(dirname "$0")"
W=${1:?opening width mm}; H=${2:?opening height mm}; FAN=${3:-80}; N=${4:-3}; MOUNT=${5:-floor}
NAME="frame_${N}x${FAN}_${W}x${H}_${MOUNT}"
mkdir -p stl
ARGS="-D opening_w=$W -D opening_h=$H -D fan=$FAN -D n_fans=$N -D mount=\"$MOUNT\""
for P in base_full bezel_full base_a base_b bezel_a bezel_b tabs; do
  eval openscad -q $ARGS -D "part=\\\"$P\\\"" -o "stl/${NAME}_$P.stl" frame.scad
done
eval openscad $ARGS -D "part=\\\"assembly\\\"" -o /dev/null --export-format stl frame.scad 2>&1 | sed -n 's/^ECHO: "\(.*\)"$/\1/p'
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
