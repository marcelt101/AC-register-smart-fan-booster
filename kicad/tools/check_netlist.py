#!/usr/bin/env python3
"""Export the schematic netlist with kicad-cli and verify it against PARTS."""
import re, subprocess, sys, os, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import gen_schematic as g
net_file = os.path.join(tempfile.gettempdir(), "vent_fans.net")
subprocess.run(["kicad-cli", "sch", "export", "netlist", "-o", net_file,
                os.path.join(g.PROJ, "vent_fans.kicad_sch")], check=True, capture_output=True)
nets = {}
for blk in open(net_file).read().split("(net (code")[1:]:
    name = re.search(r'\(name "([^"]*)"\)', blk).group(1).lstrip("/")
    nets[name] = set(re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', blk))
want = {}
for ref, (lib, val, fp, pos, rot, pn, desc) in g.PARTS.items():
    for p, n in pn.items():
        want.setdefault(n, set()).add((ref, str(p)))
bad = 0
# compare connectivity, not names: unlabelled wires get auto names in KiCad
by_node = {node: name for name, nodes in nets.items() for node in nodes}
for n, nodes in sorted(want.items()):
    got_names = {by_node.get(nd) for nd in nodes}
    got = nets.get(next(iter(got_names)), set()) if len(got_names) == 1 and None not in got_names else None
    if got != nodes:
        bad += 1; print(f"MISMATCH {n}: want {sorted(nodes)} got {sorted(got or [])} in {got_names}")
    else:
        print(f"ok  {n:9s} {len(nodes):2d} pins  (KiCad net: {next(iter(got_names))})")
wanted = {frozenset(v) for v in want.values()}
extra = [n for n, v in nets.items() if frozenset(v) not in wanted and not n.startswith("unconnected")]
if extra: bad += 1; print("unexpected nets:", extra)
print("NETLIST OK" if not bad else f"{bad} PROBLEM(S)"); sys.exit(1 if bad else 0)
