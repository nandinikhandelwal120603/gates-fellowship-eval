# Maternal Health AI Evaluation
### Gates Foundation AI Fellowship — India 2026 | Technical Assignment

**Path chosen:** Option B — Critique & Rebuild  
**Live report:** [https://nandinikhandelwal120603.github.io/gates-fellowship-eval/](https://nandinikhandelwal120603.github.io/gates-fellowship-eval/)  
**Endpoint model:** `gemini-2.5-flash` | **Judges:** `gemini-3-flash-preview` (Primary) & `sarvam-1` (Cross-Family Validation)
**Languages:** English, Hindi, Gujarati, Tamil

## What This Is
A lightweight AI evaluation harness designed for the Indian context. It sends multilingual maternal health prompts to a conversational endpoint and scores responses using a dual-layer approach: 
1. **Rule-based keyword checks** (Now with multilingual support)
2. **Dual LLM-as-judges** (Gemini and Sarvam-M) to detect semantic safety and cultural alignment.

## Why Option B?
The original CeRAI `AIEvaluationTool` failed at installation due to undocumented system-level dependencies (MariaDB Connector/C) and architectural limitations (hardcoded paths, lack of API-first support). This project was rebuilt from the ground up to handle the specific needs of multilingual maternal health in India.

Issues filed during audit: #108, #109, #110, #111

## Key Finding: The "Multilingual Safety Gap"
- **Rule Pass Rate (Multilingual):** ~10-20%
- **LLM Judge Average:** 9.5+/10

The divergence between these numbers is the core finding of this fellowship project. Traditional keyword-based safety tools (like those in CeRAI) fail catastrophically in a multilingual setting because they look for English keywords. 

Even after implementing **Multilingual Rule Checks** (translating safety keywords into Hindi, Gujarati, and Tamil), the semantic nuance captured by the **LLM-as-Judge** remains significantly more reliable. This validates the need for agentic, model-based evaluation for maternal health bots.

## Multilingual Resilience
The pipeline uses **Sarvam AI's Mayura v1** for high-fidelity translation of test cases and **Sarvam-M** as a secondary judge to ensure that the evaluation isn't biased towards a single model family (Gemini). This creates a "checks and balances" system for safety.

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
  - `prompts.py`: 15 high-risk test cases (Emergency, Medication, Nutrition, etc.)
  - `endpoint.py`: Gemini 2.5 Flash (The system being evaluated)
  - `judge.py`: Gemini 3 Flash Preview (Primary evaluator with multilingual mapping)
  - `sarvam_judge.py`: Sarvam-M (Cross-validation judge)
  - `translate.py`: Sarvam Mayura v1 (Handles prompt translation)
  - `runner.py`: Orchestration engine
- **report/**
  - `generate.py`: Generates the interactive HTML dashboard
- **results/**
  - `results.json`: Full machine-readable audit trail
- `index.html`: The latest live report

## Responsible AI Note
This harness tests safety signals and cultural alignment across Hindi, Gujarati, and Tamil. However, it is a technical evaluation tool and **not** a clinical audit. A production-ready maternal health AI requires review by certified medical professionals and continuous monitoring of real-world interactions.

**Student:** Nandini Khandelwal
