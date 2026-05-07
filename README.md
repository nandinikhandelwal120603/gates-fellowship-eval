# Gates Fellowship Eval: Maternal Health AI Auditor

This repository contains an automated evaluation framework to audit large language models (specifically Gemini 2.5 Flash) on critical maternal health inquiries. 

The evaluation uses **LLM-as-a-Judge** (powered by Gemini 3 Flash Preview) to critique the responses based on predefined criteria, ensuring safety, accuracy, and appropriate medical disclaimers.

## Project Structure
```text
gates-fellowship-eval/
├── evaluator/
│   ├── __init__.py
│   ├── prompts.py        # 15 maternal health test cases
│   ├── endpoint.py       # Gemini 2.5 Flash (system being evaluated)
│   ├── judge.py          # Gemini 3 Flash Preview (evaluator/critic)
│   └── runner.py         # Orchestrates the evaluation
├── results/
│   ├── results.json      # Machine-readable output (generated)
│   └── report.html       # Live report page (generated)
├── report/
│   ├── __init__.py
│   └── generate.py       # Logic to generate the HTML report
├── .env                  # API Keys (not tracked)
├── requirements.txt      # Dependencies
├── main.py               # Main execution script
└── README.md             # This file
```

## Setup & Execution

1. **Environment Setup**
   Ensure you have Python 3.9+ and set up your virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **API Keys**
   You need a Google Gemini API key. Add it to your `.env` file:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

3. **Run the Evaluation**
   Execute the evaluation pipeline (takes ~3-5 minutes due to API rate limits):
   ```bash
   python main.py
   ```
   This will query the test cases, judge the responses, and generate both `results.json` and a visually readable `report.html` in the `results/` folder.

## Viewing the Report
Once generated, you can open `results/report.html` locally in your browser. 

To host the report live via GitHub Pages:
1. Push the repository to GitHub.
2. Go to **Settings** > **Pages**.
3. Set the source branch (e.g., `main`).
4. Access the live endpoint!
