"""
runner.py
---------
Orchestrates the full evaluation pipeline:
  - Multilingual testing (English, Hindi, Urdu, Tamil)
  - Dual judge (Gemini 3 Flash Preview + Sarvam-M)
  - Judge agreement analysis

CRITICAL DESIGN NOTE on multilingual evaluation:
The translated prompt is what actually gets sent to Gemini 2.5 Flash.
This tests whether the health AI can handle native-language queries —
which is realistic for India deployment where users ask in their
mother tongue.

The endpoint always responds in English regardless of input language.
Rule checks and judge evaluation are applied to the English response.
This is a documented limitation: keyword sets should ideally be
translated per language in a production system.

Run modes:
  python main.py                  → English only (~3 mins)
  python main.py --multilingual   → English + Hindi + Urdu + Tamil (~12 mins)
"""

import google.generativeai as genai
import os
import json
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

from evaluator.prompts import TEST_CASES
from evaluator.endpoint import get_endpoint_response
from evaluator.judge import rule_based_check, llm_judge
from evaluator.sarvam_judge import sarvam_judge, compute_judge_agreement
from evaluator.translate import translate_batch

try:
    from rich.progress import track
    from rich.console import Console
    RICH = True
    console = Console()
except ImportError:
    RICH = False

MULTILINGUAL = "--multilingual" in sys.argv
LANGUAGES_TO_TEST = ["english", "hindi", "urdu", "tamil"] if MULTILINGUAL else ["english"]


def evaluate_single_case(case: dict, prompt_text: str, language: str) -> dict:
    """
    Run full evaluation for one test case in one language.

    prompt_text is the TRANSLATED version of the prompt —
    this is what actually gets sent to the endpoint.
    This is the core of the multilingual evaluation.
    """
    print(f"\n    Prompt sent ({language}): {prompt_text[:80]}{'...' if len(prompt_text) > 80 else ''}")

    # Step 1: Send TRANSLATED prompt to endpoint
    endpoint_result = get_endpoint_response(prompt_text)

    if endpoint_result["error"]:
        return {
            "case_id": case["id"],
            "category": case["category"],
            "risk_level": case["risk_level"],
            "language": language,
            "prompt_original_english": case["prompt"],
            "prompt_sent_to_endpoint": prompt_text,
            "response": "",
            "error": endpoint_result["error"],
        }

    response_text = endpoint_result["text"]

    # Step 2: Rule-based check on English response
    # Note: keyword lists are in English. The endpoint responds in English
    # even when queried in Hindi/Urdu/Tamil, so this is valid.
    # Limitation: we cannot catch cases where the model switches to
    # the input language in its response.
    rule_result = rule_based_check(
        response_text,
        case["must_contain"],
        case["must_not_contain"],
    )

    # Step 3: Gemini judge — evaluates English response
    gemini_result = llm_judge(prompt_text, response_text)

    # Step 4: Sarvam judge — independent cross-family validation
    sarvam_result = sarvam_judge(prompt_text, response_text)

    # Step 5: Judge agreement analysis
    agreement = None
    if not gemini_result.get("error") and not sarvam_result.get("error"):
        agreement = compute_judge_agreement(
            gemini_result.get("composite_score", 0),
            sarvam_result.get("composite_score", 0),
        )

    return {
        "case_id": case["id"],
        "category": case["category"],
        "risk_level": case["risk_level"],
        "language": language,
        "prompt_original_english": case["prompt"],
        "prompt_sent_to_endpoint": prompt_text,   # ← translated version
        "response": response_text,
        "latency_seconds": endpoint_result["latency_seconds"],
        "rule_check": rule_result,
        "gemini_judgment": gemini_result,
        "sarvam_judgment": sarvam_result,
        "judge_agreement": agreement,
        "error": None,
    }


def safe_avg(items, key_fn):
    vals = [key_fn(i) for i in items if key_fn(i) is not None]
    return round(sum(vals) / len(vals), 2) if vals else 0


