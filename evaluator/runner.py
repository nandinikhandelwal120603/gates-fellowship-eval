"""
runner.py
---------
Orchestrates the full evaluation pipeline:
  1. Load test cases
  2. For each: get endpoint response, run rule check, run LLM judge
  3. Aggregate results
  4. Save results.json
  5. Print a summary table to console
"""

import google.generativeai as genai
import os
import json
from datetime import datetime
from dotenv import load_dotenv

from evaluator.prompts import TEST_CASES
from evaluator.endpoint import get_endpoint_response
from evaluator.judge import rule_based_check, llm_judge

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import track
    RICH = True
    console = Console()
except ImportError:
    RICH = False


def run_evaluation():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")

    genai.configure(api_key=api_key)

    results = []
    total = len(TEST_CASES)

    print(f"\n{'='*60}")
    print(f"  Gates Fellowship — Maternal Health Evaluation")
    print(f"  Endpoint: gemini-2.5-flash | Judge: gemini-3-flash-preview")
    print(f"  Test cases: {total}")
    print(f"{'='*60}\n")

    iterator = track(TEST_CASES, description="Evaluating...") if RICH else TEST_CASES

    for i, case in enumerate(iterator):
        if not RICH:
            print(f"[{i+1}/{total}] {case['id']}: {case['category']} (risk: {case['risk_level']})")

        # Step 1: Get endpoint response
        endpoint_result = get_endpoint_response(case["prompt"])

        if endpoint_result["error"]:
            print(f"  ✗ Endpoint error: {endpoint_result['error']}")
            results.append({
                "case": case,
                "endpoint": endpoint_result,
                "rule_check": None,
                "llm_judgment": None,
                "error": endpoint_result["error"],
            })
            continue

        # Step 2: Rule-based check
        rule_result = rule_based_check(
            endpoint_result["text"],
            case["must_contain"],
            case["must_not_contain"],
        )

        # Step 3: LLM judge
        judgment = llm_judge(case["prompt"], endpoint_result["text"])

        result = {
            "case_id": case["id"],
            "category": case["category"],
            "risk_level": case["risk_level"],
            "prompt": case["prompt"],
            "response": endpoint_result["text"],
            "latency_seconds": endpoint_result["latency_seconds"],
            "rule_check": rule_result,
            "llm_judgment": judgment,
            "error": None,
        }
        results.append(result)

        # Quick console feedback
        if not RICH and not judgment.get("error"):
            score = judgment.get("composite_score", "?")
            rule_pass = "✓" if rule_result["passed"] else "✗"
            print(f"  Rule check: {rule_pass} | LLM composite: {score}/10")

    # ── Aggregate stats ───────────────────────────────────────────────────
    valid = [r for r in results if not r.get("error") and r.get("llm_judgment") and not r["llm_judgment"].get("error")]

    summary = {
        "run_timestamp": datetime.utcnow().isoformat() + "Z",
        "endpoint_model": "gemini-2.5-flash",
        "judge_model": "gemini-3-flash-preview",
        "total_cases": total,
        "successful_evaluations": len(valid),
        "rule_check_pass_rate": round(
            sum(1 for r in valid if r["rule_check"]["passed"]) / len(valid), 3
        ) if valid else 0,
        "avg_composite_score": round(
            sum(r["llm_judgment"]["composite_score"] for r in valid) / len(valid), 2
        ) if valid else 0,
        "avg_safety_score": round(
            sum(r["llm_judgment"].get("safety_score", 0) for r in valid) / len(valid), 2
        ) if valid else 0,
        "avg_latency_seconds": round(
            sum(r["latency_seconds"] for r in valid) / len(valid), 2
        ) if valid else 0,
        "by_category": {},
        "by_risk_level": {},
        "high_risk_cases_failed_rule_check": [],
    }

    # By category
    categories = set(r["category"] for r in valid)
    for cat in categories:
        cat_cases = [r for r in valid if r["category"] == cat]
        summary["by_category"][cat] = {
            "count": len(cat_cases),
            "avg_composite": round(
                sum(r["llm_judgment"]["composite_score"] for r in cat_cases) / len(cat_cases), 2
            ),
            "rule_pass_rate": round(
                sum(1 for r in cat_cases if r["rule_check"]["passed"]) / len(cat_cases), 3
            ),
        }

    # By risk level
    for level in ["high", "medium", "low"]:
        level_cases = [r for r in valid if r["risk_level"] == level]
        if level_cases:
            summary["by_risk_level"][level] = {
                "count": len(level_cases),
                "avg_composite": round(
                    sum(r["llm_judgment"]["composite_score"] for r in level_cases) / len(level_cases), 2
                ),
                "rule_pass_rate": round(
                    sum(1 for r in level_cases if r["rule_check"]["passed"]) / len(level_cases), 3
                ),
            }

    # Flag high-risk failures
    for r in valid:
        if r["risk_level"] == "high" and not r["rule_check"]["passed"]:
            summary["high_risk_cases_failed_rule_check"].append({
                "case_id": r["case_id"],
                "missing": r["rule_check"]["missing_required_keywords"],
                "forbidden_found": r["rule_check"]["found_forbidden_keywords"],
            })

    output = {
        "summary": summary,
        "results": results,
    }

    # ── Save results ──────────────────────────────────────────────────────
    os.makedirs("results", exist_ok=True)
    with open("results/results.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  EVALUATION COMPLETE")
    print(f"  Cases evaluated:     {summary['successful_evaluations']}/{total}")
    print(f"  Rule check pass:     {summary['rule_check_pass_rate']*100:.0f}%")
    print(f"  Avg composite score: {summary['avg_composite_score']}/10")
    print(f"  Avg safety score:    {summary['avg_safety_score']}/10")
    print(f"  Avg latency:         {summary['avg_latency_seconds']}s")
    print(f"{'='*60}")
    print(f"\n  Results saved to: results/results.json\n")

    return output


if __name__ == "__main__":
    run_evaluation()
