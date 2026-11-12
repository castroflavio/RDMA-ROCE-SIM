# Demo: a victim flow on two switches

Does a PFC PAUSE caused by one congested port also stop a flow to an idle host? This is the smallest network where
it does and where senders that share no link with the victim still slow it down: two switches. It accompanies the
post *WTH is a lossless network?* (version 2).

Switch A holds VS (host 2, sends only the 1 MB victim flow to VR) and S (host 3, an incast sender). Switch B holds
R (host 0, the incast receiver), VR (host 1, idle) and `EXTRA` more incast senders (hosts 4 and up, default 6).
Every link is 100 Gb/s, 1 µs. `two_switch.py` writes this topology into a dry-run's inputs, because the repository's
generators only build fat-trees and rail topologies.

## Run it

```
make setup   # build the simulator image, ~4 min once (needs Docker; x86 image runs under Rosetta on Apple Silicon)
make all     # four runs, ~2 min
```

```
alone           victim   89.2 us   PAUSE frames received: 0
big-buffer      victim  109.2 us   PAUSE frames received: 0
pfc             victim  342.4 us   PAUSE frames received: 137
other-priority  victim  104.3 us   PAUSE frames received: 123
```

| Run | Incast | Switch buffer | Victim's priority |
|---|---|---|---|
| `alone` | no | 32 MiB | 3 |
| `big-buffer` | yes | 32 MiB | 3 |
| `pfc` | yes | 1 MiB | 3 |
| `other-priority` | yes | 1 MiB | 1 |

Results go to `results/pfc-victim-2sw/<run>/` at the top of the repository: `fct.txt` (one line per flow; the
victim is `0b000201 0b000101`, completion time in ns in column 7) and `pfc.txt` (time ns, node, node type,
interface, type 1 = PAUSE / 0 = RESUME). Switch A is node `4 + EXTRA` (10 by default); its interface 3 is the link to
switch B. To see when it was paused: `awk '$2 == 10 && $4 == 3' ../../results/pfc-victim-2sw/pfc/pfc.txt`.

## Try next

- `make sweep` runs `pfc` with 0 to 8 extra senders (results in `sweep-<n>`). Victim times, µs:
  0: 172.2, 1: 143.9, 2: 125.5, 3: 116.9, 4: 208.5, 5: 248.6, 6: 342.4, 7: 436.0, 8: 242.2.
- `make pfc PFC_BUF=2` changes the `pfc` run's buffer (MiB); `QCN=0` switches DCQCN off.
- `make pfc ALGO=hpcc` swaps DCQCN for HPCC.

## Limits

One simulator, one buffer setting chosen to make PFC fire, one run per point. Real switches differ in how they
share buffer and set the pause threshold. The mechanism is the same: a PAUSE stops one priority on a whole link,
not one destination.
