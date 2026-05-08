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
    if score is None:
        return "#6b7280"
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
    valid = [r for r in results if not r.get("error") and r.get("gemini_judgment") and not r["gemini_judgment"].get("error")]

    # Build results rows
    rows_html = ""
    for r in valid:
        gj = r.get("gemini_judgment", {})
        sj = r.get("sarvam_judgment", {})
        rc = r["rule_check"]
        gem_comp = gj.get("composite_score", 0)
        sarv_comp = sj.get("composite_score", 0) if sj and not sj.get("error") else None
        
        flags = gj.get("flags", [])
        flags_html = "".join(
            f'<span style="display:inline-block;background:#fee2e2;color:#991b1b;border-radius:4px;padding:1px 6px;font-size:11px;margin:2px">{f}</span>'
            for f in flags
        ) if flags else '<span style="color:#6b7280;font-size:12px;">None</span>'

        rows_html += f"""
        <tr style="border-bottom:1px solid #f3f4f6;">
          <td style="padding:12px 8px;font-weight:600;color:#374151;">{r['case_id']}</td>
          <td style="padding:12px 8px;color:#6b7280;font-size:13px;text-transform:capitalize;">{r.get('language', 'english')}</td>
          <td style="padding:12px 8px;">{risk_badge(r['risk_level'])}</td>
          <td style="padding:12px 8px;font-size:13px;max-width:280px;">{r.get('prompt_used', r.get('prompt', ''))}</td>
          <td style="padding:12px 8px;text-align:center;">{rule_badge(rc['passed'])}</td>
          <td style="padding:12px 8px;text-align:center;font-weight:700;font-size:16px;color:{score_color(gem_comp)};">{gem_comp}</td>
          <td style="padding:12px 8px;text-align:center;font-weight:700;font-size:16px;color:{score_color(sarv_comp)};">{sarv_comp if sarv_comp is not None else '—'}</td>
          <td style="padding:12px 8px;">{flags_html}</td>
        </tr>
        <tr style="background:#f9fafb;border-bottom:1px solid #e5e7eb;">
          <td colspan="8" style="padding:8px 16px 12px;">
            <div style="font-size:12px;color:#6b7280;margin-bottom:4px;font-weight:600;">GEMINI JUDGE REASONING</div>
            <div style="font-size:13px;color:#374151;line-height:1.5;margin-bottom:6px;">{gj.get('reasoning','—')}</div>
            <div style="font-size:12px;color:#6b7280;margin-bottom:4px;font-weight:600;">SARVAM JUDGE REASONING</div>
            <div style="font-size:13px;color:#374151;line-height:1.5;">{sj.get('reasoning','—') if sj and not sj.get("error") else '—'}</div>
            {"<div style='margin-top:6px;font-size:12px;color:#dc2626;'>Missing keywords: " + ", ".join(rc['missing_required_keywords']) + "</div>" if rc.get('missing_required_keywords') else ""}
          </td>
        </tr>"""

    # Language breakdown table
    lang_rows = ""
    for lang, stats in summary.get("by_language", {}).items():
        lang_rows += f"""
        <tr style="border-bottom:1px solid #f3f4f6;">
          <td style="padding:10px 12px;text-transform:capitalize;">{lang}</td>
          <td style="padding:10px 12px;text-align:center;">{stats['count']}</td>
          <td style="padding:10px 12px;text-align:center;font-weight:700;color:{score_color(stats.get('avg_gemini_score'))}">{stats.get('avg_gemini_score', '—')}</td>
          <td style="padding:10px 12px;text-align:center;font-weight:700;color:{score_color(stats.get('avg_sarvam_score'))}">{stats.get('avg_sarvam_score', '—')}</td>
          <td style="padding:10px 12px;text-align:center;">{int(stats['rule_pass_rate']*100)}%</td>
        </tr>"""

    # Category breakdown table
    cat_rows = ""
    for cat, stats in summary.get("by_category", {}).items():
        cat_rows += f"""
        <tr style="border-bottom:1px solid #f3f4f6;">
          <td style="padding:10px 12px;">{cat}</td>
          <td style="padding:10px 12px;text-align:center;">{stats['count']}</td>
          <td style="padding:10px 12px;text-align:center;font-weight:700;color:{score_color(stats.get('avg_gemini_composite'))}">{stats.get('avg_gemini_composite', '—')}</td>
          <td style="padding:10px 12px;text-align:center;">{int(stats['rule_pass_rate']*100)}%</td>
        </tr>"""

    # Disagreement rows
    disagree_rows = ""
    for c in summary.get("conflicting_cases", []):
        disagree_rows += f"""
        <tr style="border-bottom:1px solid #f3f4f6; background:#fff1f2;">
          <td style="padding:10px 12px;font-weight:600;">{c['case_id']}</td>
          <td style="padding:10px 12px;text-transform:capitalize;">{c['language']}</td>
          <td style="padding:10px 12px;text-align:center;font-weight:700;color:{score_color(c['gemini'])}">{c['gemini']}</td>
          <td style="padding:10px 12px;text-align:center;font-weight:700;color:{score_color(c['sarvam'])}">{c['sarvam']}</td>
          <td style="padding:10px 12px;text-align:center;font-weight:700;color:#991b1b;">{c['diff']}</td>
        </tr>"""

    if not disagree_rows:
        disagree_rows = '<tr><td colspan="5" style="padding:10px 12px;text-align:center;color:#6b7280;">No major judge disagreements found.</td></tr>'

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
      Endpoint: <code>{summary.get('endpoint_model', 'gemini-2.5-flash')}</code> &nbsp;·&nbsp;
      Judges: <code>gemini-3-flash</code> + <code>sarvam-m</code> &nbsp;·&nbsp;
      Run: {summary.get('run_timestamp', '')}
    </div>
  </div>

  <!-- Summary Stats -->
  <div class="stats-grid" style="margin-bottom:32px;">
    <div class="stat">
      <div class="stat-value">{summary.get('total_evaluations', summary.get('total_cases', 0))}</div>
      <div class="stat-label">Evaluations</div>
    </div>
    <div class="stat">
      <div class="stat-value">{int(summary.get('english_rule_check_pass_rate', summary.get('rule_check_pass_rate', 0))*100)}%</div>
      <div class="stat-label">EN Rule Pass Rate</div>
    </div>
    <div class="stat">
      <div class="stat-value" style="color:{score_color(summary.get('english_avg_gemini_score', 0))}">{summary.get('english_avg_gemini_score', 0)}</div>
      <div class="stat-label">Gemini Avg (EN)</div>
    </div>
    <div class="stat">
      <div class="stat-value" style="color:{score_color(summary.get('english_avg_sarvam_score', 0))}">{summary.get('english_avg_sarvam_score', 0)}</div>
      <div class="stat-label">Sarvam Avg (EN)</div>
    </div>
    <div class="stat">
      <div class="stat-value" style="color:#0f172a;">{int(summary.get('judge_agreement_rate', 0)*100)}%</div>
      <div class="stat-label">Judge Agreement</div>
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
      A lightweight Python evaluation harness with two distinct evaluation layers, plus multilingual validation via translation APIs and dual-LLM judging.
    </p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
      <div style="background:#f0fdf4;border-radius:8px;padding:16px;">
        <div style="font-weight:600;color:#166534;margin-bottom:6px;">Layer 1 — Rule-Based Check</div>
        <div style="font-size:13px;color:#374151;">Fast, deterministic keyword matching. Checks that required safety terms appear and forbidden terms (e.g. "wait", "normal") are absent. No model call required.</div>
        <div style="font-size:12px;color:#6b7280;margin-top:8px;font-style:italic;">Limitation: brittle. "Don't take ibuprofen" passes the keyword check despite correct advice.</div>
      </div>
      <div style="background:#eff6ff;border-radius:8px;padding:16px;">
        <div style="font-weight:600;color:#1d4ed8;margin-bottom:6px;">Layer 2 — Dual LLM-as-Judge</div>
        <div style="font-size:13px;color:#374151;">Both Gemini 3 Flash Preview and Sarvam-M independently score responses on safety, accuracy, and appropriateness.</div>
        <div style="font-size:12px;color:#6b7280;margin-top:8px;font-style:italic;">Cross-Family Validation: Addresses model alignment bias by comparing scores between a global model and an India-focused model.</div>
      </div>
    </div>
  </div>

  <!-- Part 3: Results -->
  <div class="section">
    <h2 style="margin-top:0">Part 3 — Evaluation Results</h2>

    <h3>By Language</h3>
    <table style="margin-bottom:24px;">
      <tr><th>Language</th><th>Cases</th><th>Avg Gemini Score</th><th>Avg Sarvam Score</th><th>Rule Pass Rate</th></tr>
      {lang_rows}
    </table>

    <h3>By Category (English)</h3>
    <table style="margin-bottom:24px;">
      <tr><th>Category</th><th>Cases</th><th>Avg Gemini Score</th><th>Rule Pass Rate</th></tr>
      {cat_rows}
    </table>

    <h3>Judge Disagreement (Flagged Cases)</h3>
    <p style="font-size:13px;color:#6b7280;margin-bottom:8px;">Cases where the two judges disagreed by >2 points. These highlight potential cultural or linguistic nuances.</p>
    <table style="margin-bottom:24px;">
      <tr><th>Case ID</th><th>Language</th><th>Gemini Score</th><th>Sarvam Score</th><th>Diff</th></tr>
      {disagree_rows}
    </table>

    <h3>Case-by-Case Results</h3>
    <table>
      <tr>
        <th>ID</th><th>Lang</th><th>Risk</th><th>Prompt</th>
        <th>Rule</th><th>Gemini</th><th>Sarvam</th><th>Flags</th>
      </tr>
      {rows_html}
    </table>
  </div>

  <!-- Part 4: Interpretation -->
  <div class="card">
    <h2 style="margin-top:0">Part 4 — Interpretation &amp; Responsible AI Considerations</h2>

    <h3>What the results show</h3>
    <p style="font-size:14px;color:#374151;margin-bottom:12px;">
      Comparing an India-focused judge (Sarvam-M) with a general model (Gemini) reveals cases where the general model misses nuances or where they disagree on safety guidelines. Judge agreement rate ({int(summary.get('judge_agreement_rate', 0)*100)}%) is a strong signal: where they diverge, it often means the case is nuanced or context-dependent.
    </p>

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
    Evaluated {summary.get('total_evaluations', summary.get('total_cases', 0))} evaluations · {summary.get('run_timestamp', '')}
  </footer>

</div>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    print(f"  Report saved to: {output_path}")
    return output_path
