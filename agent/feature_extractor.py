from pathlib import Path
import argparse
import json
import re

FLOW_DIR = Path.home() / "OpenROAD-flow-scripts" / "flow"
PROJECT_DIR = Path("/mnt/d/MLCAD-timing-opt")
RESULTS_DIR = PROJECT_DIR / "results"

DEFAULT_PLATFORM = "nangate45"
DEFAULT_DESIGN = "gcd"
DEFAULT_VARIANT = "base"


def read_text(path: Path) -> str:
    return path.read_text(errors="ignore") if path.exists() else ""


def extract_float(pattern: str, text: str):
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return float(m.group(1)) if m else None


def extract_int(pattern: str, text: str):
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return int(m.group(1)) if m else None


def parse_report(path: Path) -> dict:
    text = read_text(path)
    return {
        "report": str(path),
        "tns": extract_float(r"tns\s+max\s+(-?\d+(?:\.\d+)?)", text),
        "wns": extract_float(r"wns\s+max\s+(-?\d+(?:\.\d+)?)", text),
        "worst_slack": extract_float(r"worst\s+slack\s+max\s+(-?\d+(?:\.\d+)?)", text),
        "setup_violation_count": extract_int(r"setup\s+violation\s+count\s+(\d+)", text),
        "hold_violation_count": extract_int(r"hold\s+violation\s+count\s+(\d+)", text),
        "max_slew_violation_count": extract_int(r"max\s+slew\s+violation\s+count\s+(\d+)", text),
        "max_fanout_violation_count": extract_int(r"max\s+fanout\s+violation\s+count\s+(\d+)", text),
        "max_cap_violation_count": extract_int(r"max\s+cap\s+violation\s+count\s+(\d+)", text),
    }


def parse_runtime(log_dir: Path) -> dict:
    text = ""
    for log in log_dir.glob("*.log"):
        text += read_text(log) + "\n"

    elapsed = re.findall(r"Elapsed time:\s*(\d+):(\d+\.\d+|\d+)", text)
    peak = re.findall(r"Peak memory:\s*(\d+)KB", text)

    total_runtime_s = None
    if elapsed:
        total_runtime_s = sum(int(m) * 60 + float(s) for m, s in elapsed)

    return {
        "total_runtime_s": round(total_runtime_s, 2) if total_runtime_s else None,
        "peak_memory_mb": round(max(map(int, peak)) / 1024, 2) if peak else None,
    }


def parse_area_power(report_path: Path, log_dir: Path) -> dict:
    text = read_text(report_path)
    for p in log_dir.glob("*.log"):
        text += "\n" + read_text(p)

    return {
        "design_area_um2": extract_float(r"Design\s+area\s+(\d+(?:\.\d+)?)\s+um\^2", text),
        "utilization_percent": extract_float(r"Design\s+area\s+\d+(?:\.\d+)?\s+um\^2\s+(\d+(?:\.\d+)?)%\s+utilization", text),
        "total_power_w": extract_float(r"Total\s+power\s*:\s*([-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?)", text),
        "worst_ir_drop_v": extract_float(r"Worstcase\s+IR\s+drop:\s*([-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?)", text),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", default=DEFAULT_PLATFORM)
    parser.add_argument("--design", default=DEFAULT_DESIGN)
    parser.add_argument("--variant", default=DEFAULT_VARIANT)
    parser.add_argument("--tag", default="baseline")
    args = parser.parse_args()

    report_dir = FLOW_DIR / "reports" / args.platform / args.design / args.variant
    log_dir = FLOW_DIR / "logs" / args.platform / args.design / args.variant
    result_dir = FLOW_DIR / "results" / args.platform / args.design / args.variant

    final_report = report_dir / "6_finish.rpt"

    summary = {
        "platform": args.platform,
        "design": args.design,
        "variant": args.variant,
        "report_dir": str(report_dir),
        "log_dir": str(log_dir),
        "result_dir": str(result_dir),
        "final_gds_exists": (result_dir / "6_final.gds").exists(),
        "final_def_exists": (result_dir / "6_final.def").exists(),
        "final_metrics": parse_report(final_report),
        "area_power": parse_area_power(final_report, log_dir),
        "runtime": parse_runtime(log_dir),
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"{args.design}_{args.tag}_features.json"
    out.write_text(json.dumps(summary, indent=2))

    print("===== MLCAD Timing Feature Summary =====")
    print(json.dumps(summary, indent=2))
    print(f"\nSaved feature summary to: {out}")


if __name__ == "__main__":
    main()
