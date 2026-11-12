"""Rewrite a dry-run's inputs into the two-switch victim-flow experiment.

    python3 two_switch.py RUN_DIR --extra N --buf MIB [--prio P] [--alone] [--qcn 0|1]

Hosts: 0 = R (incast receiver), 1 = VR (idle), 2 = VS (victim source, sends nothing else), 3 = S (incast sender),
4 .. 3+N = extra incast senders. Switch A = first switch id, holds VS and S. Switch B = second, holds R, VR and the
extra senders. A and B share one link. The victim VS -> VR crosses A -> B; the extra senders share no link with it.
Every link is 100 Gb/s, 1 us. The incast uses priority 3; each flow is 1 MB and starts at 2.0 s.
"""
import argparse
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("run", type=Path)
p.add_argument("--extra", type=int, default=6)
p.add_argument("--buf", default="1")
p.add_argument("--prio", type=int, default=3)
p.add_argument("--alone", action="store_true")
p.add_argument("--qcn", default="1")
a = p.parse_args()

hosts = 4 + a.extra
A, B = hosts, hosts + 1
links = [(2, A), (3, A), (A, B), (0, B), (1, B)] + [(h, B) for h in range(4, hosts)]
nodes = hosts + 2
topo = [f"{nodes} 2 {len(links)}", f"{A} {B}"] + [f"{x} {y} 100Gbps 1000ns 0.000000" for x, y in links]
(a.run / "topology.txt").write_text("\n".join(topo) + "\n")

flows = [] if a.alone else [f"{s} 0 3 {100 + i} 1000000 2.0" for i, s in enumerate([3] + list(range(4, hosts)))]
flows.append(f"2 1 {a.prio} 200 1000000 2.0")
(a.run / "flow.txt").write_text(f"{len(flows)}\n" + "\n".join(flows) + "\n")
(a.run / "trace.txt").write_text(f"{nodes}\n" + " ".join(map(str, range(nodes))) + "\n")

cfg = []
for line in (a.run / "config.txt").read_text().splitlines():
    key = line.split(" ", 1)[0]
    cfg.append({"BUFFER_SIZE": f"BUFFER_SIZE {a.buf}", "ENABLE_QCN": f"ENABLE_QCN {a.qcn}"}.get(key, line))
(a.run / "config.txt").write_text("\n".join(cfg) + "\n")
