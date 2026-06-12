"""
PDF report builder using ReportLab.

Generates a professional PDF from the structured report dict
produced by generator.py. Uses ReportLab (already in requirements.txt).

Sections:
1. Executive Summary
2. Interview Overview
3. Communication Analysis
4. Behavioral Insights (dynamic metrics)
5. Attention Indicators
6. Integrity Indicators
7. Stress Indicators
8. Emotional Stability
9. Technical Summary
10. Evidence-Based Observations
11. Transcript Appendix
"""

import io
import logging
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)

logger = logging.getLogger(__name__)

# Colors
ACCENT = colors.HexColor("#0055ff")
SUCCESS = colors.HexColor("#10b981")
WARNING = colors.HexColor("#f59e0b")
DANGER = colors.HexColor("#ef4444")
GRAY = colors.HexColor("#6b7280")
LIGHT_BG = colors.HexColor("#f9fafb")


def build_pdf(report_data: dict) -> bytes:
    """
    Generate a PDF report from the structured report dict.

    Returns PDF as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    styles.add(ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        textColor=ACCENT,
        spaceAfter=8,
        spaceBefore=16,
    ))
    styles.add(ParagraphStyle(
        "SubInfo",
        parent=styles["Normal"],
        textColor=GRAY,
        fontSize=9,
    ))
    styles.add(ParagraphStyle(
        "Evidence",
        parent=styles["Normal"],
        fontSize=8,
        textColor=GRAY,
        leftIndent=16,
        borderPadding=4,
    ))

    elements = []

    # ── Title ────────────────────────────────────────────────────────────
    exec_summary = report_data.get("executive_summary", {})
    candidate = exec_summary.get("candidate", "Unknown Candidate")
    job = exec_summary.get("job", "")

    elements.append(Paragraph(
        f"Interview Analysis Report",
        styles["Title"],
    ))
    elements.append(Paragraph(
        f"Candidate: {candidate}" + (f" — {job}" if job else ""),
        styles["SubInfo"],
    ))
    elements.append(Paragraph(
        f"Generated: {report_data.get('generated_at', 'N/A')}",
        styles["SubInfo"],
    ))
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", color=ACCENT, thickness=1))
    elements.append(Spacer(1, 12))

    # ── Section 1: Executive Summary ─────────────────────────────────────
    elements.append(Paragraph("1. Executive Summary", styles["SectionTitle"]))
    summary_data = [
        ["Duration", f"{exec_summary.get('duration_minutes', 'N/A')} min"],
        ["Status", exec_summary.get("status", "N/A")],
        ["Dominant Emotion", exec_summary.get("dominant_emotion", "N/A")],
        ["Avg Confidence", f"{exec_summary.get('avg_confidence', 0)}%"],
        ["Overall Sentiment", exec_summary.get("overall_sentiment", "N/A")],
        ["Metrics Computed", str(exec_summary.get("metrics_computed", 0))],
        ["Integrity Alerts", str(exec_summary.get("integrity_alerts", 0))],
    ]
    elements.append(_build_kv_table(summary_data))
    elements.append(Spacer(1, 8))

    # ── Section 2: Interview Overview ────────────────────────────────────
    overview = report_data.get("interview_overview", {})
    elements.append(Paragraph("2. Interview Overview", styles["SectionTitle"]))
    overview_data = [
        ["Started", overview.get("started_at", "N/A")],
        ["Ended", overview.get("ended_at", "N/A")],
        ["Total Frames", str(overview.get("total_frames", 0))],
        ["Transcript Chunks", str(overview.get("transcript_chunks", 0))],
        ["Questions Generated", str(overview.get("questions_generated", 0))],
        ["Questions Asked", str(overview.get("questions_asked", 0))],
    ]
    elements.append(_build_kv_table(overview_data))
    elements.append(Spacer(1, 8))

    # ── Section 3: Communication Analysis ────────────────────────────────
    comm = report_data.get("communication_analysis", {})
    elements.append(Paragraph("3. Communication Analysis", styles["SectionTitle"]))
    sentiment = comm.get("overall_sentiment", {})
    elements.append(Paragraph(
        f"Sentiment: {sentiment.get('label', 'N/A')} "
        f"({round(sentiment.get('score', 0) * 100)}% confidence) — "
        f"{comm.get('word_count', 0)} words across {comm.get('transcript_chunks', 0)} chunks",
        styles["Normal"],
    ))

    big_five = comm.get("big_five", {})
    if big_five:
        elements.append(Spacer(1, 4))
        elements.append(Paragraph("Big Five Personality Signals:", styles["Normal"]))
        bf_data = [[trait.title(), f"{score:.1f}/10"] for trait, score in big_five.items()]
        elements.append(_build_kv_table(bf_data))

    elements.append(Spacer(1, 8))

    # ── Section 4: Behavioral Insights ───────────────────────────────────
    behavioral = report_data.get("behavioral_insights", {})
    metrics = behavioral.get("metrics", [])
    elements.append(Paragraph("4. Behavioral Insights", styles["SectionTitle"]))

    if metrics:
        metric_data = [["Metric", "Score", "Level"]]
        for m in metrics:
            metric_data.append([
                m.get("name", ""),
                f"{m.get('score', 0)}/100",
                m.get("level", ""),
            ])
        t = Table(metric_data, colWidths=[200, 80, 100])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph("No behavioral metrics computed.", styles["Normal"]))

    elements.append(Spacer(1, 8))

    # ── Section 5: Attention Indicators ──────────────────────────────────
    attention = report_data.get("attention_indicators", {})
    elements.append(Paragraph("5. Attention Indicators", styles["SectionTitle"]))
    if attention:
        elements.append(Paragraph(
            f"Eye contact ratio: {attention.get('center_ratio', 'N/A')}% — "
            f"Total events: {attention.get('total_events', 0)}",
            styles["Normal"],
        ))
    else:
        elements.append(Paragraph(
            "Attention tracking data will be available when MediaPipe is active.",
            styles["SubInfo"],
        ))

    elements.append(Spacer(1, 8))

    # ── Section 6: Integrity Indicators ──────────────────────────────────
    integrity = report_data.get("integrity_indicators", {})
    elements.append(Paragraph("6. Integrity Indicators", styles["SectionTitle"]))
    int_events = integrity.get("events", [])

    if int_events:
        elements.append(Paragraph(
            f"{integrity.get('total_alerts', 0)} alert(s) detected.",
            styles["Normal"],
        ))
        for event in int_events[:10]:  # limit to first 10
            sev = event.get("severity", "info")
            color = "#ef4444" if sev == "critical" else "#f59e0b" if sev == "warning" else "#6b7280"
            elements.append(Paragraph(
                f'<font color="{color}">[{sev.upper()}]</font> '
                f'{event.get("event_type", "")} — {event.get("timestamp", "")}',
                styles["Normal"],
            ))
    else:
        elements.append(Paragraph("No integrity concerns detected.", styles["Normal"]))

    elements.append(Spacer(1, 8))

    # ── Section 7: Stress Indicators ─────────────────────────────────────
    stress = report_data.get("stress_indicators")
    elements.append(Paragraph("7. Stress Indicators", styles["SectionTitle"]))
    if stress:
        elements.append(Paragraph(
            f"Score: {stress.get('score', 0)}/100 ({stress.get('level', 'N/A')})",
            styles["Normal"],
        ))
        if stress.get("explanation"):
            elements.append(Paragraph(stress["explanation"], styles["SubInfo"]))
    else:
        elements.append(Paragraph("Stress metric not available.", styles["SubInfo"]))

    elements.append(Spacer(1, 8))

    # ── Section 8: Emotional Stability ───────────────────────────────────
    emo_stab = report_data.get("emotional_stability", {})
    elements.append(Paragraph("8. Emotional Stability", styles["SectionTitle"]))
    metric = emo_stab.get("metric")
    if metric:
        elements.append(Paragraph(
            f"Score: {metric.get('score', 0)}/100 ({metric.get('level', 'N/A')})",
            styles["Normal"],
        ))
        if metric.get("explanation"):
            elements.append(Paragraph(metric["explanation"], styles["SubInfo"]))
    breakdown = emo_stab.get("emotion_breakdown", {})
    if breakdown:
        elements.append(Spacer(1, 4))
        bd_data = [[em.title(), f"{pct}%"] for em, pct in breakdown.items()]
        elements.append(_build_kv_table(bd_data))

    elements.append(Spacer(1, 8))

    # ── Section 9: Technical Summary ─────────────────────────────────────
    tech = report_data.get("technical_summary", {})
    elements.append(Paragraph("9. Technical Summary", styles["SectionTitle"]))
    skills = tech.get("job_skills", [])
    if tech.get("job_title"):
        elements.append(Paragraph(f"Role: {tech['job_title']}", styles["Normal"]))
    if tech.get("seniority"):
        elements.append(Paragraph(f"Seniority: {tech['seniority']}", styles["Normal"]))
    if skills:
        elements.append(Paragraph(f"Required skills: {', '.join(skills)}", styles["Normal"]))

    elements.append(Spacer(1, 8))

    # ── Section 10: Evidence-Based Observations ──────────────────────────
    evidence_obs = report_data.get("evidence_observations", {})
    elements.append(Paragraph("10. Evidence-Based Observations", styles["SectionTitle"]))
    metrics_with_ev = evidence_obs.get("metrics_with_evidence", [])
    if metrics_with_ev:
        for m in metrics_with_ev:
            elements.append(Paragraph(
                f"<b>{m['name']}</b> — {m['score']}/100 ({m['level']})",
                styles["Normal"],
            ))
            if m.get("explanation"):
                elements.append(Paragraph(m["explanation"], styles["SubInfo"]))
            for ev in m.get("evidence", [])[:3]:
                quote = ev.get("quote", "")
                if quote:
                    elements.append(Paragraph(f'"{quote}"', styles["Evidence"]))
            elements.append(Spacer(1, 4))
    else:
        elements.append(Paragraph("No evidence-based observations available.", styles["SubInfo"]))

    # ── Section 11: Transcript Appendix ──────────────────────────────────
    elements.append(PageBreak())
    transcript_data = report_data.get("transcript_appendix", {})
    elements.append(Paragraph("11. Transcript Appendix", styles["SectionTitle"]))

    full_text = transcript_data.get("full_transcript", "")
    if full_text:
        # Truncate for PDF (very long transcripts can crash ReportLab)
        display_text = full_text[:8000]
        if len(full_text) > 8000:
            display_text += f"\n\n[...truncated — {len(full_text)} characters total]"
        elements.append(Paragraph(display_text, styles["Normal"]))
    else:
        elements.append(Paragraph("No transcript data available.", styles["SubInfo"]))

    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


def _build_kv_table(data: list[list]) -> Table:
    """Build a simple 2-column key-value table."""
    t = Table(data, colWidths=[200, 200])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), GRAY),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
    ]))
    return t
