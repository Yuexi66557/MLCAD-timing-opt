from pathlib import Path
import json
import subprocess
import re

PROJECT_DIR = Path("/mnt/d/MLCAD-timing-opt")
RESULTS_DIR = PROJECT_DIR / "results"
CONFIG_DIR = PROJECT_DIR / "configs"

FLOW_DIR = Path.home() / "OpenROAD-flow-scripts" / "flow"

PLATFORM = "nangate45"
DESIGN = "gcd"
VARIANT = "base"

BASE_CONFIG = FLOW_DIR / "designs" / PLATFORM / DESIGN / "config.mk"
BASE_SDC = FLOW_DIR / "designs" / PLATFORM / DESIGN / "constraint.sdc"

REPORT_DIR = FLOW_DIR / "reports" / PLATFORM / DESIGN / VARIANT
LOG_DIR = FLOW_DIR / "logs" / PLATFORM / DESIGN / VARIANT
RESULT_DIR = FLOW_DIR / "results" / PLATFORM / DESIGN / VARIANT
FINAL_REPORT = REPORT_DIR / "6_finish.rpt"
ROUTE_LOG = LOG_DIR / "5_2_route.log"


def read_text(path: Path) -> str:
    return path.read_text(errors="ignore") if path.exists() else ""


def extract_float(pattern: str, text: str):
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return float(m.group(1)) if m else None


def extract_int(pattern: str, text: str):
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return int(m.group(1)) if m else None


def load_policy():
    return json.loads((RESULTS_DIR / "openai_llm_policy.json").read_text())


def generate_sdc(strategy: dict) -> Path:
    text = BASE_SDC.read_text()
    text = re.sub(
        r"^set\s+clk_period\s+[-+]?\d+(?:\.\d+)?",
        f"set clk_period {strategy['clock_period']}",
        text,
        flags=re.MULTILINE,
    )

    text += f"""

# MLCAD Agent Generated SDC
# strategy: {strategy['name']}
# source: {strategy.get('source')}
# mode: {strategy.get('mode')}
"""

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    out = CONFIG_DIR / f"gcd_{strategy['name']}.sdc"
    out.write_text(text)
    return out


def replace_or_append(text: str, key: str, value: str) -> str:
    pattern = rf"^(?:export\s+)?{key}\s*(?::=|\?=|=)\s*.*$"
    repl = f"export {key} = {value}"

    if re.search(pattern, text, flags=re.MULTILINE):
        return re.sub(pattern, repl, text, flags=re.MULTILINE)

    return text.rstrip() + "\n" + repl + "\n"


def generate_config(strategy: dict, sdc_path: Path) -> Path:
    text = BASE_CONFIG.read_text()

    text = replace_or_append(text, "SDC_FILE", str(sdc_path))
    text = replace_or_append(text, "CORE_UTILIZATION", str(strategy["core_utilization"]))
    text = replace_or_append(text, "PLACE_DENSITY_LB_ADDON", str(strategy["place_density_lb_addon"]))
    text = replace_or_append(text, "TNS_END_PERCENT", str(strategy["tns_end_percent"]))

    text += f"""

# MLCAD Agent Generated Config
# strategy: {strategy['name']}
# source: {strategy.get('source')}
# mode: {strategy.get('mode')}
# clock_period: {strategy.get('clock_period')}
"""

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    out = CONFIG_DIR / f"gcd_{strategy['name']}.mk"
    out.write_text(text)
    return out


def run_flow(config_path: Path):
    subprocess.run(
        "make clean_all",
        cwd=FLOW_DIR,
        shell=True,
        check=True,
    )

    subprocess.run(
        f"make DESIGN_CONFIG={config_path}",
        cwd=FLOW_DIR,
        shell=True,
        check=True,
    )


def parse_final_report() -> dict:
    text = read_text(FINAL_REPORT)

    return {
        "wns": extract_float(r"wns\s+max\s+(-?\d+(?:\.\d+)?)", text),
        "tns": extract_float(r"tns\s+max\s+(-?\d+(?:\.\d+)?)", text),
        "worst_slack": extract_float(r"worst\s+slack\s+max\s+(-?\d+(?:\.\d+)?)", text),
        "setup_violations": extract_int(r"setup\s+violation\s+count\s+(\d+)", text),
        "hold_violations": extract_int(r"hold\s+violation\s+count\s+(\d+)", text),
        "max_slew_violations": extract_int(r"max\s+slew\s+violation\s+count\s+(\d+)", text),
        "max_fanout_violations": extract_int(r"max\s+fanout\s+violation\s+count\s+(\d+)", text),
        "max_cap_violations": extract_int(r"max\s+cap\s+violation\s+count\s+(\d+)", text),
    }


