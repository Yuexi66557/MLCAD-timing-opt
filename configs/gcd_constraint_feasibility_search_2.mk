export DESIGN_NAME = gcd
export PLATFORM    = nangate45

export VERILOG_FILES = $(DESIGN_HOME)/src/$(DESIGN_NAME)/gcd.v
export SDC_FILE = /mnt/d/MLCAD-timing-opt/configs/gcd_constraint_feasibility_search_2.sdc
export ABC_AREA      = 1

# Adders degrade GCD
export ADDER_MAP_FILE :=

export CORE_UTILIZATION = 55
export PLACE_DENSITY_LB_ADDON = 0.2
export TNS_END_PERCENT = 70
export SYNTH_REPEATABLE_BUILD ?= 1

# This needs a smaller pitch to accomodate a small block
export PDN_TCL ?= $(DESIGN_HOME)/$(PLATFORM)/$(DESIGN_NAME)/grid_strategy-M1-M4-M7.tcl


# MLCAD Agent Generated Config
# strategy: constraint_feasibility_search_2
# source: deepseek_llm
# mode: constraint_feasibility_search
# clock_period: 0.55
