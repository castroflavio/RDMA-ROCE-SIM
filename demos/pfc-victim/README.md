# Demo: the flow that a PAUSE stops by mistake

Does a PFC PAUSE caused by one congested port also stop a flow to an idle host? This demo answers that with four
runs of the simulator in this repository, on a small fat-tree of 16 hosts. Each run sends one 1 MB "victim" flow from
host 3 to host 12, which is idle, and measures how long it takes. Three of the runs add an 8:1 incast to host 0.

It accompanies the post *How do lossless DC fabrics work?*

## What you need

- Docker. The simulator image is x86; on Apple Silicon, Docker runs it under Rosetta.
- About 3 GB of disk for the image, and about 4 minutes to build it once.
- `make` and `awk`.

## 1. Build the simulator

From this folder:

```
make setup
```

This builds the repository's Docker image, `rdma-sim`: ns-3 with the RoCEv2 model released with the HPCC paper
(Li et al., *HPCC: High Precision Congestion Control*, SIGCOMM 2019). It models RoCEv2, ECN, PFC, DCQCN and a
shared-buffer switch.

## 2. Run the four experiments

```
make all
```

The four runs take about 2 minutes together. You should see:

```
alone           victim   95.4 us   PAUSE frames received: 0
big-buffer      victim  115.3 us   PAUSE frames received: 0
pfc             victim  608.1 us   PAUSE frames received: 263
other-priority  victim  122.2 us   PAUSE frames received: 262
```

Each run changes one thing from the run above it:

| Run | Incast (hosts 1–8 → host 0) | Switch buffer | Victim's priority |
|---|---|---|---|
| `alone` | no | 32 MiB | 3 |
| `big-buffer` | yes | 32 MiB | 3 |
| `pfc` | yes | 1 MiB | 3 |
| `other-priority` | yes | 1 MiB | 1 |

The PAUSE count is for the whole fabric. You can run any one of them on its own, for example `make pfc`.
`make summary` reprints the results.

## 3. What a run does

The topology is a k=4 fat-tree: 16 hosts in 4 pods, two hosts per edge switch, every link 100 Gb/s with a 1 µs
delay. Switches are numbered after the hosts: edge switches 16–23 (host n attaches to edge 16 + n/2), aggregation
switches 24–31, core switches 32–35. Host 3 shares edge switch 17 with host 2. Both send incast traffic to host 0,
so edge 17's two uplinks to the aggregation layer carry the incast and the victim on the same priority.

Each target in the `Makefile` does four steps:

1. `experiments.run --dry-run` writes the simulator's inputs into `results/pfc-victim/k4/<run>/` at the top of the
   repository: `config.txt`, the topology and `flow.txt`, the list of flows. It does not run anything yet.
2. `sed` sets `BUFFER_SIZE` in `config.txt`. The simulator reads it in MiB, per switch.
3. One line is appended to `flow.txt` for the victim: `3 12 3 200 1000000 2.0`, which means source host,
   destination host, priority, destination port, size in bytes and start time in seconds. The incast flows start
   at the same time.
4. `waf --run scratch/third` runs ns-3 on those inputs.

## 4. Read the output yourself

Two files in each run's folder matter:

- `fct.txt` has one line per completed flow: source IP, destination IP, source port, destination port, size, start
  time (ns), completion time (ns), and the time the flow would take alone (ns). Hosts are encoded in the IP: host 3
  is `0b000301`, host 12 is `0b000c01`.
- `pfc.txt` has one line per PFC frame *received*: time (ns from simulation start; flows start at 2 s), node, node
  type (0 host, 1 switch), interface, and type (1 PAUSE, 0 RESUME).

To see which frames host 3's edge switch received in the `pfc` run:

```
awk '$2 == 17 && $3 == 1' ../../results/pfc-victim/k4/pfc/pfc.txt
```

Interfaces 3 and 4 are edge 17's uplinks to aggregation switches 24 and 25 (interfaces 1 and 2 go to hosts 2 and 3).
They receive 24 and 22 PAUSE frames and are paused for about 229 µs and 427 µs. Host 3 itself receives only 3 PAUSE
frames, about 12 µs of pausing (`awk '$2 == 3 && $3 == 0' ...`). So the victim's packets wait inside edge 17, behind
uplinks that the aggregation switches have paused: the PAUSE has spread one hop up the tree.

## 5. Try next

Each of these overwrites `results/pfc-victim/k4/pfc/`.

- `make pfc SRC=1` sends the victim from host 1, which shares edge 16 with the congested host 0.
- `make pfc SRC=9`: host 9 is idle and shares edge 20 with an incast sender (host 8); its flow is unaffected.
- `make pfc ALGO=hpcc` swaps DCQCN for HPCC, a congestion control that keeps queues shorter.
- `make pfc N=4` changes the number of incast senders (hosts 1..N). Hosts 4–8 are in other pods and share no
  link with the victim's path, yet adding them slows it (the post's Figure 5, after the DCQCN paper's Figure 4):
  N=3: 149.9 µs, 4: 145.8, 5: 235.8, 6: 293.1, 7: 291.3, 8: 608.1.
- `make pfc PFC_BUF=4` changes the `pfc` run's switch buffer (MiB), and `QCN=0` switches DCQCN off. The post's
  Table 2 comes from `PFC_BUF=1, 2, 4, 8` with `QCN=1` and `QCN=0`:

  | Switch buffer | PAUSE frames, DCQCN on | DCQCN off |
  |---|---|---|
  | 1 MiB | 263 | 263 |
  | 2 MiB | 59 | 157 |
  | 4 MiB | 7 | 103 |
  | 8 MiB | 0 | 0 |
- `make all K=8 SRC=5 DST=100` runs the same experiment on a k=8 fat-tree (128 hosts), with results in
  `results/pfc-victim/k8/`. There, the PAUSE frames land on the sending host itself.

## Limits

This is one simulator with one buffer setting chosen to make PFC fire. Real switches differ in how they share buffer
and set the pause threshold. The mechanism is the same: a PAUSE stops one priority on a whole link, not one
destination.
