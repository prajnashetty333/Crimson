"""Shared utilities and common helpers for OvaCare AI backend."""
from .auth import (
    auth_serializer,
    generate_auth_token,
    verify_auth_token,
    token_required,
    DEFAULT_TOKEN_MAX_AGE,
)
from .period_tracker import (
    VALID_GAP_CLARIFICATIONS,
    calculate_intervals,
    validate_cycle_inputs,
    recalculate_user_cycles,
    log_cycle,
    delete_user_cycle,
    calculate_period_prediction,
    calculate_cycle_analytics_metrics,
    get_user_typical_cycle_lengths,
)

from .doctor_summary import (
    generate_doctor_summary,
    get_user_doctor_summary,
    render_doctor_summary_html,
)

__all__ = [
    "auth_serializer",
    "generate_auth_token",
    "verify_auth_token",
    "token_required",
    "DEFAULT_TOKEN_MAX_AGE",
    "VALID_GAP_CLARIFICATIONS",
    "calculate_intervals",
    "validate_cycle_inputs",
    "recalculate_user_cycles",
    "log_cycle",
    "delete_user_cycle",
    "calculate_period_prediction",
    "calculate_cycle_analytics_metrics",
    "get_user_typical_cycle_lengths",
    "generate_doctor_summary",
    "get_user_doctor_summary",
    "render_doctor_summary_html",
]
