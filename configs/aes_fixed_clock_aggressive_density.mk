export DESIGN_NICKNAME = aes
export DESIGN_NAME = aes_cipher_top
export PLATFORM    = nangate45

export VERILOG_FILES = $(sort $(wildcard $(DESIGN_HOME)/src/$(DESIGN_NICKNAME)/*.v))
export SDC_FILE = /mnt/d/MLCAD-timing-opt/configs/aes_fixed_clock_aggressive_density.sdc

export FLOORPLAN_DEF = $(DESIGN_HOME)/$(PLATFORM)/$(DESIGN_NICKNAME)/aes_ng45_fp.def

export PLACE_DENSITY_LB_ADDON = 0.25
export TNS_END_PERCENT = 100
# workaround for high congestion in post-grt repair
export SKIP_INCREMENTAL_REPAIR = 1

export SWAP_ARITH_OPERATORS = 1
export OPENROAD_HIERARCHICAL = 1


# MLCAD Agent Generated Config
# strategy: fixed_clock_aggressive_density
# source: deepseek_llm
# mode: fixed_clock_flow_search
# clock_period: 0.46
