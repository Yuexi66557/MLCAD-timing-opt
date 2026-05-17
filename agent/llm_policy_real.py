from pathlib import Path
import json
import os
import re
from typing import Dict, Any

PROJECT_DIR = Path("/mnt/d/MLCAD-timing-opt")
RESULTS_DIR = PROJECT_DIR / "results"


def load_features() -> Dict[str, Any]:
    path = RESULTS_DIR / "gcd_baseline_features.json"
    if not path.exists():
        raise FileNotFoundError("Run feature_extractor.py --tag baseline first.")
    return json.loads(path.read_text())


def extract_json(text: str) -> Dict[str, Any]:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM response.")
    return json.loads(match.group(0))


def build_prompt(features: Dict[str, Any]) -> str:
    final = features["final_metrics"]
    area_power = features.get("area_power", {})

    return f"""
You are an ASIC physical design timing optimization agent.

Goal:
Generate OpenROAD timing optimization strategies for the given design.

Design:
- platform: {features["platform"]}
- design: {features["design"]}
- original clock target: 0.46 ns

Final baseline timing:
- WNS: {final.get("wns")} ns
- TNS: {final.get("tns")} ns
- setup violations: {final.get("setup_violation_count")}
- hold violations: {final.get("hold_violation_count")}
- max slew violations: {final.get("max_slew_violation_count")}
- max cap violations: {final.get("max_cap_violation_count")}

Physical QoR:
- design area: {area_power.get("design_area_um2")} um^2
- utilization: {area_power.get("utilization_percent")} %
- total power: {area_power.get("total_power_w")} W
- worst IR drop: {area_power.get("worst_ir_drop_v")} V

Task:
Generate 6 candidate strategies.

Important rules:
1. Include at least 3 fixed-clock strategies using clock_period = 0.46.
2. Include at most 3 constraint-feasibility strategies with relaxed clock.
3. Use realistic OpenROAD flow-level parameters.
4. Do not output prose.
5. Return ONLY valid JSON.

Allowed JSON format:
{{
  "strategies": [
    {{
      "name": "string",
      "mode": "fixed_clock_flow_search",
      "clock_period": 0.46,
      "core_utilization": 50,
      "place_density_lb_addon": 0.15,
      "tns_end_percent": 100,
      "rationale": "string"
    }}
  ]
}}

Allowed mode values:
- fixed_clock_flow_search
- constraint_feasibility_search

Allowed ranges:
- clock_period: 0.46 to 0.60
- core_utilization: 35 to 60
- place_density_lb_addon: 0.05 to 0.30
- tns_end_percent: 50 to 100
""".strip()


def call_deepseek(prompt: str) -> Dict[str, Any]:
    from openai import OpenAI

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise EnvironmentError("DEEPSEEK_API_KEY is not set.")

    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise EDA timing optimization agent. "
                    "Return only valid JSON. Do not include markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    text = response.choices[0].message.content
    return extract_json(text)


def fallback_policy() -> Dict[str, Any]:
    return {
        "strategies": [
            {
                "name": "fallback_fixed_low_util",
                "mode": "fixed_clock_flow_search",
                "clock_period": 0.46,
                "core_utilization": 40,
                "place_density_lb_addon": 0.10,
                "tns_end_percent": 100,
                "rationale": "Add whitespace under the original clock target.",
            },
            {
                "name": "fallback_fixed_medium_util",
                "mode": "fixed_clock_flow_search",
                "clock_period": 0.46,
                "core_utilization": 50,
                "place_density_lb_addon": 0.15,
                "tns_end_percent": 100,
                "rationale": "Moderate utilization with full TNS repair.",
            },
            {
                "name": "fallback_fixed_high_density",
                "mode": "fixed_clock_flow_search",
                "clock_period": 0.46,
                "core_utilization": 55,
                "place_density_lb_addon": 0.20,
                "tns_end_percent": 100,
                "rationale": "Baseline-like density for comparison.",
            },
            {
                "name": "fallback_relax_048",
                "mode": "constraint_feasibility_search",
                "clock_period": 0.48,
                "core_utilization": 50,
                "place_density_lb_addon": 0.15,
                "tns_end_percent": 100,
                "rationale": "Slightly relax clock to test feasibility.",
            },
            {
                "name": "fallback_relax_050",
                "mode": "constraint_feasibility_search",
                "clock_period": 0.50,
                "core_utilization": 55,
                "place_density_lb_addon": 0.15,
                "tns_end_percent": 100,
                "rationale": "Moderate clock relaxation.",
            },
            {
                "name": "fallback_relax_055",
                "mode": "constraint_feasibility_search",
                "clock_period": 0.55,
                "core_utilization": 40,
                "place_density_lb_addon": 0.25,
                "tns_end_percent": 70,
                "rationale": "Larger relaxation to guarantee timing closure.",
            },
        ]
    }


def validate_policy(policy: Dict[str, Any], source: str) -> Dict[str, Any]:
    valid_modes = {"fixed_clock_flow_search", "constraint_feasibility_search"}

    if "strategies" not in policy or not isinstance(policy["strategies"], list):
        raise ValueError("Policy must contain a strategies list.")

    cleaned = []

    for idx, s in enumerate(policy["strategies"]):
        mode = s.get("mode", "fixed_clock_flow_search")
        if mode not in valid_modes:
            mode = "fixed_clock_flow_search"

        clock = float(s.get("clock_period", 0.46))
        clock = max(0.46, min(clock, 0.60))

        util = int(s.get("core_utilization", 55))
        util = max(35, min(util, 60))

        addon = float(s.get("place_density_lb_addon", 0.20))
        addon = max(0.05, min(addon, 0.30))

        tns_end = int(s.get("tns_end_percent", 100))
        tns_end = max(50, min(tns_end, 100))

        cleaned.append(
            {
                "name": str(s.get("name", f"strategy_{idx}")),
                "mode": mode,
                "clock_period": clock,
                "core_utilization": util,
                "place_density_lb_addon": addon,
                "tns_end_percent": tns_end,
                "description": str(s.get("rationale", "")),
                "source": source,
            }
        )

    return {"strategies": cleaned, "policy_source": source}


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    features = load_features()
    prompt = build_prompt(features)
    prompt_path = RESULTS_DIR / "deepseek_llm_prompt.txt"
    prompt_path.write_text(prompt)

    try:
        raw_policy = call_deepseek(prompt)
        source = "deepseek_llm"
    except Exception as e:
        print(f"[WARNING] DeepSeek call failed: {e}")
        print("[INFO] Using fallback policy.")
        raw_policy = fallback_policy()
        source = "fallback_policy"

    policy = validate_policy(raw_policy, source)

    out_path = RESULTS_DIR / "openai_llm_policy.json"
    out_path.write_text(json.dumps(policy, indent=2))

    print("===== LLM Policy =====")
    print(json.dumps(policy, indent=2))
    print(f"\nSaved prompt to: {prompt_path}")
    print(f"Saved policy to: {out_path}")


if __name__ == "__main__":
    main()
