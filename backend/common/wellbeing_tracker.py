"""
Physical and Emotional Wellbeing Intelligence Engine for OvaCare AI.

Provides deterministic, explainable, and privacy-preserving pattern detection
by analyzing longitudinal wellness logs (fatigue, cramps, mood, stress, sleep)
grouped and aligned by authenticated user menstrual cycle boundaries.

Non-negotiable clinical & safety principles:
- Evidence-based: Insights only generate when supported by user-logged records.
- Non-causal: Never asserts that menstruation, hormones, or cycle phases "caused" a symptom.
- Non-diagnostic: Avoids clinical terms (PMS, PMDD, dysmenorrhea, insomnia, anovulation).
- Missing data distinction: Explicitly distinguishes unrecorded fields from symptom absence.
- Window estimation transparency: Explains how phase windows are derived and marks them as estimated.
- Minimum-evidence guardrails: Rejects pattern claims when history is insufficient or unreliable.
"""

import os
import sys
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple

# Ensure backend directory is in path
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
    normalize_gap_clarification,
)

# Configurable product rules for evidence-based insight generation
DEFAULT_WELLBEING_CONFIG = {
    "min_cycles_for_pattern": 2,          # Minimum cycles with logs in target window to claim a recurring pattern
    "min_logged_days_for_pattern": 3,      # Minimum total days logged in target window across cycles
    "min_recurrence_ratio": 0.66,         # Pattern must appear in >= 66% of cycles with data in window
    "premenstrual_days": 5,               # Number of days before period onset considered premenstrual window
    "default_period_length": 5,           # Assumed menstrual days if period_length not recorded
    "max_cycle_length_reliable": 45,      # Cycle lengths exceeding 45d are unreliable unless clarified
}


def _parse_date(d: Any) -> Optional[date]:
    """Safely converts string, date, or datetime objects to a date object."""
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


def assign_logs_to_cycles(
    cycles: List[Dict[str, Any]], 
    wellness_logs: List[Dict[str, Any]],
    avg_cycle_length: int = STANDARD_CYCLE_BASELINE
) -> List[Dict[str, Any]]:
    """
    Groups wellness logs into corresponding cycle intervals.
    
    Each cycle output dict contains:
      - cycle_id
      - start_date
      - next_start_date (None if ongoing/latest)
      - period_length
      - cycle_length (actual or estimated)
      - is_completed (bool)
      - is_reliable (bool: False if unclarified tracking gap or non-physiological length)
      - logs (list of log dicts falling into this cycle)
    """
    if not cycles:
        return []

    # Sort cycles chronologically ascending
    sorted_cycles = sorted(
        cycles, 
        key=lambda c: _parse_date(c.get('start_date')) or date.min
    )

    cycle_structures = []
    for i, c in enumerate(sorted_cycles):
        s_date = _parse_date(c.get('start_date'))
        if not s_date:
            continue

        next_s_date = None
        if i + 1 < len(sorted_cycles):
            next_s_date = _parse_date(sorted_cycles[i + 1].get('start_date'))

        # Period length determination
        p_len = c.get('period_length')
        if p_len is None and c.get('end_date'):
            e_date = _parse_date(c.get('end_date'))
            if e_date and e_date >= s_date:
                p_len = (e_date - s_date).days + 1
        if p_len is None or p_len <= 0 or p_len > 15:
            p_len = DEFAULT_WELLBEING_CONFIG["default_period_length"]

        # Cycle length determination
        c_len = c.get('cycle_length')
        if c_len is None and next_s_date:
            c_len = (next_s_date - s_date).days

        # Reliability evaluation
        gap_type = normalize_gap_clarification(c.get('gap_type'))
        is_reliable = True
        reliability_reason = None

        if gap_type in ('unclarified_gap', 'missed_period', 'forgotten_entry'):
            is_reliable = False
            reliability_reason = f"Cycle contains tracking gap ({gap_type})"
        elif c_len and c_len > DEFAULT_WELLBEING_CONFIG["max_cycle_length_reliable"] and gap_type != 'confirmed_long_cycle':
            is_reliable = False
            reliability_reason = f"Cycle length ({c_len}d) exceeds 45 days without confirmation"
        elif c_len and c_len < PHYSIOLOGICAL_CYCLE_MIN:
            is_reliable = False
            reliability_reason = f"Cycle length ({c_len}d) below 21 days"

        cycle_structures.append({
            "cycle_id": c.get('cycle_id'),
            "start_date": s_date,
            "next_start_date": next_s_date,
            "period_length": p_len,
            "cycle_length": c_len or avg_cycle_length,
            "is_completed": bool(next_s_date),
            "is_reliable": is_reliable,
            "reliability_reason": reliability_reason,
            "gap_type": gap_type,
            "logs": []
        })

    # Associate wellness logs to cycles
    for log in wellness_logs:
        l_date = _parse_date(log.get('date'))
        if not l_date:
            continue

        assigned = False
        for c_struct in cycle_structures:
            s_date = c_struct["start_date"]
            next_date = c_struct["next_start_date"]

            if next_date:
                # Completed cycle interval [start_date, next_start_date)
                if s_date <= l_date < next_date:
                    c_struct["logs"].append(log)
                    assigned = True
                    break
            else:
                # Ongoing latest cycle: from start_date up to estimated cycle boundary
                cutoff = s_date + timedelta(days=c_struct["cycle_length"] + 14)
                if s_date <= l_date <= cutoff:
                    c_struct["logs"].append(log)
                    assigned = True
                    break

    return cycle_structures