def parse_area_power() -> dict:
    text = read_text(FINAL_REPORT)
    for p in LOG_DIR.glob("*.log"):
        text += "\n" + read_text(p)

    return {
        "design_area_um2": extract_float(r"Design\s+area\s+(\d+(?:\.\d+)?)\s+um\^2", text),
        "utilization_percent": extract_float(
            r"Design\s+area\s+\d+(?:\.\d+)?\s+um\^2\s+(\d+(?:\.\d+)?)%\s+utilization",
            text,
        ),
        "total_power_w": extract_float(r"Total\s+power\s*:\s*([-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?)", text),
        "worst_ir_drop_v": extract_float(r"Worstcase\s+IR\s+drop:\s*([-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?)", text),
    }


def parse_route_log() -> dict:
    text = read_text(ROUTE_LOG)

    wirelengths = re.findall(r"Total wire length =\s+(\d+)\s+um", text)
    vias = re.findall(r"Total number of vias =\s+(\d+)", text)
    violations = re.findall(r"Number of violations =\s+(\d+)", text)

    return {
        "final_wirelength_um": int(wirelengths[-1]) if wirelengths else None,
        "final_vias": int(vias[-1]) if vias else None,
        "final_drc_violations": int(violations[-1]) if violations else None,
    }


def score(metrics: dict, strategy: dict) -> float:
    wns = metrics.get("wns")
    tns = metrics.get("tns")
    setup = metrics.get("setup_violations")
    drc = metrics.get("final_drc_violations")
    wire = metrics.get("final_wirelength_um")
    vias = metrics.get("final_vias")

    if wns is None:
        return -1e9

    tns = tns if tns is not None else -999
    setup = setup if setup is not None else 999
    drc = drc if drc is not None else 999
    wire = wire if wire is not None else 999999
    vias = vias if vias is not None else 999999

    clock_penalty = 0
    if strategy.get("mode") == "constraint_feasibility_search":
        clock_penalty = 20 * (strategy["clock_period"] - 0.46)

    return (
        1000 * wns
        + 10 * tns
        - 3 * setup
        - 5 * drc
        - 0.001 * wire
        - 0.0005 * vias
        - clock_penalty
    )


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    policy = load_policy()
    all_results = []

    for strategy in policy["strategies"]:
        print("\n" + "=" * 80)
        print(f"Running strategy: {strategy['name']}")

        sdc_path = generate_sdc(strategy)
        config_path = generate_config(strategy, sdc_path)

        try:
            run_flow(config_path)

            metrics = {}
            metrics.update(parse_final_report())
            metrics.update(parse_area_power())
            metrics.update(parse_route_log())

            result = {
                "strategy": strategy,
                "generated_sdc": str(sdc_path),
                "config_path": str(config_path),
                "metrics": metrics,
            }
            result["score"] = score(metrics, strategy)

        except subprocess.CalledProcessError as e:
            result = {
                "strategy": strategy,
                "generated_sdc": str(sdc_path),
                "config_path": str(config_path),
                "error": str(e),
                "score": -1e9,
            }

        all_results.append(result)
        print(json.dumps(result, indent=2))

    valid = [r for r in all_results if "metrics" in r]
    best = max(valid, key=lambda r: r["score"]) if valid else all_results[0]

    fixed = [r for r in valid if r["strategy"].get("mode") == "fixed_clock_flow_search"]
    best_fixed = max(fixed, key=lambda r: r["score"]) if fixed else None

    (RESULTS_DIR / "strategy_search_results.json").write_text(json.dumps(all_results, indent=2))
    (RESULTS_DIR / "best_strategy.json").write_text(json.dumps(best, indent=2))
    if best_fixed:
        (RESULTS_DIR / "best_fixed_clock_strategy.json").write_text(json.dumps(best_fixed, indent=2))

    print("\n" + "=" * 80)
    print("Best Overall Strategy")
    print(json.dumps(best, indent=2))

    if best_fixed:
        print("\n" + "=" * 80)
        print("Best Fixed-Clock Strategy")
        print(json.dumps(best_fixed, indent=2))


if __name__ == "__main__":
    main()
