# Maternal Health AI Evaluation
### Gates Foundation AI Fellowship — India 2026 | Technical Assignment

**Path chosen:** Option B — Critique & Rebuild  
**Live report:** https://nandinikhandelwal120603.github.io/gates-fellowship-eval/  
**Endpoint model:** gemini-2.5-flash | **Judges:** gemini-3-flash-preview (primary) & sarvam-m (cross-family validation)
**Languages:** English, Hindi, Urdu, Tamil

## What This Is
A lightweight AI evaluation harness that sends multilingual maternal health
prompts to a conversational endpoint and scores responses using
a dual-layer approach: rule-based keyword checks + dual LLM-as-judges (Gemini and Sarvam).

## Why Option B
The CeRAI AIEvaluationTool failed at installation due to undocumented
system-level dependencies (MariaDB Connector/C). Further code review
revealed architectural limitations unsuitable for API-first evaluation.
Issues filed: #108, #109, #110, #111

## Key Finding
Rule check pass rate: 46.7% | LLM judge avg: 9.95/10

The divergence between these two numbers is itself the most important
finding: keyword-based evaluation produces false positives on contextually
correct responses ("don't wait" triggers "wait" as forbidden keyword).
This validates the critique of simplistic evaluation frameworks.

## Setup

```bash
git clone https://github.com/nandinikhandelwal120603/gates-fellowship-eval
cd gates-fellowship-eval
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your GEMINI_API_KEY and SARVAM_API_KEY
python main.py --multilingual
```

## Structure
- **evaluator/**
  - `prompts.py`: 15 test cases across 5 categories
  - `endpoint.py`: Gemini 2.5 Flash (system under evaluation)
  - `judge.py`: Gemini 3 Flash Preview (primary evaluator)
  - `sarvam_judge.py`: Sarvam-M (secondary evaluator)
  - `translate.py`: Sarvam Mayura v1 (multilingual translator)
  - `runner.py`: Orchestration + aggregation
- **report/**
  - `generate.py`: HTML report generator
- **results/**
  - `results.json`: Machine-readable output
  - `report.html`: Human-readable report
- `main.py`: Entry point

## Responsible AI Note
This harness tests surface-level safety signals only. While it tests multilingual capability (Hindi, Urdu, Tamil), it does not test clinical accuracy or real-world usability by frontline
health workers. A production maternal health AI would require clinical
expert review and ongoing monitoring.
