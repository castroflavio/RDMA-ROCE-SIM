# PFC victim-flow demo: does a PAUSE caused by one congested port stop a flow to an idle host?
# Run from this folder. Uses this repository's Docker image (ns-3 + the HPCC fork) and its experiment generator.
REPO = $(abspath $(CURDIR)/../..)
K    ?= 4
N    ?= 8
OUT  = $(REPO)/results/pfc-victim/k$(K)
RUN  = docker run --rm --platform linux/amd64 -v "$(REPO)":/work:ro -v "$(OUT)":/out -w /work rdma-sim

# The victim: one 1 MB flow from host SRC (default 3, also an incast sender) to host DST (default 12, idle).
SRC  ?= 3
DST  ?= 12
ALGO ?= dcqcn
PFC_BUF ?= 1
QCN ?= 1
# fct.txt names hosts by IP: host n is 0b.(n/256).(n%256).01, written in hex
VIP = $$(printf '0b%02x%02x01 0b%02x%02x01' $$(($(SRC) / 256)) $$(($(SRC) % 256)) $$(($(DST) / 256)) $$(($(DST) % 256)))

.PHONY: all setup alone big-buffer pfc other-priority report summary clean

all: alone big-buffer pfc other-priority

setup:           ## build the simulator image from this repository (~4 min on Apple Silicon, once)
	docker build --platform linux/amd64 -t rdma-sim "$(REPO)"

# $(call victim,name,buffer in MiB,victim priority,with incast 0/1)
define victim
	mkdir -p "$(OUT)"
	$(RUN) python3 -m experiments.run --sim-time 2.05 --no-packet-trace --out-base /out \
		--topo fat-tree --k $(K) --traffic incast --n-senders $(N) --message-size 1000000 --cc $(ALGO) \
		--name $(1) --dry-run >/dev/null
	sed -i.bak 's/^BUFFER_SIZE .*/BUFFER_SIZE $(2)/; s/^ENABLE_QCN .*/ENABLE_QCN $(QCN)/' "$(OUT)/$(1)/config.txt"
	cd "$(OUT)/$(1)" && { if [ $(4) = 1 ]; then head -1 flow.txt | awk '{print $$1 + 1}'; tail -n +2 flow.txt; \
		else echo 1; fi; echo "$(SRC) $(DST) $(3) 200 1000000 2.0"; } > flow.new && mv flow.new flow.txt
	$(RUN) sh -c 'cd /opt/hpcc/simulation && ./waf --run "scratch/third /out/$(1)/config.txt"' \
		> "$(OUT)/$(1)/run.log" 2>&1
	@$(MAKE) -s report NAME=$(1)
endef

alone:           ## the victim flow on an otherwise idle fabric
	$(call victim,alone,32,3,0)

big-buffer:      ## + an 8:1 incast (hosts 1-8) to host 0, 32 MiB switch buffers: PFC never fires
	$(call victim,big-buffer,32,3,1)

pfc:             ## + the 8:1 incast, PFC_BUF MiB buffers (default 1): PFC fires, victim on the incast's priority (3)
	$(call victim,pfc,$(PFC_BUF),3,1)

other-priority:  ## the same as pfc, with the victim on priority 1
	$(call victim,other-priority,1,1,1)

report:
	@n=$$(grep -c "^$(VIP) " "$(OUT)/$(NAME)/fct.txt"); \
		[ "$$n" = 1 ] || { echo "$(NAME): expected 1 victim line in fct.txt, found $$n" >&2; exit 1; }
	@grep "^$(VIP) " "$(OUT)/$(NAME)/fct.txt" | awk '{printf "%-15s victim %6.1f us", "$(NAME)", $$7/1000}'
	@awk '$$5 == 1 {p++} END {printf "   PAUSE frames received: %d\n", p}' "$(OUT)/$(NAME)/pfc.txt"

summary:         ## one line per finished run
	@for r in alone big-buffer pfc other-priority; do \
		[ -f "$(OUT)/$$r/fct.txt" ] && $(MAKE) -s report NAME=$$r; done; true

clean:
	rm -rf ../../results/pfc-victim
