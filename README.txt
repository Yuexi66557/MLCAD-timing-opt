Design-Aware Timing Optimization with OpenROAD and LLM

===============================================================================
1. Project Overview
===============================================================================

This project builds a lightweight design-aware timing optimization framework
based on OpenROAD, Python automation, and LLM-assisted strategy generation.

The framework automatically analyzes timing and physical-design QoR reports,
generates candidate optimization strategies, reruns OpenROAD flows, and selects
the best strategy according to timing and physical-design metrics.

The project is designed as a research-oriented prototype for exploring
AI-assisted EDA workflows, especially timing optimization and design-space
exploration for physical design.


===============================================================================
2. Project Goal
===============================================================================

Traditional physical-design flows often use fixed optimization settings across
different designs. However, different circuits exhibit different timing
bottlenecks, congestion patterns, routing characteristics, and optimization
sensitivities.

This project explores whether an agent-style optimization framework can:

- Extract design-specific QoR features automatically
- Analyze timing and routing behavior
- Generate candidate optimization strategies
- Modify OpenROAD flow parameters automatically
- Rerun the design flow iteratively
- Compare QoR metrics automatically
- Select the best strategy dynamically

The long-term goal is to study how LLMs and AI agents can assist timing
optimization in modern EDA flows.


===============================================================================
3. Overall Workflow
===============================================================================

OpenROAD Reports
        ↓
Feature Extractor
        ↓
LLM / Agent Policy
        ↓
Strategy Generator
        ↓
Config / SDC Modifier
        ↓
OpenROAD Rerun
        ↓
QoR Evaluation
        ↓
Best Strategy Selection

The current implementation supports both:
- heuristic/agent-style strategy generation
- real external LLM API integration through DeepSeek's
  OpenAI-compatible API


===============================================================================
4. Repository Structure
===============================================================================

mlcad26_agent/

├── agent/
│   ├── feature_extractor.py
│   ├── llm_policy_real.py
│   ├── search_strategies.py
│   ├── compare_results.py
│   ├── summarize_results.py
│   └── run_agent.py
│
├── configs/
│   ├── generated .mk files
│   └── generated .sdc files
│
├── results/
│   ├── QoR summaries
│   ├── strategy search results
│   ├── best strategy reports
│   └── experiment outputs
│
├── docs/
│   ├── experiment_summary.md
│   └── experiment_summary.txt
│
└── notes/
    └── learning notes and flow understanding


===============================================================================
5. OpenROAD Baseline Flow
===============================================================================

The framework is built on top of OpenROAD-flow-scripts.

The main physical-design stages include:

1. Synthesis
2. Floorplan
3. Global Placement
4. Detailed Placement
5. Timing Repair / Resizing
6. Clock Tree Synthesis (CTS)
7. Global Routing
8. Detailed Routing
9. Finish / QoR Reporting

The agent framework does not modify OpenROAD internal algorithms directly yet.
Instead, it modifies:
- SDC timing constraints
- floorplan/utilization parameters
- placement density parameters
- timing optimization settings

and then reruns the flow automatically.


===============================================================================
6. Implemented Features
===============================================================================

6.1 Automatic QoR Extraction

The framework automatically parses:
- WNS
- TNS
- setup violations
- hold violations
- wirelength
- via count
- DRC violations
- utilization
- power
- IR drop

from OpenROAD reports.


-------------------------------------------------------------------------------
6.2 Strategy Generation
-------------------------------------------------------------------------------

The framework supports two categories of strategies:

A) Fixed-Clock Flow Search

Keep the original clock target and modify:
- core utilization
- placement density
- timing repair aggressiveness

B) Constraint-Feasibility Search

Relax timing constraints gradually to discover:
- feasible clock targets
- cleaner timing closure regions


-------------------------------------------------------------------------------
6.3 Automatic OpenROAD Rerun
-------------------------------------------------------------------------------

For each strategy:
- generate modified SDC/config files
- rerun OpenROAD automatically
- collect QoR metrics
- compare results automatically


-------------------------------------------------------------------------------
6.4 DeepSeek LLM Integration
-------------------------------------------------------------------------------

The framework supports real external LLM calls through:
- DeepSeek OpenAI-compatible API

The LLM can generate:
- candidate timing optimization strategies
- flow parameter suggestions
- design-aware optimization policies


===============================================================================
7. Current Experimental Results
===============================================================================

Benchmark:
- Platform: nangate45
- Design: gcd
- Baseline clock target: 0.46 ns


-------------------------------------------------------------------------------
7.1 Best Fixed-Clock Result
-------------------------------------------------------------------------------

Clock target: 0.46 ns

WNS: -0.03 ns
TNS: -0.31 ns
Setup violations: 11

The current search space cannot fully close timing under the aggressive
0.46 ns target.


-------------------------------------------------------------------------------
7.2 Best Overall Result
-------------------------------------------------------------------------------

Strategy:
relax_clock_more

Clock target:
0.55 ns

Final QoR:
WNS = 0.0 ns
TNS = 0.0 ns
Setup violations = 0
Hold violations = 0
DRC violations = 0

This demonstrates the framework's ability to discover feasible timing regions
automatically.


===============================================================================
8. How to Run
===============================================================================

8.1 Activate Python Environment

source venv/bin/activate


-------------------------------------------------------------------------------
8.2 Extract Baseline Features
-------------------------------------------------------------------------------

python3 agent/feature_extractor.py


-------------------------------------------------------------------------------
8.3 Generate LLM Policies
-------------------------------------------------------------------------------

python3 agent/llm_policy_real.py


-------------------------------------------------------------------------------
8.4 Run Strategy Search
-------------------------------------------------------------------------------

python3 agent/search_strategies.py


-------------------------------------------------------------------------------
8.5 Generate Experiment Summary
-------------------------------------------------------------------------------

python3 agent/summarize_results.py


===============================================================================
9. DeepSeek API Setup
===============================================================================

Set API key:

export DEEPSEEK_API_KEY="your_key"

If using WSL + Clash proxy:

export http_proxy=http://<windows_ip>:7890
export https_proxy=http://<windows_ip>:7890


===============================================================================
10. Current Limitations
===============================================================================

- Current optimization mainly modifies config/SDC-level parameters
- OpenROAD internal C++ algorithm modification is not implemented yet
- Only gcd benchmark has been fully evaluated
- Fixed-clock timing closure at 0.46 ns remains difficult
- Current strategy search space is relatively small
- LLM prompting strategy is still simple


===============================================================================
11. Future Work
===============================================================================

- Test larger benchmarks such as aes and ibex
- Add congestion-aware optimization
- Explore routing-aware timing optimization
- Add timing-path-aware prompting
- Explore OpenROAD internal algorithm modification
- Study reinforcement-learning or multi-agent approaches
- Improve prompt engineering and policy generation


===============================================================================
12. Relation to MLCAD 2026 Contest
===============================================================================

This project aligns with the MLCAD 2026 contest direction because it explores:

- LLM-guided EDA optimization
- design-specific timing optimization
- automatic strategy generation
- AI-assisted physical-design exploration
- OpenROAD-based adaptive optimization workflows

The framework demonstrates a complete agent-style optimization loop built on
top of OpenROAD physical-design flows.