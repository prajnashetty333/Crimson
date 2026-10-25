"""
Dedicated Repeatable Demo Seeder for OvaCare AI.

Creates a dedicated, fully populated synthetic demo patient account (Maya Demo)
with realistic, internally consistent menstrual health data demonstrating all
currently implemented patient-facing features:
- 6-month coherent cycle timeline with realistic physiological intervals
- High-confidence period prediction and cycle regularity assessment
- Rich physical & emotional wellbeing tracking history (explicit 'None' vs NULL)
- Deterministic pattern detection (lower premenstrual energy, cramps, stress-sleep correlation)
- Non-recurring pattern guardrails (premenstrual emotional shifts at 20% recurrence)
- Unified My Health Report generation (Category 1, 2, and 3 data segregation)
- Dedicated cycle-gap demonstration account (Jordan Gap Demo)

Safety Guardrails:
- Strictly isolates writes to ovacare_demo.db (or explicitly designated demo DB).
- Refuses to run if resolved to protected production database (backend/ovacare.db).
- Idempotent and transactional: multiple runs cleanly refresh demo records.
"""

import os
import sys
import argparse
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import db
from db import (
    PROTECTED_PROD_DB_PATH,
    DEFAULT_DEMO_DB_PATH,
    init_demo_database,
    execute_query,
    execute_write,
    get_active_db_path,
)
from common.period_tracker import (
    recalculate_user_cycles,
    calculate_period_prediction,
    log_cycle,
)
from common.wellbeing_tracker import (
    analyze_user_wellbeing_patterns,
    get_user_wellbeing_insights,
)
from common.doctor_summary import get_user_doctor_summary


MAYA_USER_ID = "usr_maya_demo"
MAYA_EMAIL = "maya.demo@example.com"
MAYA_NAME = "Maya Demo"

JORDAN_USER_ID = "usr_jordan_gap"
JORDAN_EMAIL = "jordan.gap@example.com"
JORDAN_NAME = "Jordan Gap Demo"

DEMO_PASSWORD_RAW = "DemoPass2026!"


def assert_safe_demo_target(target_path):
    """Refuses execution if the target database is the protected production database."""
    target_abs = os.path.abspath(target_path)
    prod_abs = os.path.abspath(PROTECTED_PROD_DB_PATH)
    if target_abs == prod_abs:
        raise RuntimeError(
            f"CRITICAL SAFETY VIOLATION: seed_demo.py refuses to run against the protected "
            f"production database ({PROTECTED_PROD_DB_PATH}).\n"
            f"The demo environment must use an isolated database (e.g. backend/ovacare_demo.db)."
        )


