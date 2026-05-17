import re
import json
from pathlib import Path


def extract_metric(pattern, text, cast=float, default=None):
    match = re.search(pattern, text)
    if match:
        return cast(match.group(1))
    return default


def parse_report(report_path):
    text = Path(report_path).read_text(errors="ignore")

    metrics = {
        "wns": extract_metric(r"wns\s+(-?\d+\.\d+)", text),
        "tns": extract_metric(r"tns\s+(-?\d+\.\d+)", text),
        "setup_violations": extract_metric(
            r"setup violation count\s+(\d+)",
            text,
            int,
            0,
        ),
    }

    return metrics


if __name__ == "__main__":
    report_file = "sample_report.txt"

    if Path(report_file).exists():
        result = parse_report(report_file)
        print(json.dumps(result, indent=2))
    else:
        print("sample_report.txt not found")
