# PFC victim flow on two switches: does a PAUSE caused by one congested port stop a flow to an idle host?
# Run from this folder. Uses this repository's Docker image (ns-3 + the HPCC fork); two_switch.py writes the topology.
REPO = $(abspath $(CURDIR)/../..)
OUT  = $(REPO)/results/pfc-victim-2sw
RUN  = docker run --rm --platform linux/amd64 -v "$(REPO)":/work:ro -v "$(OUT)":/out -w /work rdma-sim

EXTRA ?= 6
PFC_BUF ?= 1
QCN ?= 1
ALGO ?= dcqcn
# the victim is host 2 -> host 1; fct.txt names hosts by IP
VIP = 0b000201 0b000101

.PHONY: all setup alone big-buffer pfc other-priority sweep report summary clean

all: alone big-buffer pfc other-priority

setup:           ## build the simulator image from this repository (~4 min on Apple Silicon, once)
	docker build --platform linux/amd64 -t rdma-sim "$(REPO)"

# $(call run,name,two_switch.py options)
define run
	mkdir -p "$(OUT)"
	$(RUN) python3 -m experiments.run --sim-time 2.05 --no-packet-trace --out-base /out \
		--topo fat-tree --k 4 --traffic incast --n-senders 1 --message-size 1000000 --cc $(ALGO) \
		--name $(1) --dry-run >/dev/null
	python3 two_switch.py "$(OUT)/$(1)" $(2)
	$(RUN) sh -c 'cd /opt/hpcc/simulation && ./waf --run "scratch/third /out/$(1)/config.txt"' \
		> "$(OUT)/$(1)/run.log" 2>&1
	@$(MAKE) -s report NAME=$(1)
endef

alone:           ## the victim flow on an otherwise idle network
	$(call run,alone,--extra $(EXTRA) --buf 32 --alone)

big-buffer:      ## + the incast (S and EXTRA senders on switch B to R), 32 MiB buffers: PFC never fires
	$(call run,big-buffer,--extra $(EXTRA) --buf 32 --qcn $(QCN))

pfc:             ## + the incast, PFC_BUF MiB buffers (default 1): PFC fires, victim on the incast's priority (3)
	$(call run,pfc,--extra $(EXTRA) --buf $(PFC_BUF) --qcn $(QCN))

other-priority:  ## the same as pfc, with the victim on priority 1
	$(call run,other-priority,--extra $(EXTRA) --buf $(PFC_BUF) --qcn $(QCN) --prio 1)

sweep:           ## the pfc run with 0, 1, ... 8 extra senders (results in sweep-<n>)
	@for n in 0 1 2 3 4 5 6 7 8; do $(MAKE) -s pfc-one EXTRA=$$n; done

pfc-one:
	$(call run,sweep-$(EXTRA),--extra $(EXTRA) --buf $(PFC_BUF) --qcn $(QCN))

report:
	@n=$$(grep -c "^$(VIP) " "$(OUT)/$(NAME)/fct.txt"); \
		[ "$$n" = 1 ] || { echo "$(NAME): expected 1 victim line in fct.txt, found $$n" >&2; exit 1; }
	@grep "^$(VIP) " "$(OUT)/$(NAME)/fct.txt" | awk '{printf "%-15s victim %6.1f us", "$(NAME)", $$7/1000}'
	@awk '$$5 == 1 {p++} END {printf "   PAUSE frames received: %d\n", p}' "$(OUT)/$(NAME)/pfc.txt"

summary:         ## one line per finished run
	@for r in alone big-buffer pfc other-priority; do \
		[ -f "$(OUT)/$$r/fct.txt" ] && $(MAKE) -s report NAME=$$r; done; true

clean:
	rm -rf ../../results/pfc-victim-2sw
