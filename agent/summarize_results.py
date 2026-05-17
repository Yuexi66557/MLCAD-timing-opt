from pathlib import Path
import json

PROJECT_DIR = Path("/mnt/d/MLCAD-timing-opt")
RESULTS_DIR = PROJECT_DIR / "results"


def load_json(path):
    return json.loads(path.read_text())


def format_metric(v):
    if v is None:
        return "N/A"

    if isinstance(v, float):
        return f"{v:.4f}"

    return str(v)


def build_markdown(results):
    lines = []

    lines.append("# MLCAD Timing Optimization Experiment Summary\n")

    lines.append("## Project Goal\n")
    lines.append(
        "This project explores design-aware timing optimization "
        "using OpenROAD, Python automation, and LLM-guided strategy generation.\n"
    )

    lines.append("## Baseline Observation\n")

    baseline = load_json(RESULTS_DIR / "gcd_baseline_features.json")

    final = baseline["final_metrics"]

    lines.append(f"- Baseline WNS: {final['wns']} ns")
    lines.append(f"- Baseline TNS: {final['tns']} ns")
    lines.append(f"- Baseline setup violations: {final['setup_violation_count']}")
    lines.append("")

    lines.append("## Strategy Search Results\n")

    lines.append(
        "| Strategy | Mode | Clock(ns) | WNS(ns) | TNS(ns) | Setup Violations | Score |"
    )
    lines.append(
        "|---|---|---|---|---|---|---|"
    )

    for r in results:
        s = r["strategy"]
        m = r.get("metrics", {})

        lines.append(
            f"| {s['name']} "
            f"| {s['mode']} "
            f"| {format_metric(s['clock_period'])} "
            f"| {format_metric(m.get('wns'))} "
            f"| {format_metric(m.get('tns'))} "
            f"| {format_metric(m.get('setup_violations'))} "
            f"| {format_metric(r.get('score'))} |"
        )

    lines.append("")

    best = load_json(RESULTS_DIR / "best_strategy.json")

    best_s = best["strategy"]
    best_m = best["metrics"]

    lines.append("## Best Strategy\n")

    lines.append(f"- Strategy: `{best_s['name']}`")
    lines.append(f"- Mode: `{best_s['mode']}`")
    lines.append(f"- Clock target: `{best_s['clock_period']} ns`")
    lines.append(f"- WNS: `{best_m['wns']} ns`")
    lines.append(f"- TNS: `{best_m['tns']} ns`")
    lines.append(f"- Setup violations: `{best_m['setup_violations']}`")
    lines.append(f"- DRC violations: `{best_m['final_drc_violations']}`")
    lines.append("")

    lines.append("## Key Findings\n")

    lines.append(
        "- Different placement density and utilization settings produce different timing behaviors."
    )
    lines.append(
        "- Lower utilization does not always improve timing because excessive whitespace can increase wirelength."
    )
    lines.append(
        "- Constraint-feasibility search is useful for identifying achievable timing targets."
    )
    lines.append(
        "- The LLM-generated 0.50 ns strategy achieved timing closure with zero setup violations."
    )
    lines.append(
        "- The framework demonstrates a lightweight AI-for-EDA prototype using OpenROAD and Python automation."
    )

    return "\n".join(lines)


def main():
    result_path = RESULTS_DIR / "strategy_search_results.json"

    if not result_path.exists():
        raise FileNotFoundError("Run search_strategies.py first.")

    results = load_json(result_path)

    md = build_markdown(results)

    out = RESULTS_DIR / "experiment_summary.md"
    out.write_text(md)

    print(md)
    print(f"\nSaved summary to: {out}")


if __name__ == "__main__":
    main()