def classify_log_phase_window(
    log: Dict[str, Any],
    cycle: Dict[str, Any],
    premenstrual_days: int = 5
) -> Dict[str, Any]:
    """
    Assigns a wellness log to an estimated phase window relative to cycle boundaries.
    
    Returns:
      {
         "window": "menstrual" | "follicular" | "mid_cycle" | "premenstrual" | "other",
         "window_label": Human-readable description,
         "cycle_day": Integer day in cycle (1-indexed),
         "days_before_next_period": Optional integer if premenstrual,
         "is_estimated": True (explicitly marked as estimated)
      }
    """
    l_date = _parse_date(log.get('date'))
    s_date = cycle["start_date"]
    next_s_date = cycle.get("next_start_date")
    p_len = cycle.get("period_length", 5)
    c_len = cycle.get("cycle_length", STANDARD_CYCLE_BASELINE)

    cycle_day = (l_date - s_date).days + 1 if (l_date and s_date) else log.get('cycle_day') or 1

    # Check 1: Menstrual phase
    if cycle_day <= p_len:
        return {
            "window": "menstrual",
            "window_label": f"Menstrual days (Days 1–{p_len})",
            "cycle_day": cycle_day,
            "days_before_next_period": None,
            "is_estimated": False  # anchored on logged period dates
        }

    # Check 2: Premenstrual / Late Luteal Window (e.g. 1 to 5 days before next period)
    is_premenstrual = False
    days_before = None

    if next_s_date and l_date:
        days_until_next = (next_s_date - l_date).days
        if 1 <= days_until_next <= premenstrual_days:
            is_premenstrual = True
            days_before = days_until_next
    elif c_len:
        # Estimated against cycle length
        estimated_end = s_date + timedelta(days=c_len)
        if l_date:
            days_until_est = (estimated_end - l_date).days
            if 0 <= days_until_est <= premenstrual_days:
                is_premenstrual = True
                days_before = days_until_est

    if is_premenstrual:
        return {
            "window": "premenstrual",
            "window_label": f"Premenstrual days ({premenstrual_days} days before next period)",
            "cycle_day": cycle_day,
            "days_before_next_period": days_before,
            "is_estimated": True
        }

    # Check 3: Mid-cycle / Ovulatory window estimation (approx 40% to 60% of cycle)
    mid_start = int(c_len * 0.40) + 1
    mid_end = int(c_len * 0.60)
    if mid_start <= cycle_day <= mid_end:
        return {
            "window": "mid_cycle",
            "window_label": f"Mid-cycle window (Estimated Days {mid_start}–{mid_end})",
            "cycle_day": cycle_day,
            "days_before_next_period": None,
            "is_estimated": True
        }

    # Check 4: Follicular window (post-period to mid-cycle)
    if p_len < cycle_day < mid_start:
        return {
            "window": "follicular",
            "window_label": f"Follicular window (Estimated Days {p_len + 1}–{mid_start - 1})",
            "cycle_day": cycle_day,
            "days_before_next_period": None,
            "is_estimated": True
        }

    return {
        "window": "other",
        "window_label": f"Cycle Day {cycle_day}",
        "cycle_day": cycle_day,
        "days_before_next_period": None,
        "is_estimated": True
    }


