"""
Doctor-Visit Summary Generation Module for OvaCare AI.

Compiles an evidence-based clinical summary that strictly segregates:
1. Recorded Facts: Actual logged cycle start/end dates and verified menstrual flow history.
2. Clinical & Statistical Estimates: Average cycle length, prediction intervals, and estimated phase windows.
3. User-Reported Symptoms: Patient-reported physical/emotional logs, sleep durations, and personal reflections.

Clinical & Safety Guardrails:
- Non-diagnostic: Avoids clinical diagnostic labels (e.g., PCOS, PMDD, dysmenorrhea).
- Explicit data segregation: Clinicians can immediately distinguish objective dates from mathematical models and subjective patient reporting.
- Missing data distinction: Explicitly marks untracked fields so absence of logs is never confused with absence of symptoms.
- Safety guidance: Advises consulting a licensed healthcare provider and highlights red-flag indicators requiring prompt medical evaluation.
"""

import os
import sys
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

# Ensure backend root directory is on sys.path
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.abspath(os.path.join(_CURRENT_DIR, ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from db import execute_query
from common.period_tracker import (
    PHYSIOLOGICAL_CYCLE_MIN,
    PHYSIOLOGICAL_CYCLE_MAX,
    STANDARD_CYCLE_BASELINE,
    STANDARD_PERIOD_BASELINE,
    calculate_period_prediction,
    calculate_cycle_analytics_metrics,
    normalize_gap_clarification,
)
from common.wellbeing_tracker import analyze_user_wellbeing_patterns


def _parse_date(d: Any) -> Optional[date]:
    """Safely parses string, date, or datetime into date object."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        try:
            return datetime.strptime(str(d)[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def generate_doctor_summary(
    cycles: List[Dict[str, Any]],
    wellness_logs: List[Dict[str, Any]],
    user_profile: Optional[Dict[str, Any]] = None,
    prediction_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Pure generator function that creates a structured clinical visit summary.
    Segregates data into Recorded Facts, Statistical Estimates, and User-Reported Symptoms.
    """
    profile = user_profile or {}
    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # ---------------------------------------------------------
    # Timeframe calculation
    # ---------------------------------------------------------
    cycle_start_dates = [
        _parse_date(c.get('start_date')) for c in (cycles or [])
        if _parse_date(c.get('start_date')) is not None
    ]
    log_dates = [
        _parse_date(l.get('date')) for l in (wellness_logs or [])
        if _parse_date(l.get('date')) is not None
    ]
    all_dates = [d for d in (cycle_start_dates + log_dates) if d is not None]

    earliest_date_str = min(all_dates).isoformat() if all_dates else "None recorded"
    latest_date_str = max(all_dates).isoformat() if all_dates else "None recorded"

    # ---------------------------------------------------------
    # CATEGORY 1: RECORDED FACTS (Objective patient entries)
    # ---------------------------------------------------------
    chronological_cycles = sorted(
        cycles or [],
        key=lambda c: _parse_date(c.get('start_date')) or date.min
    )

    clean_cycles_facts = []
    for c in chronological_cycles:
        s_date = _parse_date(c.get('start_date'))
        e_date = _parse_date(c.get('end_date'))
        raw_gap = c.get('gap_type')
        canon_gap = normalize_gap_clarification(raw_gap)

        clean_cycles_facts.append({
            "cycle_id": c.get('cycle_id'),
            "start_date": s_date.isoformat() if s_date else None,
            "end_date": e_date.isoformat() if e_date else None,
            "recorded_cycle_length": c.get('cycle_length'),
            "recorded_period_length": c.get('period_length'),
            "is_irregular": bool(c.get('irregular')),
            "gap_clarification": canon_gap if canon_gap else ("none" if not raw_gap else raw_gap)
        })

    # Flow facts from wellness logs
    flow_distribution = {"Light": 0, "Medium": 0, "Heavy": 0, "None": 0}
    flow_logs_recorded = 0
    recent_flow_entries = []

    sorted_logs = sorted(
        wellness_logs or [],
        key=lambda l: _parse_date(l.get('date')) or date.min,
        reverse=True
    )

    for l in sorted_logs:
        flow = l.get('flow')
        if flow in flow_distribution:
            flow_distribution[flow] += 1
            flow_logs_recorded += 1
            if len(recent_flow_entries) < 15 and flow != "None":
                ld = _parse_date(l.get('date'))
                recent_flow_entries.append({
                    "date": ld.isoformat() if ld else None,
                    "flow": flow,
                    "cycle_day": l.get('cycle_day')
                })

    category_1 = {
        "title": "Category 1 — Recorded Facts",
        "description": "Direct, patient-confirmed cycle onset dates, bleeding duration, and daily flow records.",
        "total_cycles_recorded": len(clean_cycles_facts),
        "cycles": clean_cycles_facts,
        "menstrual_flow_records": {
            "total_flow_entries_logged": flow_logs_recorded,
            "flow_distribution": flow_distribution,
            "recent_flow_entries": recent_flow_entries
        }
    }

    # ---------------------------------------------------------
    # CATEGORY 2: STATISTICAL ESTIMATES (Algorithmic models)
    # ---------------------------------------------------------
    analytics_metrics = calculate_cycle_analytics_metrics(cycles or [])
    avg_cycle = analytics_metrics.get("average_cycle_length", STANDARD_CYCLE_BASELINE)
    avg_period = analytics_metrics.get("average_period_length", STANDARD_PERIOD_BASELINE)
    irregular_count = analytics_metrics.get("irregular_cycles_count", 0)

    # Use supplied prediction or compute fresh
    has_pcos = bool(profile.get('has_pcos', False))
    if prediction_data is None:
        prediction_data = calculate_period_prediction(cycles or [], has_pcos=has_pcos)

    if len(clean_cycles_facts) >= 2:
        variations = [
            c['recorded_cycle_length'] for c in clean_cycles_facts
            if c.get('recorded_cycle_length') is not None
        ]
        if variations:
            min_len = min(variations)
            max_len = max(variations)
            range_diff = max_len - min_len
            regularity_summary = (
                f"Observed cycle variation range is {range_diff} days (between {min_len} and {max_len} days). "
                + ("Typical physiological consistency." if range_diff <= 7 else "Noticeable variation observed.")
            )
        else:
            regularity_summary = "Cycle lengths pending confirmed consecutive interval history."
    else:
        regularity_summary = "Fewer than 2 cycles recorded; baseline standard defaults applied (28 days)."

    category_2 = {
        "title": "Category 2 — Statistical Estimates & Predictions",
        "description": "Calculated statistical metrics and algorithmic predictions derived from historical trends. NOT clinical laboratory tests.",
        "average_cycle_length_days": avg_cycle,
        "average_period_length_days": avg_period,
        "irregular_cycles_count": irregular_count,
        "regularity_assessment": regularity_summary,
        "predicted_next_cycle": {
            "estimated_next_start_date": prediction_data.get("predicted_next_date"),
            "estimated_window_range": prediction_data.get("window_range"),
            "confidence_level": prediction_data.get("confidence_level", "Baseline"),
            "prediction_explanation": prediction_data.get("explanation", "Calculated from past intervals.")
        },
        "methodology_note": (
            "All predicted dates and cycle averages are statistical estimates calculated from self-reported onset dates "
            "and physiological population baselines. They do not represent hormonal, ultrasound, or laboratory confirmation."
        )
    }

    # ---------------------------------------------------------
    # CATEGORY 3: USER-REPORTED SYMPTOMS (Subjective logs)
    # ---------------------------------------------------------
    total_logs = len(wellness_logs or [])
    cramps_counts = {"None": 0, "Mild": 0, "Moderate": 0, "Severe": 0, "untracked": 0}
    fatigue_counts = {"None": 0, "Mild": 0, "Moderate": 0, "Severe": 0, "untracked": 0}
    energy_counts = {"High": 0, "Moderate": 0, "Low": 0, "Very Low": 0, "untracked": 0}
    mood_counts: Dict[str, int] = {}
    stress_counts = {"Low": 0, "Medium": 0, "High": 0, "untracked": 0}
    sleep_values = []
    clinical_notes = []

    for l in sorted_logs:
        # Cramps
        c = l.get('cramps')
        if c in ("None", "Mild", "Moderate", "Severe"):
            cramps_counts[c] += 1
        else:
            cramps_counts["untracked"] += 1

        # Fatigue
        f = l.get('fatigue')
        if f in ("None", "Mild", "Moderate", "Severe"):
            fatigue_counts[f] += 1
        else:
            fatigue_counts["untracked"] += 1

        # Energy Level
        e = l.get('energy_level')
        if e in ("High", "Moderate", "Low", "Very Low"):
            energy_counts[e] += 1
        else:
            energy_counts["untracked"] += 1

        # Mood
        m = l.get('mood')
        if m:
            mood_counts[m] = mood_counts.get(m, 0) + 1

        # Stress
        st = l.get('stress')
        if st in ("Low", "Medium", "High"):
            stress_counts[st] += 1
        else:
            stress_counts["untracked"] += 1

        # Sleep
        sl = l.get('sleep_hours')
        if sl is not None:
            try:
                sl_f = float(sl)
                sleep_values.append(sl_f)
            except (ValueError, TypeError):
                pass

        # Notes
        n = l.get('notes')
        if n and str(n).strip():
            ld = _parse_date(l.get('date'))
            clinical_notes.append({
                "date": ld.isoformat() if ld else "Unknown",
                "cycle_day": l.get('cycle_day'),
                "note": str(n).strip()
            })

    avg_sleep = round(sum(sleep_values) / len(sleep_values), 1) if sleep_values else None

    # Derive longitudinal pattern intelligence
    try:
        wellbeing_report = analyze_user_wellbeing_patterns(cycles or [], wellness_logs or [])
        supported_patterns = [
            {
                "pattern_title": p.get("title"),
                "metric": p.get("metric"),
                "observation": p.get("observation"),
                "cycle_window": p.get("cycle_window"),
                "is_window_estimated": p.get("window_is_estimated", False),
                "distinct_cycles_observed": p.get("distinct_cycles_observed"),
                "recurrence_ratio": f"{p.get('recurrence_count')}/{p.get('recurrence_denominator')}" if p.get('recurrence_count') is not None else None,
                "evidence_status": p.get("evidence_status"),
                "supportive_care_tip": p.get("supportive_recommendation")
            }
            for p in wellbeing_report.get("patterns", [])
            if p.get("evidence_status") == "supported"
        ]
    except Exception:
        supported_patterns = []

    category_3 = {
        "title": "Category 3 — User-Reported Symptoms & Wellness Notes",
        "description": "Patient self-reported daily physical comfort, mood, stress, sleep, and reflective notes.",
        "total_days_logged": total_logs,
        "symptom_frequency_breakdown": {
            "cramps": cramps_counts,
            "fatigue": fatigue_counts,
            "energy_levels": energy_counts,
            "mood_distribution": mood_counts,
            "stress_distribution": stress_counts,
            "sleep_hours_summary": {
                "recorded_days": len(sleep_values),
                "average_hours_per_night": avg_sleep,
                "range_min": min(sleep_values) if sleep_values else None,
                "range_max": max(sleep_values) if sleep_values else None
            }
        },
        "observed_longitudinal_patterns": supported_patterns,
        "recent_patient_notes": clinical_notes[:10],
        "reporting_note": (
            "Untracked days reflect days where a parameter was not logged, which is distinct from explicit symptom absence."
        )
    }

    # ---------------------------------------------------------
    # CLINICAL SAFETY & DISCLAIMERS
    # ---------------------------------------------------------
    safety_guidance = [
        "Acute severe pelvic, lower back, or abdominal pain — particularly if sudden, worsening, or accompanied by dizziness or fever — warrants immediate medical evaluation.",
        "Abnormally heavy menstrual bleeding (e.g., soaking through one or more sanitary pads/tampons every hour for two consecutive hours) should be evaluated promptly by a healthcare professional.",
        "Cycle irregularities (e.g., cycles consistently shorter than 21 days, longer than 35 days, or absent for more than 90 days) should be investigated by a physician.",
        "OvaCare AI is an assistive wellness log and self-tracking application. It does not provide medical diagnoses, treatment plans, or clinical triage."
    ]

    disclaimer = (
        "This summary is compiled from patient-entered self-tracking data and statistical estimation algorithms. "
        "It is provided solely to facilitate collaborative conversations between the patient and their healthcare provider. "
        "It does not replace comprehensive medical history, physical examination, diagnostic laboratory testing, or physician clinical judgment."
    )

    return {
        "report_id": f"doc_summary_{int(datetime.utcnow().timestamp())}",
        "generated_at": now_iso,
        "patient_context": {
            "username": profile.get('username', 'Patient'),
            "age": profile.get('age'),
            "lifestyle": profile.get('lifestyle'),
            "has_pcos_reported": has_pcos
        },
        "timeframe": {
            "earliest_record": earliest_date_str,
            "latest_record": latest_date_str,
            "total_cycles_logged": len(clean_cycles_facts),
            "total_wellness_entries_logged": total_logs
        },
        "category_1_recorded_facts": category_1,
        "category_2_statistical_estimates": category_2,
        "category_3_user_reported_symptoms": category_3,
        "safety_guidance": safety_guidance,
        "clinical_disclaimer": disclaimer
    }


def get_user_doctor_summary(user_id: str) -> Dict[str, Any]:
    """
    Database-backed helper that queries cycles, wellness logs, and user profile
    for the authenticated user_id and generates the complete doctor summary.
    Enforces user-scoped data access.
    """
    if not user_id:
        raise ValueError("user_id is required")

    # Fetch user profile
    user_rows = execute_query(
        "SELECT user_id, username, age, lifestyle, has_pcos FROM users WHERE user_id = :user_id",
        {"user_id": user_id}
    )
    user_profile = user_rows[0] if user_rows else {}
    if user_profile:
        user_profile['has_pcos'] = bool(user_profile.get('has_pcos', False))

    # Fetch cycles
    cycles = execute_query(
        """
        SELECT cycle_id, user_id, start_date, end_date, cycle_length, period_length, irregular, gap_type
        FROM cycles
        WHERE user_id = :user_id
        ORDER BY start_date ASC
        """,
        {"user_id": user_id}
    )

    # Fetch wellness logs
    wellness_logs = execute_query(
        """
        SELECT log_id, user_id, date, cycle_day, mood, stress, sleep_hours,
               cramps, fatigue, flow, energy_level, notes
        FROM wellness_logs
        WHERE user_id = :user_id
        ORDER BY date ASC
        """,
        {"user_id": user_id}
    )

    # Fetch prediction
    prediction_data = calculate_period_prediction(
        cycles,
        has_pcos=bool(user_profile.get('has_pcos', False))
    )

    return generate_doctor_summary(
        cycles=cycles,
        wellness_logs=wellness_logs,
        user_profile=user_profile,
        prediction_data=prediction_data
    )


def render_doctor_summary_html(summary: Dict[str, Any]) -> str:
    """
    Renders a clean, print-friendly clinical HTML report from the summary dictionary.
    Includes print media styling, crisp tables, and explicit visual separation between
    Facts, Estimates, and Patient-Reported Symptoms.
    """
    patient = summary.get("patient_context", {})
    timeframe = summary.get("timeframe", {})
    cat1 = summary.get("category_1_recorded_facts", {})
    cat2 = summary.get("category_2_statistical_estimates", {})
    cat3 = summary.get("category_3_user_reported_symptoms", {})
    safety = summary.get("safety_guidance", [])
    disclaimer = summary.get("clinical_disclaimer", "")

    # Build cycle rows
    cycle_rows_html = ""
    for c in cat1.get("cycles", []):
        s_date = c.get("start_date") or "—"
        e_date = c.get("end_date") or "—"
        c_len = f"{c.get('recorded_cycle_length')} days" if c.get('recorded_cycle_length') is not None else "—"
        p_len = f"{c.get('recorded_period_length')} days" if c.get('recorded_period_length') is not None else "—"
        irreg = "Yes (Variance)" if c.get('is_irregular') else "Regular"
        gap = c.get('gap_clarification') or "None"
        cycle_rows_html += f"""
        <tr>
            <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0;">{s_date}</td>
            <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0;">{e_date}</td>
            <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0; font-weight: 600;">{c_len}</td>
            <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0;">{p_len}</td>
            <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0;">{irreg}</td>
            <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0; color: #64748b; font-size: 11px;">{gap}</td>
        </tr>
        """
    if not cycle_rows_html:
        cycle_rows_html = '<tr><td colspan="6" style="padding: 12px; text-align: center; color: #94a3b8; font-style: italic;">No cycle onset dates recorded yet.</td></tr>'

    # Build flow distribution pills
    flow_dist = cat1.get("menstrual_flow_records", {}).get("flow_distribution", {})
    flow_pills_html = " ".join([
        f'<span style="background: #f1f5f9; padding: 3px 8px; border-radius: 6px; font-size: 12px; margin-right: 6px;"><strong>{k}:</strong> {v} days</span>'
        for k, v in flow_dist.items()
    ])

    # Build symptoms breakdown tables
    sym_freq = cat3.get("symptom_frequency_breakdown", {})
    cramps_str = ", ".join([f"{k}: {v}" for k, v in sym_freq.get("cramps", {}).items() if v > 0 or k == 'untracked'])
    fatigue_str = ", ".join([f"{k}: {v}" for k, v in sym_freq.get("fatigue", {}).items() if v > 0 or k == 'untracked'])
    energy_str = ", ".join([f"{k}: {v}" for k, v in sym_freq.get("energy_levels", {}).items() if v > 0 or k == 'untracked'])
    mood_str = ", ".join([f"{k}: {v}" for k, v in sym_freq.get("mood_distribution", {}).items()]) or "None logged"
    stress_str = ", ".join([f"{k}: {v}" for k, v in sym_freq.get("stress_distribution", {}).items()])

    sleep_summary = sym_freq.get("sleep_hours_summary", {})
    avg_sleep = sleep_summary.get("average_hours_per_night")
    sleep_display = f"{avg_sleep} hrs/night (Recorded across {sleep_summary.get('recorded_days', 0)} nights)" if avg_sleep else "Untracked"

    # Build longitudinal patterns
    patterns_html = ""
    for p in cat3.get("observed_longitudinal_patterns", []):
        patterns_html += f"""
        <div style="background: #faf5ff; border: 1px solid #e9d5ff; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
            <div style="font-weight: 600; color: #6b21a8; font-size: 13px;">{p.get('pattern_title')}</div>
            <div style="font-size: 12px; color: #374151; margin-top: 2px;">{p.get('observation')}</div>
            <div style="font-size: 11px; color: #7e22ce; margin-top: 4px;">
                <span><strong>Window:</strong> {p.get('cycle_window')} {'(Estimated)' if p.get('is_window_estimated') else ''}</span> |
                <span><strong>Recurrence:</strong> {p.get('recurrence_ratio') or 'N/A'}</span>
            </div>
        </div>
        """
    if not patterns_html:
        patterns_html = '<p style="font-size: 12px; color: #64748b; font-style: italic;">No recurring patterns identified yet across recorded cycles.</p>'

    # Build safety list
    safety_items_html = "".join([f'<li style="margin-bottom: 4px;">{s}</li>' for s in safety])

    # Full HTML Document
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>OvaCare Clinical Summary — {patient.get('username', 'Patient')}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #1e293b;
            background: #ffffff;
            margin: 0;
            padding: 24px;
            font-size: 13px;
            line-height: 1.5;
        }}
        .container {{
            max-width: 820px;
            margin: 0 auto;
        }}
        .header {{
            border-bottom: 2px solid #8b5cf6;
            padding-bottom: 12px;
            margin-bottom: 18px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        .header-title {{
            font-size: 22px;
            font-weight: 700;
            color: #5b21b6;
            margin: 0;
        }}
        .header-subtitle {{
            font-size: 12px;
            color: #64748b;
            margin-top: 2px;
        }}
        .patient-card {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 10px 16px;
            margin-bottom: 18px;
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            font-size: 12px;
        }}
        .section-box {{
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            margin-bottom: 18px;
            overflow: hidden;
            page-break-inside: avoid;
        }}
        .section-header {{
            padding: 10px 14px;
            font-weight: 700;
            font-size: 13px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .section-body {{
            padding: 12px 14px;
        }}
        .badge-facts {{ background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; }}
        .badge-estimates {{ background: #f5f3ff; color: #5b21b6; border: 1px solid #ddd6fe; }}
        .badge-symptoms {{ background: #fff1f2; color: #9f1239; border: 1px solid #fecdd3; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            margin-top: 6px;
        }}
        th {{
            text-align: left;
            background: #f8fafc;
            padding: 6px 10px;
            border-bottom: 2px solid #cbd5e1;
            font-weight: 600;
            color: #475569;
        }}
        .disclaimer-box {{
            background: #fefce8;
            border: 1px solid #fef08a;
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 11px;
            color: #854d0e;
            margin-bottom: 16px;
        }}
        .safety-box {{
            background: #fff7ed;
            border: 1px solid #fed7aa;
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 11px;
            color: #9a3412;
            margin-bottom: 16px;
        }}
        .print-btn {{
            background: #8b5cf6;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            margin-bottom: 16px;
        }}
        @media print {{
            .print-btn {{ display: none; }}
            body {{ padding: 0; }}
            .container {{ max-width: 100%; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>

        <div class="header">
            <div>
                <h1 class="header-title">OvaCare AI — Clinical Visit Summary</h1>
                <div class="header-subtitle">Separating Recorded Facts, Statistical Estimates, and User-Reported Symptoms</div>
            </div>
            <div style="text-align: right; font-size: 11px; color: #64748b;">
                <div><strong>Generated:</strong> {summary.get('generated_at')}</div>
                <div><strong>Report ID:</strong> {summary.get('report_id')}</div>
            </div>
        </div>

        <div class="patient-card">
            <div><strong>Patient Name:</strong> {patient.get('username', 'Patient')}</div>
            <div><strong>Age:</strong> {patient.get('age') or 'Unspecified'}</div>
            <div><strong>Lifestyle:</strong> {patient.get('lifestyle') or 'Moderate'}</div>
            <div><strong>Self-Reported PCOS:</strong> {'Yes' if patient.get('has_pcos_reported') else 'No'}</div>
        </div>

        <div class="disclaimer-box">
            <strong>Clinical Notice & Non-Diagnostic Scope:</strong> {disclaimer}
        </div>

        <!-- CATEGORY 1: RECORDED FACTS -->
        <div class="section-box">
            <div class="section-header badge-facts">
                <span>Category 1: Recorded Facts (Patient Confirmed Onset & Bleeding Dates)</span>
                <span style="font-size: 11px; font-weight: normal;">{cat1.get('total_cycles_recorded', 0)} cycles logged</span>
            </div>
            <div class="section-body">
                <p style="margin: 0 0 8px 0; font-size: 11px; color: #475569;">
                    {cat1.get('description')}
                </p>
                <table>
                    <thead>
                        <tr>
                            <th>Start Date</th>
                            <th>End Date</th>
                            <th>Cycle Length</th>
                            <th>Bleeding Days</th>
                            <th>Regularity</th>
                            <th>Gap Clarification</th>
                        </tr>
                    </thead>
                    <tbody>
                        {cycle_rows_html}
                    </tbody>
                </table>
                <div style="margin-top: 10px;">
                    <strong style="font-size: 11px; color: #475569;">Menstrual Flow Distribution:</strong>
                    <div style="margin-top: 4px;">{flow_pills_html}</div>
                </div>
            </div>
        </div>

        <!-- CATEGORY 2: STATISTICAL ESTIMATES -->
        <div class="section-box">
            <div class="section-header badge-estimates">
                <span>Category 2: Statistical Estimates & Prediction Windows (Algorithmic Models)</span>
                <span style="font-size: 11px; font-weight: normal;">Mathematical Baseline</span>
            </div>
            <div class="section-body">
                <p style="margin: 0 0 10px 0; font-size: 11px; color: #475569;">
                    {cat2.get('description')}
                </p>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 10px;">
                    <div style="background: #f8fafc; padding: 8px 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
                        <div style="font-size: 11px; color: #64748b;">Average Cycle Duration</div>
                        <div style="font-size: 16px; font-weight: 700; color: #5b21b6;">{cat2.get('average_cycle_length_days')} days</div>
                    </div>
                    <div style="background: #f8fafc; padding: 8px 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
                        <div style="font-size: 11px; color: #64748b;">Average Bleeding Duration</div>
                        <div style="font-size: 16px; font-weight: 700; color: #5b21b6;">{cat2.get('average_period_length_days')} days</div>
                    </div>
                    <div style="background: #f8fafc; padding: 8px 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
                        <div style="font-size: 11px; color: #64748b;">Next Estimated Start Date</div>
                        <div style="font-size: 16px; font-weight: 700; color: #5b21b6;">{cat2.get('predicted_next_cycle', {}).get('estimated_next_start_date') or 'Pending'}</div>
                    </div>
                </div>
                <div style="font-size: 12px; color: #334155; margin-bottom: 4px;">
                    <strong>Regularity Analysis:</strong> {cat2.get('regularity_assessment')}
                </div>
                <div style="font-size: 11px; color: #64748b; font-style: italic;">
                    * {cat2.get('methodology_note')}
                </div>
            </div>
        </div>

        <!-- CATEGORY 3: USER-REPORTED SYMPTOMS -->
        <div class="section-box">
            <div class="section-header badge-symptoms">
                <span>Category 3: User-Reported Symptoms & Daily Logs (Subjective Entries)</span>
                <span style="font-size: 11px; font-weight: normal;">{cat3.get('total_days_logged', 0)} daily entries</span>
            </div>
            <div class="section-body">
                <p style="margin: 0 0 10px 0; font-size: 11px; color: #475569;">
                    {cat3.get('description')}
                </p>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; font-size: 12px; margin-bottom: 12px;">
                    <div style="background: #f8fafc; padding: 8px 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
                        <strong>Pelvic Cramps Reported:</strong>
                        <div style="font-size: 11px; color: #475569; margin-top: 2px;">{cramps_str}</div>
                    </div>
                    <div style="background: #f8fafc; padding: 8px 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
                        <strong>Fatigue Levels Reported:</strong>
                        <div style="font-size: 11px; color: #475569; margin-top: 2px;">{fatigue_str}</div>
                    </div>
                    <div style="background: #f8fafc; padding: 8px 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
                        <strong>Energy Levels Reported:</strong>
                        <div style="font-size: 11px; color: #475569; margin-top: 2px;">{energy_str}</div>
                    </div>
                    <div style="background: #f8fafc; padding: 8px 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
                        <strong>Sleep Hours Logged:</strong>
                        <div style="font-size: 11px; color: #475569; margin-top: 2px;">{sleep_display}</div>
                    </div>
                    <div style="background: #f8fafc; padding: 8px 12px; border-radius: 6px; border: 1px solid #e2e8f0; grid-column: span 2;">
                        <strong>Mood Distribution:</strong>
                        <div style="font-size: 11px; color: #475569; margin-top: 2px;">{mood_str} | <strong>Stress Distribution:</strong> {stress_str}</div>
                    </div>
                </div>

                <div style="margin-top: 12px;">
                    <strong style="font-size: 12px; color: #475569;">Observed Longitudinal Correlations (Evidence-Supported):</strong>
                    <div style="margin-top: 6px;">
                        {patterns_html}
                    </div>
                </div>
            </div>
        </div>

        <div class="safety-box">
            <strong>Clinical Safety Guidance & Red-Flag Warnings:</strong>
            <ul style="margin: 6px 0 0 18px; padding: 0;">
                {safety_items_html}
            </ul>
        </div>

        <div style="border-top: 1px dashed #cbd5e1; padding-top: 14px; margin-top: 20px; display: flex; justify-content: space-between; font-size: 11px; color: #94a3b8;">
            <div>OvaCare AI Menstrual Wellness Companion</div>
            <div>Confidential Medical Tracking Document — For Clinical Review Only</div>
        </div>
    </div>
</body>
</html>
"""
    return html