def seed_demo_database(target_db_path=None, reset_tables=False):
    """
    Seeds the isolated demo database with Maya Demo and Jordan Gap Demo.
    """
    target_path = target_db_path or os.getenv("DEMO_DATABASE_PATH") or DEFAULT_DEMO_DB_PATH
    assert_safe_demo_target(target_path)

    print(f"[*] Initializing isolated demo database at: {target_path}")
    active_path = init_demo_database(target_path, init_schema=True)
    assert_safe_demo_target(active_path)

    if reset_tables:
        print("[*] Resetting demo database tables...")
        # Clear only in demo database
        for table in [
            "community_comments", "community_reactions", "community_posts",
            "community_profiles", "mood_logs", "wellness_logs", "cycles",
            "predictions", "reminders", "users"
        ]:
            try:
                execute_write(f"DELETE FROM {table}")
            except Exception:
                pass
        db._init_test_schema(db.engine)
    else:
        # Idempotent cleanup of demo accounts
        print("[*] Performing idempotent cleanup of demo records...")
        for uid in (MAYA_USER_ID, JORDAN_USER_ID, "usr_demo_patient"):
            execute_write("DELETE FROM community_posts WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM community_profiles WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM mood_logs WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM wellness_logs WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM cycles WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM predictions WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM reminders WHERE user_id = :uid", {"uid": uid})
            execute_write("DELETE FROM users WHERE user_id = :uid", {"uid": uid})

    pwd_hash = generate_password_hash(DEMO_PASSWORD_RAW)

    # =========================================================================
    # 1. SEED PRIMARY DEMO PATIENT: MAYA DEMO
    # =========================================================================
    print(f"[*] Creating Primary Demo Patient: {MAYA_NAME} ({MAYA_EMAIL})...")
    execute_write(
        """
        INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos, pcos_diagnosis_status, role)
        VALUES (:uid, :uname, :email, :pwd, :age, :lifestyle, :has_pcos, :status, :role)
        """,
        {
            "uid": MAYA_USER_ID,
            "uname": MAYA_NAME,
            "email": MAYA_EMAIL,
            "pwd": pwd_hash,
            "age": 24,
            "lifestyle": "Moderate",
            "has_pcos": 0,
            "status": "prefer_not_to_say",
            "role": "member",
        }
    )

    # Community profile for Maya
    execute_write(
        """
        INSERT INTO community_profiles (profile_id, user_id, display_name, avatar_key, bio)
        VALUES (:pid, :uid, :dname, :avatar, :bio)
        """,
        {
            "pid": f"prof_{MAYA_USER_ID}",
            "uid": MAYA_USER_ID,
            "dname": "Maya D.",
            "avatar": "avatar_lavender",
            "bio": "Dedicated synthetic demo patient account demonstrating 6 months of cycle and wellness insights.",
        }
    )

    # 6-Month Chronological Cycle History for Maya
    cycle_specs = [
        ("cyc_maya_01", "2026-05-18", "2026-05-22", 5),
        ("cyc_maya_02", "2026-06-15", "2026-06-19", 5),
        ("cyc_maya_03", "2026-07-14", "2026-07-18", 5),
        ("cyc_maya_04", "2026-08-10", "2026-08-14", 5),
        ("cyc_maya_05", "2026-09-09", "2026-09-13", 5),
        ("cyc_maya_06", "2026-10-07", "2026-10-11", 5),
    ]

    for cid, s_date, e_date, p_len in cycle_specs:
        execute_write(
            """
            INSERT INTO cycles (cycle_id, user_id, start_date, end_date, period_length, irregular, gap_type)
            VALUES (:cid, :uid, :s_date, :e_date, :p_len, 0, NULL)
            """,
            {"cid": cid, "uid": MAYA_USER_ID, "s_date": s_date, "e_date": e_date, "p_len": p_len}
        )

    recalculate_user_cycles(MAYA_USER_ID)
    print("    -> 6 cycles seeded and chronologically calculated.")

    # Daily Wellness Logs for Maya (Rich distribution of complete, partial, explicit None, and NULL)
    raw_logs = [
        # --- CYCLE 1 (2026-05-18 to 2026-06-14) ---
        # Menstrual window (cramps positive)
        ("2026-05-18", 1, "Calm", "Low", 7.5, "Moderate", "Moderate", "Medium", "Low", "Period started. Used heating pad.", "Menstrual"),
        ("2026-05-19", 2, "Calm", "Low", 8.0, "Moderate", "Mild", "Heavy", "Moderate", "Heavy flow today, stayed hydrated.", "Menstrual"),
        ("2026-05-20", 3, "Happy", "Low", 8.0, "Mild", "Mild", "Medium", "Moderate", None, "Menstrual"),
        ("2026-05-21", 4, "Happy", "Low", 8.0, "None", "None", "Light", "High", None, "Menstrual"),
        ("2026-05-22", 5, "Happy", "Low", 8.0, "None", "None", "Light", "High", None, "Menstrual"),
        # Follicular / Mid-cycle
        ("2026-05-25", 8, "Happy", "Low", 8.0, "None", "None", "None", "High", "Morning run, energy feeling great.", "Follicular"),
        ("2026-05-28", 11, None, None, 7.5, None, None, None, "High", None, "Follicular"), # partial log
        ("2026-05-31", 14, "Calm", "Low", 8.0, "None", "None", "None", "High", "Mid-cycle, mild right-side twinge.", "Ovulation"),
        ("2026-06-04", 18, "Calm", "Medium", 7.5, "None", "Mild", "None", "Moderate", None, "Luteal"),
        # Premenstrual window (lower energy positive)
        ("2026-06-12", 26, "Tired", "Medium", 7.0, "None", "Moderate", "None", "Low", "Energy dipped by late afternoon.", "Luteal"),
        ("2026-06-13", 27, "Calm", "Low", 7.5, "None", "Moderate", "None", "Low", "Evening chamomile tea and early bed.", "Luteal"),

        # --- CYCLE 2 (2026-06-15 to 2026-07-13) ---
        # Menstrual window (cramps positive)
        ("2026-06-15", 1, "Calm", "Low", 7.5, "Moderate", "Mild", "Medium", "Moderate", "Period arrival. Warm compress helped.", "Menstrual"),
        ("2026-06-16", 2, "Calm", "Low", 7.5, "Mild", "Mild", "Heavy", "Moderate", None, "Menstrual"),
        ("2026-06-17", 3, "Happy", "Low", 8.0, "None", "None", "Medium", "High", None, "Menstrual"),
        ("2026-06-18", 4, "Happy", "Low", 8.0, "None", "None", "Light", "High", None, "Menstrual"),
        # Follicular / Mid-cycle (High stress & disrupted sleep correlation log)
        ("2026-06-22", 8, "Happy", "Low", 8.5, "None", "None", "None", "High", "Great morning workout!", "Follicular"),
        ("2026-06-25", 11, "Anxious", "High", 5.5, "None", "Moderate", "None", "Low", "Big deadline at work, tossed and turned.", "Follicular"),
        ("2026-06-28", 14, "Calm", "Low", 8.0, "None", "None", "None", "High", None, "Ovulation"),
        ("2026-07-03", 19, None, None, 7.5, None, None, None, "Moderate", None, "Luteal"), # partial log
        # Premenstrual window (lower energy positive)
        ("2026-07-11", 27, "Tired", "Low", 7.0, "None", "Moderate", "None", "Low", "Felt low energy, stayed in.", "Luteal"),
        ("2026-07-12", 28, "Tired", "Medium", 6.5, "None", "Severe", "None", "Very Low", "Needed extra rest today.", "Luteal"),

        # --- CYCLE 3 (2026-07-14 to 2026-08-09) ---
        # Menstrual window (cramps positive)
        ("2026-07-14", 1, "Calm", "Low", 7.5, "Mild", "Mild", "Medium", "Moderate", "Cramps were mild today.", "Menstrual"),
        ("2026-07-15", 2, "Calm", "Low", 7.5, "Mild", "Mild", "Heavy", "Moderate", None, "Menstrual"),
        ("2026-07-16", 3, "Happy", "Low", 8.0, "None", "None", "Medium", "High", None, "Menstrual"),
        # Follicular / Mid-cycle (High stress & disrupted sleep correlation log)
        ("2026-07-22", 9, "Irritated", "High", 5.5, "None", "Moderate", "None", "Low", "Work presentation prep, restless night.", "Follicular"),
        ("2026-07-26", 13, "Happy", "Low", 8.0, "None", "None", "None", "High", "Smooth weekend hiking trip.", "Follicular"),
        ("2026-07-29", 16, None, None, 8.0, None, None, None, "High", None, "Luteal"), # partial log
        # Premenstrual window (Non-fatigued observation, demonstrating variance)
        ("2026-08-07", 25, "Calm", "Low", 8.0, "None", "Mild", "None", "Moderate", "Felt okay today, energy was steady.", "Luteal"),
        ("2026-08-08", 26, "Calm", "Low", 7.5, "None", "None", "None", "Moderate", None, "Luteal"),

        # --- CYCLE 4 (2026-08-10 to 2026-09-08) ---
        # Menstrual window (No cramps logged, demonstrating variance)
        ("2026-08-10", 1, "Happy", "Low", 8.0, "None", "None", "Medium", "High", "Surprised to have no cramps this cycle!", "Menstrual"),
        ("2026-08-11", 2, "Calm", "Low", 7.5, "None", "None", "Medium", "Moderate", None, "Menstrual"),
        ("2026-08-12", 3, "Happy", "Low", 8.0, "None", "None", "Light", "High", None, "Menstrual"),
        # Follicular / Mid-cycle (High stress & disrupted sleep correlation log)
        ("2026-08-20", 11, "Anxious", "High", 6.0, "None", "Moderate", "None", "Moderate", "Stressed about travel plans.", "Follicular"),
        ("2026-08-23", 14, "Happy", "Low", 8.0, "None", "None", "None", "High", None, "Ovulation"),
        ("2026-08-29", 20, None, None, 8.5, None, None, None, "High", None, "Luteal"), # partial log
        # Premenstrual window (lower energy positive, emotional log at 20% rate)
        ("2026-09-05", 27, "Emotional", "Low", 7.5, "None", "Mild", "None", "Moderate", "A bit more sensitive than usual.", "Luteal"),
        ("2026-09-06", 28, "Tired", "Medium", 7.0, "None", "Moderate", "None", "Low", "Low energy before bed.", "Luteal"),
        ("2026-09-07", 29, "Calm", "Low", 7.5, "None", "Moderate", "None", "Low", None, "Luteal"),

        # --- CYCLE 5 (2026-09-09 to 2026-10-06) ---
        # Menstrual window (cramps positive)
        ("2026-09-09", 1, "Calm", "Low", 7.5, "Moderate", "Moderate", "Medium", "Low", "Heating pad used during work.", "Menstrual"),
        ("2026-09-10", 2, "Calm", "Low", 7.5, "Mild", "Mild", "Heavy", "Moderate", None, "Menstrual"),
        ("2026-09-11", 3, "Happy", "Low", 8.0, "None", "None", "Medium", "High", None, "Menstrual"),
        # Follicular / Mid-cycle (High stress correlation log)
        ("2026-09-18", 10, "Tired", "High", 5.5, "None", "Severe", "None", "Low", "Late night working.", "Follicular"),
        ("2026-09-22", 14, "Happy", "Low", 8.0, "None", "None", "None", "High", "Energized, full night rest.", "Ovulation"),
        ("2026-09-27", 19, None, None, 8.0, None, None, None, "High", None, "Luteal"), # partial log
        # Premenstrual window (lower energy positive)
        ("2026-10-04", 26, "Tired", "Low", 7.0, "None", "Moderate", "None", "Low", "Cozy quiet evening, energy dipped.", "Luteal"),
        ("2026-10-05", 27, "Tired", "Medium", 7.0, "None", "Moderate", "None", "Low", None, "Luteal"),

        # --- CYCLE 6 (Ongoing, 2026-10-07 to present) ---
        # Menstrual window (cramps positive)
        ("2026-10-07", 1, "Calm", "Low", 7.0, "Moderate", "Moderate", "Medium", "Low", "Day 1 flow and cramps.", "Menstrual"),
        ("2026-10-08", 2, "Calm", "Low", 7.5, "Mild", "Mild", "Heavy", "Moderate", None, "Menstrual"),
        ("2026-10-09", 3, "Happy", "Low", 8.0, "None", "None", "Medium", "High", None, "Menstrual"),
        ("2026-10-10", 4, "Happy", "Low", 8.0, "None", "None", "Light", "High", None, "Menstrual"),
        # Follicular / Current (High stress correlation log)
        ("2026-10-14", 8, "Happy", "Low", 8.0, "None", "None", "None", "High", None, "Follicular"),
        ("2026-10-16", 10, "Anxious", "High", 6.0, "None", "Moderate", "None", "Moderate", "Project review week.", "Follicular"),
        ("2026-10-20", 14, "Happy", "Low", 8.5, "None", "None", "None", "High", None, "Ovulation"),
        ("2026-10-24", 18, "Calm", "Low", 8.0, "None", "None", "None", "High", "Feeling well and balanced.", "Luteal"),
        ("2026-10-25", 19, "Happy", "Low", 8.0, "None", "None", "None", "High", "Ready for the week ahead.", "Luteal"),
    ]

    for idx, row in enumerate(raw_logs):
        log_id = f"log_maya_{idx+1:03d}"
        date_str, c_day, mood, stress, sleep, cramps, fatigue, flow, energy, notes, phase = row
        execute_write(
            """
            INSERT INTO wellness_logs (
                log_id, user_id, date, cycle_day, mood, stress, sleep_hours,
                cramps, fatigue, flow, energy_level, notes, cycle_phase
            ) VALUES (
                :lid, :uid, :date, :cday, :mood, :stress, :sleep,
                :cramps, :fatigue, :flow, :energy, :notes, :phase
            )
            """,
            {
                "lid": log_id,
                "uid": MAYA_USER_ID,
                "date": date_str,
                "cday": c_day,
                "mood": mood,
                "stress": stress,
                "sleep": sleep,
                "cramps": cramps,
                "fatigue": fatigue,
                "flow": flow,
                "energy": energy,
                "notes": notes,
                "phase": phase,
            }
        )
        if mood:
            execute_write(
                """
                INSERT INTO mood_logs (mood_log_id, user_id, mood, date)
                VALUES (:mid, :uid, :mood, :date)
                """,
                {
                    "mid": f"mld_maya_{idx+1:03d}",
                    "uid": MAYA_USER_ID,
                    "mood": mood,
                    "date": date_str,
                }
            )

    print(f"    -> {len(raw_logs)} wellness entries and mood logs seeded for Maya.")

    # Community post by Maya
    execute_write(
        """
        INSERT INTO community_posts (
            post_id, user_id, category_id, title, body, is_anonymous,
            health_label, status, view_count
        ) VALUES (
            :pid, :uid, :cat, :title, :body, 0, :label, 'active', 12
        )
        """,
        {
            "pid": "post_maya_demo_01",
            "uid": MAYA_USER_ID,
            "cat": "cat_nutrition_lifestyle",
            "title": "Gentle evening routines and sleep during luteal days",
            "body": "Over the past six months of tracking, having a consistent wind-down routine when my energy dips has really helped me rest better. What gentle habits have helped you all?",
            "label": "Personal Experience",
        }
    )

    # =========================================================================
    # 2. SEED GAP DEMO PATIENT: JORDAN GAP DEMO (Unclarified Cycle Gap Scenario)
    # =========================================================================
    print(f"[*] Creating Gap Demo Patient: {JORDAN_NAME} ({JORDAN_EMAIL})...")
    execute_write(
        """
        INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos, pcos_diagnosis_status, role)
        VALUES (:uid, :uname, :email, :pwd, :age, :lifestyle, :has_pcos, :status, :role)
        """,
        {
            "uid": JORDAN_USER_ID,
            "uname": JORDAN_NAME,
            "email": JORDAN_EMAIL,
            "pwd": pwd_hash,
            "age": 27,
            "lifestyle": "Active",
            "has_pcos": 0,
            "status": "prefer_not_to_say",
            "role": "member",
        }
    )

    execute_write(
        """
        INSERT INTO community_profiles (profile_id, user_id, display_name, avatar_key, bio)
        VALUES (:pid, :uid, :dname, :avatar, :bio)
        """,
        {
            "pid": f"prof_{JORDAN_USER_ID}",
            "uid": JORDAN_USER_ID,
            "dname": "Jordan G.",
            "avatar": "avatar_mint",
            "bio": "Synthetic demo profile demonstrating cycle gap detection and clarification.",
        }
    )

    # Jordan has a 56-day gap between cycle 1 and cycle 2
    jordan_cycles = [
        ("cyc_jordan_01", "2026-06-01", "2026-06-05", 5),
        ("cyc_jordan_02", "2026-07-27", "2026-07-31", 5), # 56 days gap!
        ("cyc_jordan_03", "2026-08-25", "2026-08-29", 5), # 29 days
        ("cyc_jordan_04", "2026-09-24", "2026-09-28", 5), # 30 days
        ("cyc_jordan_05", "2026-10-23", "2026-10-27", 5), # ongoing
    ]

    for cid, s_date, e_date, p_len in jordan_cycles:
        execute_write(
            """
            INSERT INTO cycles (cycle_id, user_id, start_date, end_date, period_length, irregular, gap_type)
            VALUES (:cid, :uid, :s_date, :e_date, :p_len, 0, NULL)
            """,
            {"cid": cid, "uid": JORDAN_USER_ID, "s_date": s_date, "e_date": e_date, "p_len": p_len}
        )

    recalculate_user_cycles(JORDAN_USER_ID)
    print("    -> 5 cycles seeded for Jordan (with unclarified 56-day tracking gap).")

    # Brief logs for Jordan
    execute_write(
        """
        INSERT INTO wellness_logs (log_id, user_id, date, cycle_day, mood, stress, sleep_hours, energy_level)
        VALUES (:lid, :uid, :date, :cday, :mood, :stress, :sleep, :energy)
        """,
        {
            "lid": "log_jordan_001",
            "uid": JORDAN_USER_ID,
            "date": "2026-10-23",
            "cday": 1,
            "mood": "Calm",
            "stress": "Low",
            "sleep": 7.5,
            "energy": "Moderate",
        }
    )

    print("[+] Demo data seeding completed successfully.")
    return True


