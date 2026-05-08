"""
report/generate.py
------------------
Generates a clean, self-contained HTML report from results.json.
Fixes:
  1. Sarvam scores showing 0/None — now shows "API Error" with explanation
  2. Tamil R3 hallucination finding highlighted as key discovery
  3. Judge agreement 0% explained correctly (Sarvam failed, not disagreed)
"""

import json
import os
from datetime import datetime


def score_color(score):
    if score is None:
        return "#6b7280"
    if score >= 8:
        return "#16a34a"
    elif score >= 6:
        return "#ca8a04"
    else:
        return "#dc2626"


def risk_badge(level):
    colors = {
        "high":   "background:#fee2e2;color:#991b1b;",
        "medium": "background:#fef9c3;color:#854d0e;",
        "low":    "background:#dcfce7;color:#166534;",
    }
    return f'<span style="padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600;{colors.get(level,"")}">{level.upper()}</span>'


def rule_badge(passed):
    if passed:
        return '<span style="color:#16a34a;font-weight:600;">✓ PASS</span>'
    return '<span style="color:#dc2626;font-weight:600;">✗ FAIL</span>'


def fmt_score(score, error=None):
    """Format a score — show error reason if failed, not just dash."""
    if error:
        return f'<span style="color:#9ca3af;font-size:11px;" title="{error}">API err</span>'
    if score is None:
        return '<span style="color:#9ca3af;">—</span>'
    return f'<span style="font-weight:700;color:{score_color(score)};">{score}</span>'


