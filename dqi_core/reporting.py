"""Report assembly and export (JSON / CSV / PDF).

Builds one structured report dict that both the PDF renderer and the raw
JSON/CSV export consume, so every export format shows the same numbers.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional


def build_report(dataset_profile, health, pillar_results, ranking_df, rank_corr,
                  validation_report=None, exposure_summary=None, contract_result=None,
                  pii_results=None) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "executive_summary": {
            "dataset": dataset_profile.filename,
            "rows": dataset_profile.rows,
            "columns": dataset_profile.columns,
            "overall_health": health.overall,
            "health_band": health.band,
            "weakest_pillars": health.weakest,
            "strongest_pillars": health.strongest,
            "top_issue_count": len(ranking_df) if ranking_df is not None else 0,
        },
        "dataset_profile": dataset_profile.to_dict(),
        "quality_pillars": {name: r.to_dict() for name, r in pillar_results.items()},
        "top_issues_by_impact": ranking_df.head(20).to_dict(orient="records") if ranking_df is not None and not ranking_df.empty else [],
        "frequency_vs_impact": {
            "spearman_rs": rank_corr.spearman_rs, "spearman_p": rank_corr.spearman_p,
            "kendall_tau": rank_corr.kendall_tau, "kendall_p": rank_corr.kendall_p,
            "interpretation": rank_corr.interpretation, "n_issues": rank_corr.n,
        },
        "remediation_validation": validation_report.to_dict() if validation_report else None,
        "business_exposure": exposure_summary,
        "data_contract": contract_result.to_dict() if contract_result else None,
        "pii_detections": [r.__dict__ for r in pii_results] if pii_results else [],
    }


def export_json(report: dict, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    return path


def export_csv(ranking_df, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ranking_df.to_csv(path, index=False)
    return path


def export_pdf(report: dict, path: str) -> str:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    os.makedirs(os.path.dirname(path), exist_ok=True)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=letter)
    flow = []

    flow.append(Paragraph("Data Quality Intelligence Report", styles["Title"]))
    flow.append(Spacer(1, 12))

    summary = report["executive_summary"]
    flow.append(Paragraph("Executive Summary", styles["Heading2"]))
    for k, v in summary.items():
        flow.append(Paragraph(f"<b>{k.replace('_', ' ').title()}:</b> {v}", styles["Normal"]))
    flow.append(Spacer(1, 12))

    flow.append(Paragraph("Quality Pillars", styles["Heading2"]))
    pillar_rows = [["Pillar", "Score", "Severity"]]
    for name, p in report["quality_pillars"].items():
        pillar_rows.append([name, str(p["score"]), p["severity"]])
    table = Table(pillar_rows)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    flow.append(table)
    flow.append(Spacer(1, 12))

    fvi = report["frequency_vs_impact"]
    flow.append(Paragraph("Frequency vs. Impact-Aware Ranking", styles["Heading2"]))
    flow.append(Paragraph(f"Spearman rs = {fvi['spearman_rs']} (p={fvi['spearman_p']}), "
                           f"Kendall tau = {fvi['kendall_tau']} (p={fvi['kendall_p']}), n={fvi['n_issues']}",
                           styles["Normal"]))
    flow.append(Paragraph(fvi["interpretation"], styles["Normal"]))
    flow.append(Spacer(1, 12))

    flow.append(Paragraph("Top Issues by Impact", styles["Heading2"]))
    top_issues = report["top_issues_by_impact"][:10]
    if top_issues:
        rows = [["Issue", "Column", "Impact", "Freq Rank", "Impact Rank", "Change"]]
        for i in top_issues:
            rows.append([i.get("issue_type"), str(i.get("column")), str(i.get("impact_score")),
                         str(i.get("frequency_rank")), str(i.get("impact_rank")), str(i.get("rank_change"))])
        t2 = Table(rows)
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))
        flow.append(t2)

    doc.build(flow)
    return path