def evaluate_cycle_window_metric(
    logs_in_window: List[Dict[str, Any]],
    metric_type: str
) -> Tuple[bool, int, int]:
    """
    Evaluates whether a metric pattern occurred in a single cycle's phase window.
    
    Returns:
      (has_occurrence, total_valid_logs, positive_observation_count)
      
    Guarantees:
      - Treats missing/unrecorded fields as unrecorded, NOT as absence of symptoms.
      - Never fabricates records.
    """
    if not logs_in_window:
        return False, 0, 0

    valid_logs = 0
    positive_count = 0

    for log in logs_in_window:
        if metric_type == "lower_energy":
            # Evaluates fatigue or explicit tired mood / low energy
            fatigue = log.get("fatigue")
            mood = log.get("mood")
            energy = log.get("energy_level")

            # Check if this metric was recorded at all
            is_recorded = (fatigue is not None) or (mood is not None) or (energy is not None)
            if not is_recorded:
                continue

            valid_logs += 1
            has_lower_energy = (
                fatigue in ("Moderate", "Severe") or
                mood == "Tired" or
                energy in ("Low", "Very Low")
            )
            if has_lower_energy:
                positive_count += 1

        elif metric_type == "cramps_pain":
            cramps = log.get("cramps")
            if cramps is None or str(cramps).strip().lower() in ('', 'unrecorded', 'null'):
                continue

            valid_logs += 1
            if cramps in ("Moderate", "Severe", "Mild"):
                positive_count += 1

        elif metric_type == "elevated_stress":
            stress = log.get("stress")
            if stress is None or str(stress).strip().lower() in ('', 'unrecorded', 'null'):
                continue

            valid_logs += 1
            if stress == "High":
                positive_count += 1

        elif metric_type == "emotional_sensitivity":
            mood = log.get("mood")
            if mood is None or str(mood).strip().lower() in ('', 'unrecorded', 'null'):
                continue

            valid_logs += 1
            if mood in ("Emotional", "Irritated", "Anxious"):
                positive_count += 1

        elif metric_type == "sleep_disruption":
            sleep = log.get("sleep_hours")
            if sleep is None:
                continue

            try:
                sleep_val = float(sleep)
                valid_logs += 1
                if sleep_val < 6.5:
                    positive_count += 1
            except (ValueError, TypeError):
                continue

    has_occurrence = (positive_count > 0)
    return has_occurrence, valid_logs, positive_count


