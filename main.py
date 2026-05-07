"""
main.py — Entry point
Run: python main.py
"""
from evaluator.runner import run_evaluation
from report.generate import generate_report

if __name__ == "__main__":
    print("Step 1/2: Running evaluation...")
    output = run_evaluation()

    print("Step 2/2: Generating HTML report...")
    generate_report(output)

    print("\nDone. Open results/report.html in your browser.")