def run_evaluation():
    load_dotenv()

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY not found in .env")
    genai.configure(api_key=gemini_key)

    sarvam_key = os.getenv("SARVAM_API_KEY")
    if not sarvam_key:
        print("  WARNING: SARVAM_API_KEY not set. Sarvam judge + translation will be skipped.")

    total = len(TEST_CASES) * len(LANGUAGES_TO_TEST)

    print(f"\n{'='*65}")
    print(f"  Gates Fellowship — Maternal Health AI Evaluation v2")
    print(f"  Endpoint : gemini-2.5-flash")
    print(f"  Judge 1  : gemini-3-flash-preview  (primary)")
    print(f"  Judge 2  : sarvam-m                (cross-family, India-native)")
    print(f"  Languages: {', '.join(LANGUAGES_TO_TEST)}")
    print(f"  Total    : {len(TEST_CASES)} cases × {len(LANGUAGES_TO_TEST)} languages = {total} evaluations")
    print(f"{'='*65}\n")

    # ── Step 1: Translate all prompts ────────────────────────────────────
    # translated_prompts maps: {language: {english_prompt: translated_prompt}}
    translated_prompts = {
        "english": {c["prompt"]: c["prompt"] for c in TEST_CASES}
    }

    non_english = [l for l in LANGUAGES_TO_TEST if l != "english"]
    if non_english and sarvam_key:
        print("Step 1/2: Translating prompts via Sarvam Mayura v1...")
        raw_translations = translate_batch(
            [c["prompt"] for c in TEST_CASES],
            non_english,
        )
        for lang in non_english:
            translated_prompts[lang] = {
                item["original"]: item["translated"]
                for item in raw_translations[lang]
            }
            # Show a sample so we can verify translation happened
            sample = raw_translations[lang][0]
            print(f"\n  Sample {lang.capitalize()} translation:")
            print(f"  EN: {sample['original'][:70]}...")
            print(f"  {lang.upper()[:2]}: {sample['translated'][:70]}...")
    elif non_english:
        print("  Skipping translation — no SARVAM_API_KEY. Running English only.")
        LANGUAGES_TO_TEST.clear()
        LANGUAGES_TO_TEST.append("english")

    # ── Step 2: Evaluation loop ─────────────────────────────────────────
    print(f"\nStep 2/2: Running evaluations...")
    all_results = []
    count = 0

    for language in LANGUAGES_TO_TEST:
        print(f"\n{'─'*65}")
        print(f"  Language: {language.upper()}")
        print(f"{'─'*65}")

        iterator = track(TEST_CASES, description=f"  [{language}]") if RICH else TEST_CASES

        for case in iterator:
            count += 1
            # This is the key line — get the translated prompt
            prompt_text = translated_prompts.get(language, {}).get(
                case["prompt"], case["prompt"]
            )

            if not RICH:
                print(f"\n  [{count}/{total}] {case['id']} | {language} | risk:{case['risk_level']}")

            result = evaluate_single_case(case, prompt_text, language)
            all_results.append(result)
            time.sleep(1)  # rate limit buffer

    # ── Aggregation ──────────────────────────────────────────────────────
    valid = [
        r for r in all_results
        if not r.get("error")
        and r.get("gemini_judgment")
        and not r["gemini_judgment"].get("error")
    ]
    english_only = [r for r in valid if r["language"] == "english"]
    agreement_cases = [r for r in valid if r.get("judge_agreement")]
    conflicting = [r for r in agreement_cases if r["judge_agreement"]["flag_for_review"]]

    summary = {
        "run_timestamp": datetime.utcnow().isoformat() + "Z",
        "endpoint_model": "gemini-2.5-flash",
        "judge_1": "gemini-3-flash-preview",
        "judge_2": "sarvam-m",
        "languages_tested": LANGUAGES_TO_TEST,
        "total_evaluations": total,
        "successful_evaluations": len(valid),

        # English baseline
        "english_rule_check_pass_rate": round(
            sum(1 for r in english_only if r["rule_check"]["passed"]) / len(english_only), 3
        ) if english_only else 0,
        "english_avg_gemini_score": safe_avg(
            english_only, lambda r: r["gemini_judgment"].get("composite_score")
        ),
        "english_avg_sarvam_score": safe_avg(
            [r for r in english_only if not r.get("sarvam_judgment", {}).get("error")],
            lambda r: r["sarvam_judgment"].get("composite_score")
        ),

        # Judge agreement
        "judge_agreement_rate": round(
            sum(1 for r in agreement_cases if r["judge_agreement"]["agreed"]) / len(agreement_cases), 3
        ) if agreement_cases else 0,
        "cases_flagged_for_review": len(conflicting),
        "conflicting_cases": [
            {
                "case_id": r["case_id"],
                "language": r["language"],
                "gemini": r["judge_agreement"]["gemini_composite"],
                "sarvam": r["judge_agreement"]["sarvam_composite"],
                "diff": r["judge_agreement"]["difference"],
            }
            for r in conflicting
        ],

        "by_language": {},
        "by_category": {},
        "by_risk_level": {},
    }

    # By language
    for lang in LANGUAGES_TO_TEST:
        lc = [r for r in valid if r["language"] == lang]
        sv = [r for r in lc if not r.get("sarvam_judgment", {}).get("error")]
        if lc:
            summary["by_language"][lang] = {
                "count": len(lc),
                "rule_pass_rate": round(
                    sum(1 for r in lc if r["rule_check"]["passed"]) / len(lc), 3
                ),
                "avg_gemini_score": safe_avg(
                    lc, lambda r: r["gemini_judgment"].get("composite_score")
                ),
                "avg_sarvam_score": safe_avg(
                    sv, lambda r: r["sarvam_judgment"].get("composite_score")
                ) if sv else None,
            }

    # By category (English baseline for clean comparison)
    for cat in set(r["category"] for r in english_only):
        cc = [r for r in english_only if r["category"] == cat]
        summary["by_category"][cat] = {
            "count": len(cc),
            "avg_gemini_composite": safe_avg(
                cc, lambda r: r["gemini_judgment"].get("composite_score")
            ),
            "rule_pass_rate": round(
                sum(1 for r in cc if r["rule_check"]["passed"]) / len(cc), 3
            ),
        }

    # By risk level (English baseline)
    for level in ["high", "medium", "low"]:
        lc = [r for r in english_only if r["risk_level"] == level]
        if lc:
            summary["by_risk_level"][level] = {
                "count": len(lc),
                "avg_gemini_composite": safe_avg(
                    lc, lambda r: r["gemini_judgment"].get("composite_score")
                ),
                "rule_pass_rate": round(
                    sum(1 for r in lc if r["rule_check"]["passed"]) / len(lc), 3
                ),
            }

    output = {"summary": summary, "results": all_results}

    os.makedirs("results", exist_ok=True)
    with open("results/results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # ── Final summary ─────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print(f"  EVALUATION COMPLETE")
    print(f"  Successful:         {len(valid)}/{total}")
    print(f"  Rule pass (EN):     {summary['english_rule_check_pass_rate']*100:.0f}%")
    print(f"  Gemini avg (EN):    {summary['english_avg_gemini_score']}/10")
    print(f"  Sarvam avg (EN):    {summary['english_avg_sarvam_score']}/10")
    print(f"  Judge agreement:    {summary['judge_agreement_rate']*100:.0f}%")
    print(f"  Flagged for review: {summary['cases_flagged_for_review']}")
    if summary["by_language"]:
        print(f"\n  By language:")
        for lang, stats in summary["by_language"].items():
            print(f"    {lang:<10} rule:{stats['rule_pass_rate']*100:.0f}%  gemini:{stats['avg_gemini_score']}/10  sarvam:{stats.get('avg_sarvam_score','—')}/10")
    print(f"{'='*65}")
    print(f"\n  Results saved to: results/results.json\n")

    return output


if __name__ == "__main__":
    run_evaluation()