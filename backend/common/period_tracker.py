"""
Menstrual Cycle Tracking and Period Prediction Module for OvaCare AI.

Contains pure calculation helpers and database recalculation routines for:
- Calculating intervals between consecutive period start dates
- Chronologically recalculating cycle lengths, tracking gaps, and irregularity status
- Validating cycle dates and preventing duplicate start dates
- Evaluating cycle gaps ('unclarified_gap', 'missed_period', 'confirmed_long_cycle')
- Calculating next-period predictions and communicating tracking uncertainty
- Consistent metrics computation for analytics and daily wellness phase context
"""

import os
import sys
import uuid
from datetime import datetime, date, timedelta
import numpy as np

# Ensure backend root directory is on sys.path if imported in non-standard context
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.abspath(os.path.join(_CURRENT_DIR, ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from db import execute_query, execute_write

# Clinical and operational thresholds
VALID_GAP_CLARIFICATIONS = {
    'missed_period',
    'confirmed_long_cycle',
    'unclarified_gap',
    'forgotten_entry',
    'forgot_to_log',
    'missed_entry',
    'forgotten_log'
}
CANONICAL_GAP_TYPES = {
    'missed_period',
    'confirmed_long_cycle',
    'unclarified_gap',
    'forgotten_entry'
}
PHYSIOLOGICAL_CYCLE_MIN = 21
PHYSIOLOGICAL_CYCLE_MAX = 45
NORMAL_VARIATION_THRESHOLD = 7
STANDARD_CYCLE_BASELINE = 28
STANDARD_PERIOD_BASELINE = 5


def normalize_gap_clarification(gap_str):
    """
    Normalizes user-supplied gap clarification strings to canonical identifiers.
    """
    if not gap_str:
        return None
    g = str(gap_str).strip().lower()
    if g in ('forgot_to_log', 'missed_entry', 'forgotten_log', 'forgotten_entry'):
        return 'forgotten_entry'
    if g in ('missed_period', 'confirmed_long_cycle', 'unclarified_gap'):
        return g
    return None


def calculate_intervals(start_dates):
    """
    Pure calculation helper: returns list of intervals (in days) between
    consecutive sorted start dates.
    
    Example:
      [date(2026, 8, 10), date(2026, 9, 9), date(2026, 10, 24)] -> [30, 45]
    """
    if not start_dates or len(start_dates) < 2:
        return []
    
    parsed = []
    for d in start_dates:
        if isinstance(d, (datetime, date)):
            parsed.append(d if isinstance(d, date) else d.date())
        elif isinstance(d, str):
            parsed.append(datetime.strptime(d[:10], "%Y-%m-%d").date())
            
    parsed.sort()
    return [(parsed[i + 1] - parsed[i]).days for i in range(len(parsed) - 1)]


def validate_cycle_inputs(start_date_str, end_date_str=None, user_id=None):
    """
    Validates cycle date inputs and checks for duplicate start dates for user_id.
    
    Returns:
      (start_date, end_date, error_message, status_code)
      If valid: (start_date, end_date, None, None)
    """
    if not start_date_str:
        return None, None, "Missing required field: start_date", 400
        
    start_str = str(start_date_str).strip()
    end_str = str(end_date_str).strip() if end_date_str else None
    
    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else None
    except ValueError:
        return None, None, "Dates must be in YYYY-MM-DD format", 400
        
    if end_date and end_date < start_date:
        return None, None, "End date cannot be earlier than start date", 400
        
    if user_id:
        existing = execute_query(
            "SELECT cycle_id FROM cycles WHERE user_id = :user_id AND start_date = :start_date",
            {"user_id": user_id, "start_date": start_str}
        )
        if existing:
            return None, None, "A cycle record with this start date already exists", 409
            
    return start_date, end_date, None, None


def recalculate_user_cycles(user_id):
    """
    Recalculates cycle_length, gap_type, and irregular status for all cycles
    belonging to user_id in chronological order (start_date ASC).
    
    Ensures:
    1. Historical insertions or deletions correctly recalculate preceding, current, and subsequent cycles.
    2. Intervals > 45 days are identified as tracking gaps ('unclarified_gap', 'missed_period', 'forgotten_entry')
       and are NOT automatically classified as irregular cycles unless explicitly confirmed ('confirmed_long_cycle').
    3. Physiological cycles (21-45 days) are evaluated for irregularity based on deviation from personal baseline.
    4. The most recent recorded cycle has cycle_length = None (ongoing cycle).
    """
    cycles = execute_query(
        "SELECT cycle_id, start_date, gap_type FROM cycles WHERE user_id = :user_id ORDER BY start_date ASC",
        {"user_id": user_id}
    )
    if not cycles:
        return

    n = len(cycles)
    
    # First pass: collect physiological intervals (<= 45 days) to compute personal baseline
    intervals = []
    for i in range(n - 1):
        d1 = datetime.strptime(str(cycles[i]['start_date'])[:10], "%Y-%m-%d").date()
        d2 = datetime.strptime(str(cycles[i+1]['start_date'])[:10], "%Y-%m-%d").date()
        length = (d2 - d1).days
        gap = normalize_gap_clarification(cycles[i].get('gap_type'))
        if length <= PHYSIOLOGICAL_CYCLE_MAX and gap not in ('missed_period', 'forgotten_entry'):
            intervals.append(length)

    avg_baseline = round(sum(intervals) / len(intervals)) if intervals else STANDARD_CYCLE_BASELINE

    for i in range(n):
        cycle_id = cycles[i]['cycle_id']
        current_gap = normalize_gap_clarification(cycles[i].get('gap_type'))
        
        if i == n - 1:
            # Latest cycle is ongoing; cycle_length is None until next cycle is recorded
            execute_write(
                "UPDATE cycles SET cycle_length = NULL, irregular = FALSE, gap_type = NULL WHERE cycle_id = :cid",
                {"cid": cycle_id}
            )
        else:
            d1 = datetime.strptime(str(cycles[i]['start_date'])[:10], "%Y-%m-%d").date()
            d2 = datetime.strptime(str(cycles[i+1]['start_date'])[:10], "%Y-%m-%d").date()
            cycle_length = (d2 - d1).days
            
            irregular = False
            gap_type = current_gap

            if cycle_length > PHYSIOLOGICAL_CYCLE_MAX:
                # Long interval: distinguish unclarified tracking gap from confirmed options
                if current_gap == 'confirmed_long_cycle':
                    gap_type = 'confirmed_long_cycle'
                    irregular = True
                elif current_gap == 'missed_period':
                    gap_type = 'missed_period'
                    irregular = False
                elif current_gap == 'forgotten_entry':
                    gap_type = 'forgotten_entry'
                    irregular = False
                else:
                    gap_type = 'unclarified_gap'
                    irregular = False
            else:
                # Physiological cycle length (<= 45 days)
                if current_gap in ('confirmed_long_cycle', 'missed_period', 'forgotten_entry'):
                    gap_type = current_gap
                else:
                    gap_type = None

                # Mark irregular if outside standard physiological window or deviates > threshold from user baseline
                if (cycle_length < PHYSIOLOGICAL_CYCLE_MIN or 
                    cycle_length > 38 or 
                    abs(cycle_length - avg_baseline) > NORMAL_VARIATION_THRESHOLD):
                    irregular = True

            execute_write(
                """
                UPDATE cycles 
                SET cycle_length = :cycle_length, irregular = :irregular, gap_type = :gap_type 
                WHERE cycle_id = :cid
                """,
                {
                    "cycle_length": cycle_length,
                    "irregular": irregular,
                    "gap_type": gap_type,
                    "cid": cycle_id
                }
            )


def log_cycle(user_id, start_date_str, end_date_str=None, gap_clarification=None):
    """
    Validates and persists a new cycle event for user_id, managing gap clarification
    and triggering chronological recalculation.
    
    Returns:
      (cycle_id, error_message, status_code)
      On success: (cycle_id, None, 201)
      On error: (None, error_message, error_code)
    """
    start_date, end_date, err, code = validate_cycle_inputs(start_date_str, end_date_str, user_id=user_id)
    if err:
        return None, err, code

    norm_clarification = normalize_gap_clarification(gap_clarification) if gap_clarification else None
    if gap_clarification and not norm_clarification:
        return None, "Invalid gap_clarification option", 400

    period_length = (end_date - start_date).days if end_date else None
    cycle_id = f"cyc_{uuid.uuid4().hex[:12]}"
    start_str = start_date.isoformat()
    end_str = end_date.isoformat() if end_date else None

    try:
        # If gap_clarification was provided for the interval preceding this cycle, attach to prev cycle
        if norm_clarification:
            prev = execute_query(
                "SELECT cycle_id FROM cycles WHERE user_id = :uid AND start_date < :start ORDER BY start_date DESC LIMIT 1",
                {"uid": user_id, "start": start_str}
            )
            if prev:
                execute_write(
                    "UPDATE cycles SET gap_type = :gap WHERE cycle_id = :cid",
                    {"gap": norm_clarification, "cid": prev[0]['cycle_id']}
                )

        execute_write(
            """
            INSERT INTO cycles (cycle_id, user_id, start_date, end_date, cycle_length, period_length, irregular, gap_type)
            VALUES (:cycle_id, :user_id, :start_date, :end_date, NULL, :period_length, FALSE, :gap_type)
            """,
            {
                "cycle_id": cycle_id,
                "user_id": user_id,
                "start_date": start_str,
                "end_date": end_str,
                "period_length": period_length,
                "gap_type": norm_clarification
            }
        )
        
        recalculate_user_cycles(user_id)
        return cycle_id, None, 201
    except Exception as e:
        return None, "Failed to log cycle record", 500


def update_cycle_clarification(user_id, cycle_id, gap_clarification):
    """
    Updates the gap_type classification of an existing cycle owned by user_id
    and recalculates all cycle intervals.
    
    Valid options:
      - 'missed_period': User experienced an anovulatory/missed period
      - 'confirmed_long_cycle': User confirms a genuine single long cycle
      - 'forgotten_entry' (or 'forgot_to_log'): User forgot to log an intermediate period
      - 'unclarified_gap': Reset to unclarified gap
      
    Returns:
      (success, message, status_code)
    """
    norm_clarification = normalize_gap_clarification(gap_clarification)
    if not norm_clarification:
        return False, "Invalid gap_clarification option. Valid choices: 'missed_period', 'confirmed_long_cycle', 'forgotten_entry', 'unclarified_gap'", 400

    try:
        cycle = execute_query(
            "SELECT user_id, start_date, cycle_length FROM cycles WHERE cycle_id = :cycle_id",
            {"cycle_id": cycle_id}
        )
        if not cycle:
            return False, "Cycle not found", 404
        if cycle[0]['user_id'] != user_id:
            return False, "Forbidden: Cannot update cycle records belonging to another user", 403

        execute_write(
            "UPDATE cycles SET gap_type = :gap WHERE cycle_id = :cid AND user_id = :uid",
            {"gap": norm_clarification, "cid": cycle_id, "uid": user_id}
        )
        recalculate_user_cycles(user_id)
        return True, "Cycle gap classification updated successfully", 200
    except Exception:
        return False, "Failed to update cycle gap classification", 500


def delete_user_cycle(user_id, cycle_id):
    """
    Safely deletes a cycle record after verifying user ownership,
    and recalculates remaining cycles.
    
    Returns:
      (success, message, status_code)
    """
    try:
        cycle = execute_query("SELECT user_id FROM cycles WHERE cycle_id = :cycle_id", {"cycle_id": cycle_id})
        if not cycle:
            return False, "Cycle not found", 404
        if cycle[0]['user_id'] != user_id:
            return False, "Forbidden: Cannot delete records belonging to another user", 403
            
        execute_write(
            "DELETE FROM cycles WHERE cycle_id = :cycle_id AND user_id = :user_id",
            {"cycle_id": cycle_id, "user_id": user_id}
        )
        
        recalculate_user_cycles(user_id)
        return True, "Cycle deleted successfully", 200
    except Exception:
        return False, "Failed to delete cycle record", 500


def calculate_period_prediction(cycles, has_pcos=False):
    """
    Adaptive calculation routine for menstrual prediction, tracking status,
    and explainable uncertainty representation.
    
    Accepts:
      cycles: list of cycle dictionaries (with start_date, cycle_length, period_length, irregular, gap_type)
      has_pcos: boolean indicating whether user has PCOS mode enabled
      
    Returns dictionary with prediction and explainability fields.
    """
    if not cycles:
        baseline_date = (datetime.now() + timedelta(days=10)).date().isoformat()
        return {
            "predicted_date": baseline_date,
            "average_cycle_length": STANDARD_CYCLE_BASELINE,
            "average_period_length": STANDARD_PERIOD_BASELINE,
            "irregular": False,
            "history_count": 0,
            "delayed_days": 0,
            "tracking_status": "insufficient_history",
            "has_unclarified_gap": False,
            "pcos_mode": bool(has_pcos),
            "pcos_aware_tracking": bool(has_pcos),
            "tracking_mode": "PCOS-Aware Tracking" if bool(has_pcos) else "Standard Tracking",
            "message": "Not enough cycle history. Providing baseline prediction.",
            "history_quality": "insufficient",
            "history_quality_description": "No recorded cycle history.",
            "prediction_confidence": "low",
            "confidence_reason": "Using standard population baseline (28 days). Prediction confidence will increase once completed cycles are recorded.",
            "is_personalized": False,
            "can_classify_regularity": False,
            "regularity_assessment": "insufficient_data",
            "regularity_message": "Insufficient cycle history to classify regularity (minimum 2 completed cycle intervals required).",
            "usable_intervals": [],
            "supporting_cycle_lengths": [],
            "excluded_intervals": [],
            "cycle_length_std_dev": None,
            "has_unresolved_gaps": False,
            "clarification_prompt": None
        }

    # Ensure cycles are ordered by start_date DESC
    sorted_cycles = sorted(
        cycles, 
        key=lambda c: str(c['start_date'])[:10], 
        reverse=True
    )
    
    period_lengths = [c['period_length'] for c in sorted_cycles if c.get('period_length') is not None]
    avg_period = round(sum(period_lengths) / len(period_lengths)) if period_lengths else STANDARD_PERIOD_BASELINE

    usable_intervals = []
    excluded_intervals = []
    has_unclarified_gap = False
    has_confirmed_long_cycle = False
    unclarified_count = 0

    for c in sorted_cycles:
        c_len = c.get('cycle_length')
        if c_len is None:
            continue
        g_type = normalize_gap_clarification(c.get('gap_type'))
        cid = c.get('cycle_id')
        s_date = str(c.get('start_date'))[:10]

        if g_type == 'confirmed_long_cycle':
            has_confirmed_long_cycle = True
            usable_intervals.append(c_len)
        elif g_type == 'missed_period':
            excluded_intervals.append({
                "cycle_id": cid,
                "start_date": s_date,
                "interval_days": c_len,
                "gap_type": "missed_period",
                "reason": "User-confirmed missed menstrual period. Excluded from normal cycle average.",
                "requires_clarification": False
            })
        elif g_type == 'forgotten_entry':
            excluded_intervals.append({
                "cycle_id": cid,
                "start_date": s_date,
                "interval_days": c_len,
                "gap_type": "forgotten_entry",
                "reason": "User-confirmed unlogged/forgotten period. Excluded from normal cycle average.",
                "requires_clarification": False
            })
        elif g_type == 'unclarified_gap' or c_len > PHYSIOLOGICAL_CYCLE_MAX:
            has_unclarified_gap = True
            unclarified_count += 1
            excluded_intervals.append({
                "cycle_id": cid,
                "start_date": s_date,
                "interval_days": c_len,
                "gap_type": "unclarified_gap",
                "reason": f"Unexplained tracking gap of {c_len} days. Excluded from normal cycle average until clarified.",
                "requires_clarification": True
            })
        else:
            usable_intervals.append(c_len)

    # Determine average cycle length without distortion from unconfirmed gaps
    physiological_lengths = [l for l in usable_intervals if l <= PHYSIOLOGICAL_CYCLE_MAX]
    if physiological_lengths:
        avg_cycle = round(sum(physiological_lengths) / len(physiological_lengths))
    elif usable_intervals:
        avg_cycle = round(sum(usable_intervals) / len(usable_intervals))
    else:
        avg_cycle = STANDARD_CYCLE_BASELINE

    last_start = datetime.strptime(str(sorted_cycles[0]['start_date'])[:10], "%Y-%m-%d").date()
    predicted_date = last_start + timedelta(days=avg_cycle)

    # Regularity classification rules
    is_irregular = False
    can_classify_regularity = False
    regularity_assessment = "insufficient_data"
    regularity_message = "Insufficient cycle history to classify regularity (minimum 2 completed cycle intervals required)."

    if has_confirmed_long_cycle:
        can_classify_regularity = True
        regularity_assessment = "irregular"
        is_irregular = True
        regularity_message = "Your recorded cycle history shows irregular intervals. There can be several reasons for this. If the pattern continues or concerns you, consider discussing it with a qualified healthcare professional."
    elif len(usable_intervals) < 2:
        can_classify_regularity = False
        regularity_assessment = "insufficient_data"
        is_irregular = False
    else:
        std_dev = float(np.std(usable_intervals))
        max_diff = max(usable_intervals) - min(usable_intervals)
        if std_dev > 4.0 or max_diff > NORMAL_VARIATION_THRESHOLD:
            can_classify_regularity = True
            regularity_assessment = "irregular"
            is_irregular = True
            regularity_message = "Your recorded cycle history shows irregular intervals. There can be several reasons for this. If the pattern continues or concerns you, consider discussing it with a qualified healthcare professional."
        else:
            can_classify_regularity = True
            regularity_assessment = "regular"
            is_irregular = False
            regularity_message = f"Recorded cycles are consistent (average {avg_cycle} days with <= {NORMAL_VARIATION_THRESHOLD} days variation)."

    # History Quality determination
    if len(sorted_cycles) <= 1:
        history_quality = "insufficient"
        if len(sorted_cycles) == 1:
            history_quality_description = "1 recorded cycle. Completed interval requires next cycle start date."
        else:
            history_quality_description = "No recorded cycle history."
    elif has_unclarified_gap:
        history_quality = "needs_clarification"
        history_quality_description = f"{len(usable_intervals)} usable cycle(s) recorded, with {unclarified_count} unexplained interval(s) requiring clarification."
    elif len(usable_intervals) == 0:
        history_quality = "insufficient"
        history_quality_description = "Recorded cycles contain only gaps or unconfirmed intervals; no usable cycle lengths."
    elif len(usable_intervals) == 1:
        history_quality = "limited"
        history_quality_description = "1 completed cycle interval recorded. Additional intervals improve personal variance analysis."
    elif len(usable_intervals) >= 3:
        history_quality = "established"
        history_quality_description = f"{len(usable_intervals)} consistent cycle intervals recorded."
    else:
        history_quality = "adequate"
        history_quality_description = f"{len(usable_intervals)} cycle intervals recorded."

    # Prediction Confidence & Uncertainty
    if len(usable_intervals) == 0:
        prediction_confidence = "low"
        is_personalized = False
        confidence_reason = "Using standard population baseline (28 days). Prediction confidence will increase once completed cycles are recorded."
    elif len(usable_intervals) == 1:
        prediction_confidence = "moderate"
        is_personalized = True
        confidence_reason = f"Based on a single recorded cycle interval ({usable_intervals[0]} days). Confidence increases with 3 or more logged cycles."
    elif has_unclarified_gap:
        prediction_confidence = "moderate"
        is_personalized = True
        confidence_reason = f"Prediction calculated from {len(usable_intervals)} regular cycles, but an unclarified tracking gap is present."
    elif is_irregular:
        prediction_confidence = "uncertain"
        is_personalized = True
        confidence_reason = f"Cycle lengths show natural irregularity (variation of {max(usable_intervals) - min(usable_intervals)} days); period arrival window may vary."
    else:
        prediction_confidence = "high"
        is_personalized = True
        confidence_reason = f"Based on {len(usable_intervals)} consistent recorded cycle intervals with low variance."

    today = datetime.now().date()
    delayed_days = 0
    if today > predicted_date:
        delayed_days = (today - predicted_date).days

    # Tracking completeness status & message
    if len(sorted_cycles) < 2 or not usable_intervals:
        tracking_status = "insufficient_history"
        msg = f"Baseline prediction: next period estimated around {predicted_date.strftime('%B %d, %Y')}."
    elif has_unclarified_gap:
        tracking_status = "needs_clarification"
        msg = f"Tracking gap detected. Prediction estimated around {predicted_date.strftime('%B %d, %Y')} based on regular cycle history."
    else:
        tracking_status = "complete"
        msg = f"Your next period is predicted to start on {predicted_date.strftime('%B %d, %Y')}"

    clarification_prompt = (
        "One or more intervals between recorded cycles exceed 45 days. You can clarify whether this was a forgotten log, a missed period, or a longer cycle."
        if has_unclarified_gap else None
    )

    return {
        "predicted_date": predicted_date.isoformat(),
        "average_cycle_length": avg_cycle,
        "average_period_length": avg_period,
        "irregular": is_irregular,
        "history_count": len(sorted_cycles),
        "delayed_days": delayed_days,
        "tracking_status": tracking_status,
        "has_unclarified_gap": has_unclarified_gap,
        "pcos_mode": bool(has_pcos),
        "pcos_aware_tracking": bool(has_pcos),
        "tracking_mode": "PCOS-Aware Tracking" if bool(has_pcos) else "Standard Tracking",
        "message": msg,
        "history_quality": history_quality,
        "history_quality_description": history_quality_description,
        "prediction_confidence": prediction_confidence,
        "confidence_reason": confidence_reason,
        "is_personalized": is_personalized,
        "can_classify_regularity": can_classify_regularity,
        "regularity_assessment": regularity_assessment,
        "regularity_message": regularity_message,
        "usable_intervals": usable_intervals,
        "supporting_cycle_lengths": usable_intervals,
        "excluded_intervals": excluded_intervals,
        "cycle_length_std_dev": round(float(np.std(usable_intervals)), 1) if len(usable_intervals) >= 2 else None,
        "has_unresolved_gaps": has_unclarified_gap,
        "clarification_prompt": clarification_prompt
    }


def calculate_cycle_analytics_metrics(cycles_db):
    """
    Computes average cycle length, average period length, and irregular count
    for analytics reporting, guaranteeing consistency with period prediction rules.
    """
    valid_cycle_lengths = [
        c['cycle_length'] for c in cycles_db 
        if c['cycle_length'] is not None 
        and normalize_gap_clarification(c.get('gap_type')) not in ('unclarified_gap', 'missed_period', 'forgotten_entry') 
        and (c['cycle_length'] <= PHYSIOLOGICAL_CYCLE_MAX or normalize_gap_clarification(c.get('gap_type')) == 'confirmed_long_cycle')
    ]
    physiological_lengths = [l for l in valid_cycle_lengths if l <= PHYSIOLOGICAL_CYCLE_MAX]
    if physiological_lengths:
        avg_cycle = round(sum(physiological_lengths) / len(physiological_lengths), 1)
    elif valid_cycle_lengths:
        avg_cycle = round(sum(valid_cycle_lengths) / len(valid_cycle_lengths), 1)
    else:
        avg_cycle = float(STANDARD_CYCLE_BASELINE)

    period_lengths = [c['period_length'] for c in cycles_db if c.get('period_length') is not None]
    avg_period = round(sum(period_lengths) / len(period_lengths), 1) if period_lengths else float(STANDARD_PERIOD_BASELINE)
    irregular_count = sum(1 for c in cycles_db if c.get('irregular'))

    return {
        "average_cycle_length": avg_cycle,
        "average_period_length": avg_period,
        "irregular_cycles_count": irregular_count
    }


def get_user_typical_cycle_lengths(user_id):
    """
    Helper for wellness logs cycle-phase calculation.
    Returns (avg_cycle, avg_period) excluding tracking gaps.
    """
    user_cycles = execute_query(
        "SELECT cycle_length, period_length, gap_type FROM cycles WHERE user_id = :user_id",
        {"user_id": user_id}
    )
    cycle_lengths = [
        c['cycle_length'] for c in user_cycles 
        if c.get('cycle_length') is not None 
        and c.get('cycle_length') <= PHYSIOLOGICAL_CYCLE_MAX 
        and normalize_gap_clarification(c.get('gap_type')) not in ('missed_period', 'forgotten_entry', 'unclarified_gap')
    ]
    period_lengths = [c['period_length'] for c in user_cycles if c.get('period_length') is not None]
    
    avg_cycle = round(sum(cycle_lengths) / len(cycle_lengths)) if cycle_lengths else STANDARD_CYCLE_BASELINE
    avg_period = round(sum(period_lengths) / len(period_lengths)) if period_lengths else STANDARD_PERIOD_BASELINE
    return avg_cycle, avg_period

