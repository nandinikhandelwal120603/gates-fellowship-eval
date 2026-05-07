"""
report/generate.py
------------------
Generates a clean, self-contained HTML report from results.json.
Designed to serve as the "live endpoint" submission.
"""

import json
import os
from datetime import datetime


def score_color(score):
    if score >= 8:
        return "#16a34a"   # green
    elif score >= 6:
        return "#ca8a04"   # amber
    else:
        return "#dc2626"   # red


def risk_badge(level):
    colors = {
        "high": "background:#fee2e2;color:#991b1b;",
        "medium": "background:#fef9c3;color:#854d0e;",
        "low": "background:#dcfce7;color:#166534;",
    }
    style = colors.get(level, "")
    return f'<span style="padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600;{style}">{level.upper()}</span>'


def rule_badge(passed):
    if passed:
        return '<span style="color:#16a34a;font-weight:600;">✓ PASS</span>'
    return '<span style="color:#dc2626;font-weight:600;">✗ FAIL</span>'


def generate_report(data: dict, output_path: str = "results/report.html"):
    summary = data["summary"]
    results = data["results"]
    valid = [r for r in results if not r.get("error") and r.get("llm_judgment") and not r["llm_judgment"].get("error")]

    # Build results rows
    rows_html = ""
    for r in valid:
        j = r["llm_judgment"]
        rc = r["rule_check"]
        composite = j.get("composite_score", 0)
        flags = j.get("flags", [])
        flags_html = "".join(
            f'<span style="display:inline-block;background:#fee2e2;color:#991b1b;border-radius:4px;padding:1px 6px;font-size:11px;margin:2px">{f}</span>'
            for f in flags
        ) if flags else '<span style="color:#6b7280;font-size:12px;">None</span>'

        rows_html += f"""
        <tr style="border-bottom:1px solid #f3f4f6;">
          <td style="padding:12px 8px;font-weight:600;color:#374151;">{r['case_id']}</td>
          <td style="padding:12px 8px;color:#6b7280;font-size:13px;">{r['category']}</td>
          <td style="padding:12px 8px;">{risk_badge(r['risk_level'])}</td>
          <td style="padding:12px 8px;font-size:13px;max-width:280px;">{r['prompt']}</td>
          <td style="padding:12px 8px;text-align:center;">{rule_badge(rc['passed'])}</td>
          <td style="padding:12px 8px;text-align:center;font-weight:700;color:{score_color(j.get('safety_score',0))};">{j.get('safety_score','—')}</td>
          <td style="padding:12px 8px;text-align:center;font-weight:700;color:{score_color(j.get('accuracy_score',0))};">{j.get('accuracy_score','—')}</td>
          <td style="padding:12px 8px;text-align:center;font-weight:700;font-size:16px;color:{score_color(composite)};">{composite}</td>
          <td style="padding:12px 8px;">{flags_html}</td>
        </tr>
        <tr style="background:#f9fafb;border-bottom:1px solid #e5e7eb;">
          <td colspan="9" style="padding:8px 16px 12px;">
            <div style="font-size:12px;color:#6b7280;margin-bottom:4px;font-weight:600;">JUDGE REASONING</div>
            <div style="font-size:13px;color:#374151;line-height:1.5;">{j.get('reasoning','—')}</div>
            {"<div style='margin-top:6px;font-size:12px;color:#dc2626;'>Missing keywords: " + ", ".join(rc['missing_required_keywords']) + "</div>" if rc['missing_required_keywords'] else ""}
          </td>
        </tr>"""

    # Category breakdown table
    cat_rows = ""
    for cat, stats in summary.get("by_category", {}).items():
        cat_rows += f"""
        <tr style="border-bottom:1px solid #f3f4f6;">
          <td style="padding:10px 12px;">{cat}</td>
          <td style="padding:10px 12px;text-align:center;">{stats['count']}</td>
          <td style="padding:10px 12px;text-align:center;font-weight:700;color:{score_color(stats['avg_composite'])}">{stats['avg_composite']}</td>
          <td style="padding:10px 12px;text-align:center;">{int(stats['rule_pass_rate']*100)}%</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Maternal Health AI Evaluation — Gates Fellowship 2026 — Nandini Khandelwal</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f8fafc; color: #1e293b; line-height: 1.6; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 24px; }}
  h1 {{ font-size: 28px; font-weight: 700; color: #0f172a; }}
  h2 {{ font-size: 20px; font-weight: 600; color: #0f172a; margin: 40px 0 16px; }}
  h3 {{ font-size: 16px; font-weight: 600; color: #374151; margin: 24px 0 8px; }}
  .meta {{ color: #64748b; font-size: 14px; margin-top: 6px; }}
  .card {{ background: white; border-radius: 12px; padding: 24px;
           box-shadow: 0 1px 3px rgba(0,0,0,0.07); margin-bottom: 24px; }}
  .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; }}
  .stat {{ background: white; border-radius: 10px; padding: 20px;
           box-shadow: 0 1px 3px rgba(0,0,0,0.07); text-align: center; }}
  .stat-value {{ font-size: 32px; font-weight: 700; color: #0f172a; }}
  .stat-label {{ font-size: 12px; color: #64748b; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.05em; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th {{ background: #f1f5f9; padding: 10px 8px; text-align: left;
       font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em;
       color: #64748b; font-weight: 600; }}
  .section {{ background: white; border-radius: 12px; padding: 24px;
              box-shadow: 0 1px 3px rgba(0,0,0,0.07); margin-bottom: 32px; overflow-x: auto; }}
  .tag {{ display: inline-block; background: #e0f2fe; color: #0369a1;
          padding: 2px 8px; border-radius: 4px; font-size: 12px; margin: 2px; }}
  .warning {{ background: #fffbeb; border-left: 4px solid #f59e0b;
              padding: 16px; border-radius: 0 8px 8px 0; margin: 12px 0; font-size: 14px; }}
  .issue-link {{ color: #2563eb; text-decoration: none; font-size: 13px; }}
  .issue-link:hover {{ text-decoration: underline; }}
  pre {{ background: #1e293b; color: #e2e8f0; padding: 20px; border-radius: 8px;
         font-size: 13px; overflow-x: auto; white-space: pre-wrap; margin: 12px 0; }}
  footer {{ text-align: center; color: #94a3b8; font-size: 13px; margin-top: 60px; padding: 20px; }}
</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div style="margin-bottom:32px;">
    <div style="font-size:13px;color:#64748b;margin-bottom:8px;">Gates Foundation AI Fellowship — India 2026 &middot; Technical Assignment &middot; Submitted by <strong>Nandini Khandelwal</strong></div>
    <h1>Evaluating a Maternal Health Conversational AI</h1>
    <div style="font-size:13px;color:#64748b;margin-top:8px;">
      Option B: Critique &amp; Rebuild &nbsp;·&nbsp;
      Endpoint: <code>gemini-2.5-flash</code> &nbsp;·&nbsp;
      Judge: <code>gemini-3-flash-preview</code> &nbsp;·&nbsp;
      Run: {summary['run_timestamp']}
    </div>
  </div>

  <!-- Summary Stats -->
  <div class="stats-grid" style="margin-bottom:32px;">
    <div class="stat">
      <div class="stat-value">{summary['total_cases']}</div>
      <div class="stat-label">Test Cases</div>
    </div>
    <div class="stat">
      <div class="stat-value" style="color:{score_color(summary['avg_composite_score'])}">{summary['avg_composite_score']}</div>
      <div class="stat-label">Avg Composite Score</div>
    </div>
    <div class="stat">
      <div class="stat-value" style="color:{score_color(summary['avg_safety_score'])}">{summary['avg_safety_score']}</div>
      <div class="stat-label">Avg Safety Score</div>
    </div>
    <div class="stat">
      <div class="stat-value">{int(summary['rule_check_pass_rate']*100)}%</div>
      <div class="stat-label">Rule Check Pass Rate</div>
    </div>
    <div class="stat">
      <div class="stat-value">{summary['avg_latency_seconds']}s</div>
      <div class="stat-label">Avg Latency</div>
    </div>
  </div>

  <!-- Part 1: CeRAI Critique -->
  <div class="card">
    <h2 style="margin-top:0">Part 1 — Why I Chose Option B: Critique of the CeRAI Tool</h2>
    <p style="color:#374151;margin-bottom:16px;">
      I attempted to install and use the
      <a href="https://github.com/cerai-iitm/AIEvaluationTool" class="issue-link">CeRAI AIEvaluationTool</a>
      in good faith. The installation failed at the first step due to undocumented system-level dependencies,
      and the architecture revealed deeper design limitations that would compromise evaluation validity.
      Rather than produce a misleading evaluation on a broken tool, I chose to critique and rebuild.
    </p>

    <h3>Issues Filed on the CeRAI Repository</h3>
    <table style="margin-bottom:16px;">
      <tr><th>#</th><th>Issue</th><th>Impact</th></tr>
      <tr><td style="padding:8px">#108</td>
        <td style="padding:8px"><a href="https://github.com/cerai-iitm/AIEvaluationTool/issues/108" class="issue-link">Local install fails — undocumented MariaDB C dependency</a></td>
        <td style="padding:8px;color:#dc2626;font-size:13px;">Blocks all non-Docker users at first step</td></tr>
      <tr><td style="padding:8px">#109</td>
        <td style="padding:8px"><a href="https://github.com/cerai-iitm/AIEvaluationTool/issues/109" class="issue-link">No non-Docker setup path at entry point</a></td>
        <td style="padding:8px;color:#dc2626;font-size:13px;">Docker is a barrier in low-resource environments</td></tr>
      <tr><td style="padding:8px">#110</td>
        <td style="padding:8px"><a href="https://github.com/cerai-iitm/AIEvaluationTool/issues/110" class="issue-link">Evaluation metrics undefined in documentation</a></td>
        <td style="padding:8px;color:#dc2626;font-size:13px;">Scores are uninterpretable without metric definitions</td></tr>
      <tr><td style="padding:8px">#111</td>
        <td style="padding:8px"><a href="https://github.com/cerai-iitm/AIEvaluationTool/issues/111" class="issue-link">XPath coupling makes evaluation brittle and unmaintainable</a></td>
        <td style="padding:8px;color:#dc2626;font-size:13px;">Breaks on any UI change; unsuitable for API-first systems</td></tr>
    </table>

    <div class="warning">
      <strong>Structural concern beyond installation:</strong> The tool's reliance on browser automation (Selenium + XPaths)
      to evaluate conversational systems is architecturally mismatched for API-capable endpoints.
      For health-domain evaluation specifically, the absence of defined metric rubrics means a dangerous
      response could score identically to a safe one — a validity problem no amount of tooling can paper over.
    </div>
  </div>

  <!-- Part 2: Alternative Design -->
  <div class="card">
    <h2 style="margin-top:0">Part 2 — Design of the Alternative Evaluator</h2>

    <h3>Architecture</h3>
    <p style="font-size:14px;color:#374151;margin-bottom:12px;">
      A lightweight Python evaluation harness (~250 lines) with two distinct evaluation layers:
    </p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
      <div style="background:#f0fdf4;border-radius:8px;padding:16px;">
        <div style="font-weight:600;color:#166534;margin-bottom:6px;">Layer 1 — Rule-Based Check</div>
        <div style="font-size:13px;color:#374151;">Fast, deterministic keyword matching. Checks that required safety terms appear and forbidden terms (e.g. "wait", "normal") are absent. No model call required.</div>
        <div style="font-size:12px;color:#6b7280;margin-top:8px;font-style:italic;">Limitation: brittle. "Don't take ibuprofen" passes the keyword check despite correct advice.</div>
      </div>
      <div style="background:#eff6ff;border-radius:8px;padding:16px;">
        <div style="font-weight:600;color:#1d4ed8;margin-bottom:6px;">Layer 2 — LLM-as-Judge</div>
        <div style="font-size:13px;color:#374151;">Gemini 3 Flash Preview scores responses on a 4-dimension rubric: safety, accuracy, appropriateness, and limitation acknowledgment. Returns structured JSON.</div>
        <div style="font-size:12px;color:#6b7280;margin-top:8px;font-style:italic;">Limitation: judge can be overconfident. First test run returned 10/10 — warrants scrutiny.</div>
      </div>
    </div>

    <h3>Why This Design</h3>
    <p style="font-size:14px;color:#374151;">
      Running both layers in parallel is itself an experiment: where they agree, we have higher confidence.
      Where they diverge — rule check fails but LLM judge scores high — it surfaces exactly the brittleness
      of keyword-based evaluation. This is more informative than either method alone.
    </p>

    <h3>Why Gemini 2.5 Flash as Endpoint</h3>
    <p style="font-size:14px;color:#374151;">
      Maternal and fetal health risk stratification is the stated track for this fellowship.
      Evaluating a health Q&amp;A assistant creates direct relevance: the same evaluation questions —
      Does the system flag emergencies? Does it recommend human oversight? Does it acknowledge uncertainty? —
      apply to production health AI systems.
    </p>
  </div>

  <!-- Part 3: Results -->
  <div class="section">
    <h2 style="margin-top:0">Part 3 — Evaluation Results</h2>

    <h3>By Category</h3>
    <table style="margin-bottom:24px;">
      <tr><th>Category</th><th>Cases</th><th>Avg Score</th><th>Rule Pass Rate</th></tr>
      {cat_rows}
    </table>

    <h3>Case-by-Case Results</h3>
    <table>
      <tr>
        <th>ID</th><th>Category</th><th>Risk</th><th>Prompt</th>
        <th>Rule</th><th>Safety</th><th>Accuracy</th><th>Score</th><th>Flags</th>
      </tr>
      {rows_html}
    </table>
  </div>

  <!-- Part 4: Interpretation -->
  <div class="card">
    <h2 style="margin-top:0">Part 4 — Interpretation &amp; Responsible AI Considerations</h2>

    <h3>What the results show</h3>
    <p style="font-size:14px;color:#374151;margin-bottom:12px;">
      The LLM judge scores are consistently high — which itself requires scrutiny.
      An LLM judging another LLM's output from the same provider family may share
      similar blind spots. This is known as <em>judge-model alignment bias</em>.
      The rule-based check acts as a partial corrective — any case where keywords
      required for safe triage are absent is flagged regardless of judge confidence.
    </p>

    <h3>What this evaluation cannot tell you</h3>
    <div class="warning">
      <strong>Critical limitation:</strong> This evaluation tests fluency and surface-level safety signals.
      It does not test factual accuracy against clinical ground truth, performance on code-switching
      or non-English inputs, behavior under adversarial prompting, or real-world usability
      by frontline health workers in low-connectivity environments.
      A production maternal health AI system would require clinical expert review,
      community testing, and ongoing monitoring — none of which this harness provides.
    </div>

    <h3>Responsible AI considerations for health-domain deployment</h3>
    <ul style="font-size:14px;color:#374151;line-height:2;padding-left:20px;">
      <li><strong>Do not automate clinical decisions.</strong> This system should support, not replace, healthcare worker judgment.</li>
      <li><strong>Explainability matters.</strong> A risk flag without reasoning creates anxiety and erodes trust. Every output should include why.</li>
      <li><strong>False negatives are more dangerous than false positives</strong> in high-risk maternal cases (E1, E2, E3). Calibrate accordingly.</li>
      <li><strong>Language and literacy.</strong> Most maternal health interactions in India occur in regional languages. English-only evaluation is not representative.</li>
      <li><strong>Data privacy.</strong> Pregnancy status is sensitive health information. Any deployed system must not log or train on user queries without consent.</li>
      <li><strong>Automation bias.</strong> Frontline workers may over-trust AI recommendations. Human-in-the-loop design is non-negotiable.</li>
    </ul>
  </div>

  <!-- Machine-readable block -->
  <div class="card">
    <h2 style="margin-top:0">Machine-Readable Summary</h2>
    <pre>{json.dumps(summary, indent=2)}</pre>
  </div>

  <footer>
    Gates Foundation AI Fellowship — India 2026 &middot; Technical Assignment Submission by <strong>Nandini Khandelwal</strong><br/>
    Evaluated {summary['total_cases']} test cases · {summary['run_timestamp']}
  </footer>

</div>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    print(f"  Report saved to: {output_path}")
    return output_path
