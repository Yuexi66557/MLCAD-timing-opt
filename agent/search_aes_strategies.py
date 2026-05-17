from pathlib import Path
import json
import re
import subprocess
import shutil

PROJECT_DIR = Path("/mnt/d/MLCAD-timing-opt")
RESULTS_DIR = PROJECT_DIR / "results"
CONFIG_DIR = PROJECT_DIR / "configs"

FLOW_DIR = Path.home() / "OpenROAD-flow-scripts" / "flow"
PLATFORM = "nangate45"
DESIGN = "aes"
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
    return json.loads((RESULTS_DIR / "aes_policy.json").read_text())


def generate_sdc(strategy):
    text = BASE_SDC.read_text()

    text = re.sub(
        r"set\s+clk_period\s+[-+]?\d+(?:\.\d+)?",
        f"set clk_period {strategy['clock_period']}",
        text,
    )

    text += f"""

# MLCAD AES Agent Generated SDC
# strategy: {strategy['name']}
# clock_period: {strategy['clock_period']}
"""

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    out = CONFIG_DIR / f"{strategy['name']}.sdc"
    out.write_text(text)
    return out


def replace_or_append(text, key, value):
    pattern = rf"^(?:export\s+)?{key}\s*(?::=|\?=|=)\s*.*$"
    repl = f"export {key} = {value}"

    if re.search(pattern, text, flags=re.MULTILINE):
        return re.sub(pattern, repl, text, flags=re.MULTILINE)

    return text.rstrip() + "\n" + repl + "\n"


def generate_config(strategy, sdc_path):
    text = BASE_CONFIG.read_text()

    # AES uses FLOORPLAN_DEF, so DO NOT add CORE_UTILIZATION.
    text = replace_or_append(text, "SDC_FILE", str(sdc_path))
    text = replace_or_append(text, "PLACE_DENSITY_LB_ADDON", str(strategy["place_density_lb_addon"]))
    text = replace_or_append(text, "TNS_END_PERCENT", str(strategy["tns_end_percent"]))

    text += f"""

# MLCAD AES Agent Generated Config
# strategy: {strategy['name']}
# mode: {strategy['mode']}
# clock_period: {strategy['clock_period']}
"""

    out = CONFIG_DIR / f"{strategy['name']}.mk"
    out.write_text(text)
    return out


def run_flow(config_path):
    subprocess.run("make clean_all", cwd=FLOW_DIR, shell=True, check=True)
    subprocess.run(f"make DESIGN_CONFIG={config_path}", cwd=FLOW_DIR, shell=True, check=True)


def parse_final_report():
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


def parse_area_power():
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


def parse_runtime():
    text = ""
    for p in LOG_DIR.glob("*.log"):
        text += "\n" + read_text(p)

    elapsed = re.findall(r"Elapsed time:\s*(\d+):(\d+(?:\.\d+)?)", text)
    peak = re.findall(r"Peak memory:\s*(\d+)KB", text)

    total_runtime_s = None
    if elapsed:
        total_runtime_s = sum(int(m) * 60 + float(s) for m, s in elapsed)

    return {
        "total_runtime_s": round(total_runtime_s, 2) if total_runtime_s else None,
        "peak_memory_mb": round(max(map(int, peak)) / 1024, 2) if peak else None,
    }


def parse_route_log():
    text = read_text(ROUTE_LOG)

    wirelengths = re.findall(r"Total wire length =\s+(\d+)\s+um", text)
    vias = re.findall(r"Total number of vias =\s+(\d+)", text)
    violations = re.findall(r"Number of violations =\s+(\d+)", text)

    return {
        "final_wirelength_um": int(wirelengths[-1]) if wirelengths else None,
        "final_vias": int(vias[-1]) if vias else None,
        "final_drc_violations": int(violations[-1]) if violations else None,
    }


def copy_artifacts(strategy_name):
    dest = RESULTS_DIR / "aes_artifacts" / strategy_name
    dest.mkdir(parents=True, exist_ok=True)

    for src in [
        FINAL_REPORT,
        LOG_DIR / "6_report.log",
        LOG_DIR / "5_2_route.log",
        REPORT_DIR / "final_placement.webp",
        REPORT_DIR / "final_routing.webp",
        REPORT_DIR / "final_congestion.webp",
        REPORT_DIR / "final_worst_path.webp",
    ]:
        if src.exists():
            shutil.copy(src, dest / src.name)


def score(metrics, strategy):
    if metrics.get("wns") is None:
        return -1e9

    wns = metrics.get("wns") or 0
    tns = metrics.get("tns") or 0
    setup = metrics.get("setup_violations") or 0
    drc = metrics.get("final_drc_violations") or 0
    wire = metrics.get("final_wirelength_um") or 0
    power = metrics.get("total_power_w") or 0

    clock_penalty = 5 * (strategy["clock_period"] - 0.82)

    return (
        1000 * wns
        + 10 * tns
        - 3 * setup
        - 5 * drc
        - 0.0005 * wire
        - 2 * power
        - clock_penalty
    )


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    policy = load_policy()
    all_results = []

    for strategy in policy["strategies"]:
        print("\n" + "=" * 80)
        print(f"Running AES strategy: {strategy['name']}")

        sdc_path = generate_sdc(strategy)
        config_path = generate_config(strategy, sdc_path)

        try:
            run_flow(config_path)

            metrics = {}
            metrics.update(parse_final_report())
            metrics.update(parse_area_power())
            metrics.update(parse_runtime())
            metrics.update(parse_route_log())

            result = {
                "strategy": strategy,
                "generated_sdc": str(sdc_path),
                "config_path": str(config_path),
                "metrics": metrics,
            }
            result["score"] = score(metrics, strategy)

            copy_artifacts(strategy["name"])

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

    out = RESULTS_DIR / "aes_strategy_search_results.json"
    best_out = RESULTS_DIR / "aes_best_strategy.json"

    out.write_text(json.dumps(all_results, indent=2))
    best_out.write_text(json.dumps(best, indent=2))

    print("\n" + "=" * 80)
    print("Best AES Strategy")
    print(json.dumps(best, indent=2))
    print(f"\nSaved all AES results to: {out}")
    print(f"Saved best AES strategy to: {best_out}")


if __name__ == "__main__":
    main()