def verify_demo_patient_outputs():
    """
    Validates that seeded demo data generates expected predictions,
    deterministic wellbeing patterns, and My Health Report.
    """
    print("\n[*] Running automated clinical & prediction verifications on Maya Demo...")

    # 1. Cycles & Prediction Verification
    cycles = execute_query(
        "SELECT * FROM cycles WHERE user_id = :uid ORDER BY start_date ASC",
        {"uid": MAYA_USER_ID}
    )
    assert len(cycles) == 6, f"Expected 6 cycles, found {len(cycles)}"
    lengths = [c['cycle_length'] for c in cycles if c['cycle_length'] is not None]
    assert lengths == [28, 29, 27, 30, 28], f"Unexpected cycle lengths: {lengths}"

    prediction = calculate_period_prediction(cycles, has_pcos=False)
    assert prediction['average_cycle_length'] == 28, f"Expected avg 28, got {prediction['average_cycle_length']}"
    assert prediction['prediction_confidence'] == 'high', f"Expected high confidence, got {prediction['prediction_confidence']}"
    assert prediction['regularity_assessment'] == 'regular', f"Expected regular, got {prediction['regularity_assessment']}"
    assert prediction['has_unclarified_gap'] is False, "Maya should have no unclarified gaps"
    assert prediction['predicted_date'] == "2026-11-04", f"Expected 2026-11-04, got {prediction['predicted_date']}"
    print("    [PASS] Cycle lengths: [28, 29, 27, 30, 28] -> Avg 28d, Regular, High Confidence, Next: 2026-11-04")

    # 2. Wellbeing Pattern Intelligence Verification
    logs = execute_query(
        "SELECT * FROM wellness_logs WHERE user_id = :uid ORDER BY date ASC",
        {"uid": MAYA_USER_ID}
    )
    assert len(logs) >= 30, f"Expected >= 30 wellness logs, found {len(logs)}"

    patterns_report = analyze_user_wellbeing_patterns(cycles, logs)
    patterns = {p['pattern_id']: p for p in patterns_report['patterns']}

    # Check Premenstrual Lower Energy (Supported)
    p_energy = patterns.get('premenstrual_lower_energy')
    assert p_energy and p_energy['evidence_status'] == 'supported', "Lower energy pattern must be supported"
    print(f"    [PASS] Pattern 1: {p_energy['title']} -> {p_energy['evidence_status']} ({p_energy['description']})")

    # Check Menstrual Discomfort / Cramps (Supported)
    p_cramps = patterns.get('menstrual_cramps')
    assert p_cramps and p_cramps['evidence_status'] == 'supported', "Menstrual cramps pattern must be supported"
    print(f"    [PASS] Pattern 2: {p_cramps['title']} -> {p_cramps['evidence_status']} ({p_cramps['description']})")

    # Check Stress & Sleep Relationship (Supported)
    p_stress = patterns.get('stress_sleep_correlation')
    assert p_stress and p_stress['evidence_status'] == 'supported', "Stress & sleep correlation must be supported"
    print(f"    [PASS] Pattern 3: {p_stress['title']} -> {p_stress['evidence_status']} ({p_stress['description']})")

    # Check Premenstrual Emotional Shifts (Honest non-recurring guardrail)
    p_mood = patterns.get('premenstrual_emotional_shifts')
    assert p_mood and p_mood['evidence_status'] == 'non_recurring', "Emotional shifts must be non_recurring"
    print(f"    [PASS] Pattern 4: {p_mood['title']} -> {p_mood['evidence_status']} ({p_mood['status_reason']})")

    # 3. My Health Report Verification
    summary = get_user_doctor_summary(MAYA_USER_ID)
    assert summary['patient_context']['username'] == MAYA_NAME
    assert summary['patient_context']['age'] == 24
    assert summary['timeframe']['total_cycles_logged'] == 6
    assert summary['category_1_recorded_facts']['total_cycles_recorded'] == 6
    assert round(summary['category_2_statistical_estimates']['average_cycle_length_days']) == 28
    assert summary['clinical_disclaimer'] is not None
    print("    [PASS] Unified My Health Report verified (Category 1, 2, and 3 clinical segregation active).")

    # 4. Jordan Gap Demo Verification
    j_cycles = execute_query(
        "SELECT * FROM cycles WHERE user_id = :uid ORDER BY start_date ASC",
        {"uid": JORDAN_USER_ID}
    )
    j_pred = calculate_period_prediction(j_cycles, has_pcos=False)
    assert j_pred['has_unclarified_gap'] is True, "Jordan must have unclarified gap"
    assert j_pred['history_quality'] == 'needs_clarification', "Jordan history quality must need clarification"
    assert j_pred['prediction_confidence'] == 'moderate', "Jordan prediction confidence must be moderate"
    assert len(j_pred['excluded_intervals']) == 1, "Jordan must have 1 excluded interval"
    print(f"    [PASS] Jordan Gap Demo verified: 56-day gap correctly flagged as unclarified_gap needing user input.")

    print("\n[+] ALL DEMO PATIENT VERIFICATION CHECKS PASSED!\n")


def main():
    parser = argparse.ArgumentParser(description="OvaCare AI Synthetic Demo Patient Seeder")
    parser.add_argument("--confirm", action="store_true", help="Confirm execution without interactive prompt.")
    parser.add_argument("--reset", action="store_true", help="Completely reset and reinitialize demo tables.")
    parser.add_argument("--target-db", type=str, default=None, help="Explicit target demo database path.")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing demo data without seeding.")

    args = parser.parse_args()
    target = args.target_db or os.getenv("DEMO_DATABASE_PATH") or DEFAULT_DEMO_DB_PATH

    assert_safe_demo_target(target)

    if not args.confirm and not args.verify_only:
        print(f"Targeting demo database: {target}")
        print("This will seed synthetic demo accounts (Maya Demo, Jordan Gap Demo).")
        if sys.stdin.isatty():
            choice = input("Proceed with demo seeding? [y/N]: ").strip().lower()
            if choice not in ('y', 'yes'):
                print("Aborted.")
                sys.exit(0)

    if not args.verify_only:
        seed_demo_database(target_db_path=target, reset_tables=args.reset)

    verify_demo_patient_outputs()


if __name__ == "__main__":
    main()