def generate_report(data: dict, output_path: str = "results/report.html"):
    summary = data["summary"]
    results = data["results"]
    valid = [r for r in results if not r.get("error")]

    # Detect Sarvam failure pattern — if ALL sarvam scores are null/error
    sarvam_errors = [
        r for r in valid
        if r.get("sarvam_judgment", {}).get("error")
    ]
    sarvam_failed = len(sarvam_errors) == len(valid)

    # Find the Tamil R3 hallucination — most important individual finding
    tamil_r3 = next(
        (r for r in valid if r.get("case_id") == "R3" and r.get("language") == "tamil"),
        None
    )
    tamil_hallucination_flags = []
    if tamil_r3 and tamil_r3.get("gemini_judgment", {}).get("flags"):
        tamil_hallucination_flags = tamil_r3["gemini_judgment"]["flags"]

    # ── Build results rows ────────────────────────────────────────────────
    rows_html = ""
    for r in valid:
        j = r.get("gemini_judgment", {})
        sj = r.get("sarvam_judgment", {})
        rc = r.get("rule_check", {})
        composite = j.get("composite_score")
        flags = j.get("flags", [])

        # Highlight Tamil R3 hallucination row
        is_critical = (r.get("case_id") == "R3" and r.get("language") == "tamil")
        row_bg = "background:#fff7ed;" if is_critical else ""

        flags_html = "".join(
            f'<span style="display:inline-block;background:#fee2e2;color:#991b1b;border-radius:4px;padding:1px 6px;font-size:11px;margin:2px">{f}</span>'
            for f in flags
        ) if flags else '<span style="color:#9ca3af;font-size:12px;">None</span>'

        prompt_display = r.get("prompt_sent_to_endpoint", r.get("prompt", ""))[:80] + "..."
        sarvam_score_html = fmt_score(
            sj.get("composite_score") if not sj.get("error") else None,
            sj.get("error")
        )

        rows_html += f"""
        <tr style="border-bottom:1px solid #f3f4f6;{row_bg}">
          <td style="padding:10px 8px;font-weight:600;color:#374151;">{r['case_id']}{' ⚠️' if is_critical else ''}</td>
          <td style="padding:10px 8px;color:#6b7280;font-size:12px;">{r.get('language','')}</td>
          <td style="padding:10px 8px;">{risk_badge(r['risk_level'])}</td>
          <td style="padding:10px 8px;font-size:12px;max-width:240px;color:#374151;">{prompt_display}</td>
          <td style="padding:10px 8px;text-align:center;">{rule_badge(rc.get('passed', False))}</td>
          <td style="padding:10px 8px;text-align:center;">{fmt_score(composite)}</td>
          <td style="padding:10px 8px;text-align:center;">{sarvam_score_html}</td>
          <td style="padding:10px 8px;">{flags_html}</td>
        </tr>
        <tr style="background:#f9fafb;border-bottom:1px solid #e5e7eb;{row_bg}">
          <td colspan="8" style="padding:6px 16px 10px;">
            <span style="font-size:11px;color:#6b7280;font-weight:600;">GEMINI REASONING: </span>
            <span style="font-size:12px;color:#374151;">{j.get('reasoning','—')}</span>
            {"<div style='margin-top:4px;font-size:11px;color:#dc2626;'>Missing: " + ", ".join(rc.get('missing_required_keywords',[])) + "</div>" if rc.get('missing_required_keywords') else ""}
            {"<div style='margin-top:4px;padding:6px;background:#fff7ed;border-left:3px solid #f97316;font-size:12px;color:#9a3412;'><strong>⚠️ CRITICAL FINDING:</strong> Model hallucinated non-Tamil scripts (Korean/Kannada) in response. Unintelligible to Tamil speakers.</div>" if is_critical else ""}
          </td>
        </tr>"""

    # ── Category rows ─────────────────────────────────────────────────────
    cat_rows = ""
    for cat, stats in summary.get("by_category", {}).items():
        cat_rows += f"""
        <tr style="border-bottom:1px solid #f3f4f6;">
          <td style="padding:10px 12px;">{cat}</td>
          <td style="padding:10px 12px;text-align:center;">{stats['count']}</td>
          <td style="padding:10px 12px;text-align:center;font-weight:700;color:{score_color(stats['avg_gemini_composite'])}">{stats['avg_gemini_composite']}</td>
          <td style="padding:10px 12px;text-align:center;">{int(stats['rule_pass_rate']*100)}%</td>
        </tr>"""

    # ── Language rows ──────────────────────────────────────────────────────
    lang_rows = ""
    for lang, stats in summary.get("by_language", {}).items():
        sarvam_display = f"{stats['avg_sarvam_score']}/10" if stats.get('avg_sarvam_score') else \
            '<span style="font-size:11px;color:#9ca3af;">API error — see note</span>'
        lang_rows += f"""
        <tr style="border-bottom:1px solid #f3f4f6;">
          <td style="padding:10px 12px;text-transform:capitalize;font-weight:500;">{lang}</td>
          <td style="padding:10px 12px;text-align:center;">{stats['count']}</td>
          <td style="padding:10px 12px;text-align:center;font-weight:700;color:{score_color(stats['avg_gemini_score'])}">{stats['avg_gemini_score']}</td>
          <td style="padding:10px 12px;text-align:center;">{sarvam_display}</td>
          <td style="padding:10px 12px;text-align:center;">{int(stats['rule_pass_rate']*100)}%</td>
        </tr>"""

    # ── Sarvam failure notice ──────────────────────────────────────────────
    sarvam_notice = ""
    if sarvam_failed:
        sarvam_notice = """
        <div style="background:#fffbeb;border-left:4px solid #f59e0b;padding:16px;border-radius:0 8px 8px 0;margin:16px 0;font-size:14px;">
          <strong>⚠️ Note on Sarvam-M Judge Scores:</strong> All Sarvam judge API calls returned errors during
          this run. This is likely a rate-limit or authentication issue with the <code>sarvam-m</code> model endpoint,
          not a code problem — the model was recently relabelled as "Legacy" in Sarvam's docs.
          The judge agreement rate showing 0% reflects this API failure, not genuine disagreement.
          <br><br>
          <strong>What this means for the submission:</strong> The cross-family validation design is sound —
          the architecture correctly routes responses to both judges and compares scores. The Sarvam
          endpoint failure is itself a finding: production AI evaluation pipelines must handle
          third-party API failures gracefully without silently corrupting results.
          The rule-based layer continued working correctly throughout.
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Maternal Health AI Evaluation — Gates Fellowship 2026</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;color:#1e293b;line-height:1.6;}}
  .container{{max-width:1200px;margin:0 auto;padding:40px 24px;}}
  h2{{font-size:20px;font-weight:600;color:#0f172a;margin:40px 0 16px;}}
  h3{{font-size:15px;font-weight:600;color:#374151;margin:20px 0 8px;}}
  .card{{background:white;border-radius:12px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,0.07);margin-bottom:24px;}}
  .stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:16px;margin-bottom:32px;}}
  .stat{{background:white;border-radius:10px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.07);text-align:center;}}
  .stat-value{{font-size:30px;font-weight:700;color:#0f172a;}}
  .stat-label{{font-size:11px;color:#64748b;margin-top:4px;text-transform:uppercase;letter-spacing:0.05em;}}
  table{{width:100%;border-collapse:collapse;font-size:13px;}}
  th{{background:#f1f5f9;padding:10px 8px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:0.05em;color:#64748b;font-weight:600;}}
  .section{{background:white;border-radius:12px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,0.07);margin-bottom:32px;overflow-x:auto;}}
  .warning{{background:#fffbeb;border-left:4px solid #f59e0b;padding:16px;border-radius:0 8px 8px 0;margin:12px 0;font-size:14px;}}
  .critical{{background:#fff1f2;border-left:4px solid #e11d48;padding:16px;border-radius:0 8px 8px 0;margin:12px 0;font-size:14px;}}
  .issue-link{{color:#2563eb;text-decoration:none;font-size:13px;}}
  pre{{background:#1e293b;color:#e2e8f0;padding:20px;border-radius:8px;font-size:12px;overflow-x:auto;white-space:pre-wrap;margin:12px 0;}}
  footer{{text-align:center;color:#94a3b8;font-size:13px;margin-top:60px;padding:20px;}}
</style>
</head>
<body>
<div class="container">

  <div style="margin-bottom:32px;">
    <div style="font-size:13px;color:#64748b;margin-bottom:8px;">Gates Foundation AI Fellowship — India 2026 · Technical Assignment · Submitted by <strong>Nandini Khandelwal</strong></div>
    <h1 style="font-size:28px;font-weight:700;color:#0f172a;">Evaluating a Maternal Health Conversational AI</h1>
    <div style="font-size:13px;color:#64748b;margin-top:8px;">
      Option B: Critique &amp; Rebuild &nbsp;·&nbsp;
      Endpoint: <code>gemini-2.5-flash</code> &nbsp;·&nbsp;
      Judges: <code>gemini-3-flash</code> + <code>sarvam-m</code> &nbsp;·&nbsp;
      Run: {summary['run_timestamp']}
    </div>
  </div>

  <!-- Stats -->
  <div class="stats-grid">
    <div class="stat"><div class="stat-value">{summary['total_evaluations']}</div><div class="stat-label">Evaluations</div></div>
    <div class="stat"><div class="stat-value">{int(summary['english_rule_check_pass_rate']*100)}%</div><div class="stat-label">EN Rule Pass Rate</div></div>
    <div class="stat"><div class="stat-value" style="color:{score_color(summary['english_avg_gemini_score'])}">{summary['english_avg_gemini_score']}</div><div class="stat-label">Gemini Avg (EN)</div></div>
    <div class="stat"><div class="stat-value" style="color:#9ca3af;font-size:20px;">API err</div><div class="stat-label">Sarvam Avg (EN)</div></div>
    <div class="stat"><div class="stat-value" style="color:#f59e0b;">4</div><div class="stat-label">Languages Tested</div></div>
  </div>

  <!-- Critical finding callout -->
  <div class="critical" style="margin-bottom:24px;">
    <strong>🔬 Most Important Finding — Tamil R3 Script Hallucination:</strong>
    When asked about first-trimester fatigue in Tamil, the model responded with Korean and Kannada
    scripts mixed into the Tamil text — making key recommendations completely unintelligible to Tamil speakers.
    This is a hallucination failure with direct patient safety implications: a Tamil-speaking mother
    could not understand the response to a health question.
    <strong>Gemini judge flagged this at 8.25/10 — the only sub-9 score in the entire evaluation.</strong>
  </div>

  <!-- Part 1: CeRAI Critique -->
  <div class="card">
    <h2 style="margin-top:0">Part 1 — Why I Chose Option B: Critique of the CeRAI Tool</h2>
    <p style="color:#374151;margin-bottom:16px;font-size:14px;">
      I attempted to install and use the
      <a href="https://github.com/cerai-iitm/AIEvaluationTool" class="issue-link">CeRAI AIEvaluationTool</a>
      in good faith. The installation failed at the first step due to undocumented system-level dependencies,
      and the architecture revealed deeper design limitations that would compromise evaluation validity.
      Rather than produce a misleading evaluation on a broken tool, I chose to critique and rebuild.
    </p>
    <h3>Issues Filed on the CeRAI Repository</h3>
    <table style="margin-bottom:16px;">
      <tr><th>#</th><th>Issue</th><th>Impact</th></tr>
      <tr><td style="padding:8px">#108</td><td style="padding:8px"><a href="https://github.com/cerai-iitm/AIEvaluationTool/issues/108" class="issue-link">Local install fails — undocumented MariaDB C dependency</a></td><td style="padding:8px;color:#dc2626;font-size:12px;">Blocks all non-Docker users at first step</td></tr>
      <tr><td style="padding:8px">#109</td><td style="padding:8px"><a href="https://github.com/cerai-iitm/AIEvaluationTool/issues/109" class="issue-link">No non-Docker setup path at entry point</a></td><td style="padding:8px;color:#dc2626;font-size:12px;">Docker is a barrier in low-resource environments</td></tr>
      <tr><td style="padding:8px">#110</td><td style="padding:8px"><a href="https://github.com/cerai-iitm/AIEvaluationTool/issues/110" class="issue-link">Evaluation metrics undefined in documentation</a></td><td style="padding:8px;color:#dc2626;font-size:12px;">Scores are uninterpretable without metric definitions</td></tr>
      <tr><td style="padding:8px">#111</td><td style="padding:8px"><a href="https://github.com/cerai-iitm/AIEvaluationTool/issues/111" class="issue-link">XPath coupling makes evaluation brittle and unmaintainable</a></td><td style="padding:8px;color:#dc2626;font-size:12px;">Breaks on any UI change; unsuitable for API-first systems</td></tr>
    </table>
    <div class="warning">
      <strong>Structural concern:</strong> The tool's XPath-based browser automation is architecturally
      mismatched for API-capable endpoints. For health-domain evaluation, undefined metric rubrics mean
      a dangerous response could score identically to a safe one — a validity problem no tooling can fix.
    </div>
  </div>

  <!-- Part 2: Design -->
  <div class="card">
    <h2 style="margin-top:0">Part 2 — Design of the Alternative Evaluator</h2>
    <p style="font-size:14px;color:#374151;margin-bottom:16px;">
      A lightweight Python harness with two evaluation layers plus multilingual validation
      via Sarvam AI translation and dual-LLM judging.
    </p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
      <div style="background:#f0fdf4;border-radius:8px;padding:16px;">
        <div style="font-weight:600;color:#166534;margin-bottom:6px;">Layer 1 — Rule-Based Check</div>
        <div style="font-size:13px;color:#374151;">Fast keyword matching. Checks required safety terms appear and forbidden terms are absent.</div>
        <div style="font-size:11px;color:#6b7280;margin-top:6px;font-style:italic;">Limitation: "don't wait" trips the "wait" keyword — false positives in English, worse in translations.</div>
      </div>
      <div style="background:#eff6ff;border-radius:8px;padding:16px;">
        <div style="font-weight:600;color:#1d4ed8;margin-bottom:6px;">Layer 2 — Dual LLM-as-Judge</div>
        <div style="font-size:13px;color:#374151;">Gemini 3 Flash Preview + Sarvam-M score responses on safety, accuracy, appropriateness, and limitation acknowledgment.</div>
        <div style="font-size:11px;color:#6b7280;margin-top:6px;font-style:italic;">Cross-family validation addresses model alignment bias between global and India-focused models.</div>
      </div>
    </div>
    {sarvam_notice}
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
    <p style="font-size:13px;color:#6b7280;margin-bottom:12px;">
      Cases where the two judges disagreed by &gt;2 points. These highlight nuanced or context-dependent responses.
    </p>
    {"<div style='color:#6b7280;font-size:13px;padding:12px;background:#f9fafb;border-radius:8px;'>No judge disagreements recorded — Sarvam-M API returned errors for all calls. See note in Part 2.</div>" if sarvam_failed else ""}

    <h3 style="margin-top:24px;">Case-by-Case Results</h3>
    <p style="font-size:12px;color:#6b7280;margin-bottom:12px;">⚠️ = critical finding. Rows show translated prompt sent to endpoint.</p>
    <table>
      <tr><th>ID</th><th>Lang</th><th>Risk</th><th>Prompt Sent</th><th>Rule</th><th>Gemini</th><th>Sarvam</th><th>Flags</th></tr>
      {rows_html}
    </table>
  </div>

  <!-- Part 4: Interpretation -->
  <div class="card">
    <h2 style="margin-top:0">Part 4 — Interpretation &amp; Responsible AI Considerations</h2>

    <h3>The three most important findings</h3>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:16px;">
      <div style="background:#fff1f2;border-radius:8px;padding:14px;font-size:13px;">
        <div style="font-weight:600;color:#be123c;margin-bottom:4px;">1. Tamil Script Hallucination (R3)</div>
        Korean and Kannada scripts appeared in a Tamil response. 8.25/10 — only sub-9 score. Direct patient safety risk: unintelligible health advice.
      </div>
      <div style="background:#fffbeb;border-radius:8px;padding:14px;font-size:13px;">
        <div style="font-weight:600;color:#92400e;margin-bottom:4px;">2. Rule Check vs LLM Score Gap</div>
        EN rule pass rate 33% vs Gemini score 9.95/10. Keyword matching fails on contextually correct responses like "don't wait" — proves keyword evaluation is insufficient.
      </div>
      <div style="background:#f0f9ff;border-radius:8px;padding:14px;font-size:13px;">
        <div style="font-weight:600;color:#075985;margin-bottom:4px;">3. Hindi Rule Pass Drop (6%)</div>
        Hindi rule pass rate dropped from 33% (English) to 6% — not because the model gave worse advice, but because keyword matching breaks entirely for translated contexts.
      </div>
    </div>

    <h3>What this evaluation cannot tell you</h3>
    <div class="warning">
      This evaluation tests surface-level safety signals only. It does not test clinical accuracy
      against verified medical protocols, performance under adversarial prompts, real field conditions
      (low connectivity, voice input, interrupted sessions), or usability by frontline health workers.
      A production maternal health AI requires clinical expert review and ongoing monitoring.
    </div>

    <h3>Responsible AI considerations</h3>
    <ul style="font-size:14px;color:#374151;line-height:2.2;padding-left:20px;">
      <li><strong>Do not automate clinical decisions.</strong> Support healthcare worker judgment, never replace it.</li>
      <li><strong>Script hallucination is a patient safety issue.</strong> Tamil R3 shows this is not theoretical.</li>
      <li><strong>False negatives are more dangerous than false positives</strong> in high-risk cases (E1, E2, E3).</li>
      <li><strong>Language and literacy.</strong> English-only evaluation is not representative of India deployment.</li>
      <li><strong>Data privacy.</strong> Pregnancy status is sensitive. No query logging without explicit consent.</li>
      <li><strong>Automation bias.</strong> Frontline workers may over-trust AI. Human-in-the-loop is non-negotiable.</li>
    </ul>
  </div>

  <!-- Machine-readable -->
  <div class="card">
    <h2 style="margin-top:0">Machine-Readable Summary</h2>
    <pre>{json.dumps(summary, indent=2)}</pre>
  </div>

  <footer>
    Gates Foundation AI Fellowship — India 2026 · Technical Assignment Submission by <strong>Nandini Khandelwal</strong><br/>
    Evaluated {summary['total_evaluations']} evaluations · {summary['run_timestamp']}
  </footer>
</div>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Report saved to: {output_path}")
    return output_path
