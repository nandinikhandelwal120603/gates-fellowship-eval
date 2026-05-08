import json
import os
import sys

# Add the project root to sys.path to import evaluator
sys.path.append(os.getcwd())

from evaluator.judge import rule_based_check
from evaluator.prompts import TEST_CASES

def update_rules():
    results_path = "results/results.json"
    if not os.path.exists(results_path):
        print("Results file not found.")
        return

    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Create a map for quick case lookup
    case_map = {c["id"]: c for c in TEST_CASES}

    updated_count = 0
    for r in data["results"]:
        case_id = r["case_id"]
        lang = r["language"]
        response = r["response"]
        
        case = case_map.get(case_id)
        if not case:
            continue
            
        # Re-run the rule check with the new multilingual logic
        new_rule_result = rule_based_check(
            response,
            case["must_contain"],
            case["must_not_contain"],
            language=lang
        )
        
        if r["rule_check"]["passed"] != new_rule_result["passed"]:
            updated_count += 1
            
        r["rule_check"] = new_rule_result

    # Update summary counts if necessary
    # (Actually runner.py aggregation logic should be re-run or we just update the specific fields)
    
    # Recalculate pass rates
    for lang_code, stats in data["summary"]["by_language"].items():
        lang_results = [r for r in data["results"] if r["language"] == lang_code]
        if lang_results:
            passed = sum(1 for r in lang_results if r["rule_check"]["passed"])
            stats["rule_pass_rate"] = round(passed / len(lang_results), 3)

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Updated rule checks for {updated_count} results.")

if __name__ == "__main__":
    update_rules()