def analyze_user_wellbeing_patterns(
    cycles: List[Dict[str, Any]],
    wellness_logs: List[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Pure analysis function that inspects cycle-grouped wellness logs and returns
    structured, explainable pattern candidates with evidence metrics.
    
    Returns:
      {
        "status": "ready" | "insufficient_data" | "unreliable_history",
        "cycles_evaluated_count": int,
        "reliable_cycles_count": int,
        "total_wellness_logs": int,
        "patterns": List[Dict],
        "insufficient_data_reasons": List[str]
      }
    """
    cfg = dict(DEFAULT_WELLBEING_CONFIG)
    if config:
        cfg.update(config)

    min_cycles = cfg["min_cycles_for_pattern"]
    min_days = cfg["min_logged_days_for_pattern"]
    min_ratio = cfg["min_recurrence_ratio"]
    premenstrual_days = cfg["premenstrual_days"]

    total_logs = len(wellness_logs) if wellness_logs else 0

    # Guardrail 1: Empty history
    if not cycles or not wellness_logs:
        return {
            "status": "insufficient_data",
            "cycles_evaluated_count": len(cycles) if cycles else 0,
            "reliable_cycles_count": 0,
            "total_wellness_logs": total_logs,
            "patterns": [],
            "insufficient_data_reasons": [
                "No cycle or wellness log history recorded yet. Log daily entries across multiple cycles to build personalized patterns."
            ]
        }

    # Assign logs to cycle structures
    cycle_structures = assign_logs_to_cycles(cycles, wellness_logs)
    reliable_cycles = [c for c in cycle_structures if c["is_reliable"]]
    unreliable_cycles = [c for c in cycle_structures if not c["is_reliable"]]

    # Guardrail 2: Unreliable cycle windows (e.g. all cycles are unclarified gaps)
    if len(reliable_cycles) < 1 and unreliable_cycles:
        return {
            "status": "unreliable_history",
            "cycles_evaluated_count": len(cycle_structures),
            "reliable_cycles_count": 0,
            "total_wellness_logs": total_logs,
            "patterns": [],
            "insufficient_data_reasons": [
                "Cycle windows cannot be reliably determined due to unclarified tracking gaps (>45 days). Clarifying your cycle intervals will enable pattern detection."
            ]
        }

    # Tag each log with its window within its assigned cycle
    for c in cycle_structures:
        window_grouped = {
            "menstrual": [],
            "follicular": [],
            "mid_cycle": [],
            "premenstrual": [],
            "other": []
        }
        for log in c["logs"]:
            w_info = classify_log_phase_window(log, c, premenstrual_days=premenstrual_days)
            log_copy = dict(log)
            log_copy["_window_info"] = w_info
            window_grouped[w_info["window"]].append(log_copy)
        c["window_logs"] = window_grouped

    patterns: List[Dict[str, Any]] = []

    # ---------------------------------------------------------
    # Pattern 1: Premenstrual Lower Energy / Fatigue
    # ---------------------------------------------------------
    p1 = _evaluate_cross_cycle_pattern(
        cycle_structures=reliable_cycles,
        target_window="premenstrual",
        metric_type="lower_energy",
        pattern_id="premenstrual_lower_energy",
        title="Lower Energy Before Period",
        window_label=f"Premenstrual days (Days before period)",
        is_window_estimated=True,
        min_cycles=min_cycles,
        min_days=min_days,
        min_ratio=min_ratio,
        description_template="In {recurrence_count} of your last {evaluated_cycles} logged cycles, you reported lower energy during the days before your period.",
        recommendation="Gentle, restorative routines or early bedtimes may feel supportive during these days."
    )
    patterns.append(p1)

    # ---------------------------------------------------------
    # Pattern 2: Early Menstrual Cramps / Discomfort
    # ---------------------------------------------------------
    p2 = _evaluate_cross_cycle_pattern(
        cycle_structures=reliable_cycles,
        target_window="menstrual",
        metric_type="cramps_pain",
        pattern_id="menstrual_cramps",
        title="Menstrual Discomfort Pattern",
        window_label="Menstrual days (Days 1–5)",
        is_window_estimated=False,
        min_cycles=min_cycles,
        min_days=min_days,
        min_ratio=min_ratio,
        description_template="In {recurrence_count} of your last {evaluated_cycles} recorded cycles, you logged cramps during the early days of your period.",
        recommendation="Heat relief, gentle stretching, and staying hydrated can provide comfort during early cycle days."
    )
    patterns.append(p2)

    # ---------------------------------------------------------
    # Pattern 3: Premenstrual Emotional Shifts
    # ---------------------------------------------------------
    p3 = _evaluate_cross_cycle_pattern(
        cycle_structures=reliable_cycles,
        target_window="premenstrual",
        metric_type="emotional_sensitivity",
        pattern_id="premenstrual_emotional_shifts",
        title="Emotional Shifts Before Period",
        window_label=f"Premenstrual days (Days before period)",
        is_window_estimated=True,
        min_cycles=min_cycles,
        min_days=min_days,
        min_ratio=min_ratio,
        description_template="In {recurrence_count} of your last {evaluated_cycles} logged cycles, you noted heightened emotional sensitivity or mood changes in the days leading up to your period.",
        recommendation="Allowing space for quiet downtime and journaling can be a gentle way to honor emotional shifts."
    )
    patterns.append(p3)

    # ---------------------------------------------------------
    # Pattern 4: Premenstrual Sleep Disruption (<6.5 hrs)
    # ---------------------------------------------------------
    p4 = _evaluate_cross_cycle_pattern(
        cycle_structures=reliable_cycles,
        target_window="premenstrual",
        metric_type="sleep_disruption",
        pattern_id="premenstrual_sleep_disruption",
        title="Lighter Sleep Before Period",
        window_label=f"Premenstrual days (Days before period)",
        is_window_estimated=True,
        min_cycles=min_cycles,
        min_days=min_days,
        min_ratio=min_ratio,
        description_template="In {recurrence_count} of your last {evaluated_cycles} recorded cycles, you logged shorter sleep duration in the days before your period.",
        recommendation="A calming evening wind-down or reducing screen light before bed may encourage deeper rest."
    )
    patterns.append(p4)

    # ---------------------------------------------------------
    # Pattern 5: High Stress Sleep Correlation (Overall)
    # ---------------------------------------------------------
    p5 = _evaluate_stress_sleep_correlation(wellness_logs)
    if p5:
        patterns.append(p5)

    # Check overall status
    has_supported = any(p["evidence_status"] == "supported" for p in patterns)
    status = "ready" if has_supported else "insufficient_data"

    insufficient_reasons = []
    if not has_supported:
        insufficient_reasons.append(
            f"Logged data does not yet meet the {min_cycles}-cycle and {min_days}-day threshold for recurring patterns. Continue daily logging to unlock personal insights."
        )

    return {
        "status": status,
        "cycles_evaluated_count": len(cycle_structures),
        "reliable_cycles_count": len(reliable_cycles),
        "total_wellness_logs": total_logs,
        "patterns": patterns,
        "insufficient_data_reasons": insufficient_reasons
    }


def _evaluate_cross_cycle_pattern(
    cycle_structures: List[Dict[str, Any]],
    target_window: str,
    metric_type: str,
    pattern_id: str,
    title: str,
    window_label: str,
    is_window_estimated: bool,
    min_cycles: int,
    min_days: int,
    min_ratio: float,
    description_template: str,
    recommendation: str
) -> Dict[str, Any]:
    """
    Evaluates cross-cycle recurrence for a specific metric in a target window.
    Strictly calculates observation denominators and transparent evidence metrics.
    """
    cycles_with_data = 0
    cycles_with_pattern = 0
    total_logged_days_in_window = 0
    total_positive_days_in_window = 0

    for c in cycle_structures:
        window_logs = c.get("window_logs", {}).get(target_window, [])
        has_occ, valid_logs, pos_count = evaluate_cycle_window_metric(window_logs, metric_type)

        if valid_logs > 0:
            cycles_with_data += 1
            total_logged_days_in_window += valid_logs
            total_positive_days_in_window += pos_count
            if has_occ:
                cycles_with_pattern += 1

    # Ratio calculation
    ratio = (cycles_with_pattern / cycles_with_data) if cycles_with_data > 0 else 0.0
    percentage = round(ratio * 100.0, 1)

    # Determine evidence status
    evidence_status = "insufficient_data"
    status_reason = None
    is_recurring = False

    if cycles_with_data < min_cycles:
        evidence_status = "insufficient_data"
        status_reason = (
            f"Recorded in {cycles_with_data} cycle(s). At least {min_cycles} distinct cycles with "
            f"logged entries in this window are required to confirm a recurring pattern."
        )
    elif total_logged_days_in_window < min_days:
        evidence_status = "insufficient_data"
        status_reason = (
            f"Logged on {total_logged_days_in_window} day(s). At least {min_days} logged days in "
            f"this window across cycles are required to assess consistency."
        )
    elif ratio >= min_ratio:
        evidence_status = "supported"
        is_recurring = True
        status_reason = None
    else:
        evidence_status = "non_recurring"
        status_reason = (
            f"Observed in {cycles_with_pattern} of {cycles_with_data} cycles ({percentage}%); "
            f"does not meet the {int(min_ratio * 100)}% threshold for a recurring pattern."
        )

    # Generate description
    if evidence_status == "supported":
        desc = description_template.format(
            recurrence_count=cycles_with_pattern,
            evaluated_cycles=cycles_with_data,
            total_days=total_logged_days_in_window
        )
    elif evidence_status == "non_recurring":
        desc = f"Reported during {cycles_with_pattern} of {cycles_with_data} logged cycles. Does not represent a consistent recurring pattern."
    else:
        desc = f"Not enough logged history in this window to evaluate recurrence."

    return {
        "pattern_id": pattern_id,
        "title": title,
        "metric": metric_type,
        "target_window": target_window,
        "window_label": window_label,
        "is_window_estimated": is_window_estimated,
        "description": desc,
        "evidence_status": evidence_status,
        "status_reason": status_reason,
        "is_recurring": is_recurring,
        "cycles_observed": cycles_with_pattern,
        "total_cycles_evaluated": cycles_with_data,
        "relevant_logged_days": total_logged_days_in_window,
        "positive_observation_days": total_positive_days_in_window,
        "recurrence_count": cycles_with_pattern,
        "recurrence_denominator": cycles_with_data,
        "recurrence_percentage": percentage,
        "recommendation": recommendation if is_recurring else None
    }


def _evaluate_stress_sleep_correlation(wellness_logs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Evaluates the relationship between user-reported high stress and sleep hours
    across all available logs.
    """
    if not wellness_logs:
        return None

    high_stress_sleep = []
    normal_stress_sleep = []

    for log in wellness_logs:
        stress = log.get("stress")
        sleep = log.get("sleep_hours")
        if stress is None or sleep is None:
            continue

        try:
            val = float(sleep)
            if stress == "High":
                high_stress_sleep.append(val)
            elif stress in ("Low", "Medium"):
                normal_stress_sleep.append(val)
        except (ValueError, TypeError):
            continue

    total_logs = len(high_stress_sleep) + len(normal_stress_sleep)
    if len(high_stress_sleep) < 2 or len(normal_stress_sleep) < 2:
        return {
            "pattern_id": "stress_sleep_correlation",
            "title": "Stress & Sleep Relationship",
            "metric": "sleep_stress",
            "target_window": "overall",
            "window_label": "Overall tracking logs",
            "is_window_estimated": False,
            "description": "Not enough stress and sleep logs to evaluate correlation.",
            "evidence_status": "insufficient_data",
            "status_reason": "Requires at least 2 high-stress logs and 2 lower-stress logs.",
            "is_recurring": False,
            "cycles_observed": 0,
            "total_cycles_evaluated": 0,
            "relevant_logged_days": total_logs,
            "positive_observation_days": len(high_stress_sleep),
            "recurrence_count": 0,
            "recurrence_denominator": 0,
            "recurrence_percentage": 0.0,
            "recommendation": None
        }

    high_avg = sum(high_stress_sleep) / len(high_stress_sleep)
    normal_avg = sum(normal_stress_sleep) / len(normal_stress_sleep)
    diff = normal_avg - high_avg

    is_supported = (diff >= 0.8 and high_avg < 7.0)

    if is_supported:
        desc = (
            f"On days with high stress, your average sleep was {round(high_avg, 1)} hrs, "
            f"compared to {round(normal_avg, 1)} hrs on lower-stress days ({total_logs} logs analyzed)."
        )
        return {
            "pattern_id": "stress_sleep_correlation",
            "title": "Stress & Sleep Relationship",
            "metric": "sleep_stress",
            "target_window": "overall",
            "window_label": "Overall tracking logs",
            "is_window_estimated": False,
            "description": desc,
            "evidence_status": "supported",
            "status_reason": None,
            "is_recurring": True,
            "cycles_observed": 0,
            "total_cycles_evaluated": 0,
            "relevant_logged_days": total_logs,
            "positive_observation_days": len(high_stress_sleep),
            "recurrence_count": len(high_stress_sleep),
            "recurrence_denominator": total_logs,
            "recurrence_percentage": round((len(high_stress_sleep) / total_logs) * 100.0, 1),
            "recommendation": "Brief evening wind-downs, reducing evening screen light, or reading before bed may help ease evening tension."
        }
    else:
        return {
            "pattern_id": "stress_sleep_correlation",
            "title": "Stress & Sleep Relationship",
            "metric": "sleep_stress",
            "target_window": "overall",
            "window_label": "Overall tracking logs",
            "is_window_estimated": False,
            "description": f"No strong correlation between high stress and shortened sleep duration in your logs (difference: {round(abs(diff), 1)} hrs).",
            "evidence_status": "non_recurring",
            "status_reason": "Sleep duration was not substantially lower on high stress days.",
            "is_recurring": False,
            "cycles_observed": 0,
            "total_cycles_evaluated": 0,
            "relevant_logged_days": total_logs,
            "positive_observation_days": len(high_stress_sleep),
            "recurrence_count": 0,
            "recurrence_denominator": total_logs,
            "recurrence_percentage": 0.0,
            "recommendation": None
        }


def get_user_wellbeing_insights(user_id: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Database-backed helper that queries cycles and wellness logs for the authenticated user_id
    and evaluates wellbeing patterns using strictly isolated parameterized SQL.
    """
    if not user_id:
        return {
            "status": "insufficient_data",
            "cycles_evaluated_count": 0,
            "reliable_cycles_count": 0,
            "total_wellness_logs": 0,
            "patterns": [],
            "insufficient_data_reasons": ["User ID not specified"]
        }

    # Fetch user's cycles ordered chronologically ascending
    cycles = execute_query(
        """
        SELECT cycle_id, user_id, start_date, end_date, cycle_length, period_length, irregular, gap_type
        FROM cycles
        WHERE user_id = :user_id
        ORDER BY start_date ASC
        """,
        {"user_id": user_id}
    )

    # Fetch user's wellness logs ordered chronologically ascending
    wellness_logs = execute_query(
        """
        SELECT log_id, user_id, date, cycle_day, mood, stress, sleep_hours, cramps, fatigue, flow, energy_level
        FROM wellness_logs
        WHERE user_id = :user_id
        ORDER BY date ASC
        """,
        {"user_id": user_id}
    )

    return analyze_user_wellbeing_patterns(cycles, wellness_logs, config=config)
