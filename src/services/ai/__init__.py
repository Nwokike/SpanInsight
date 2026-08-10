"""AI Service package exporting all split modules."""

from __future__ import annotations

from .analysis import (
    analyze_image_for_data,
    describe_dataset,
    describe_result,
    fallback_suggestions,
    generate_code,
    generate_corrected_code,
    interpret,
    plan_next_step,
    suggest,
)
from .audio import transcribe_audio
from .client import check_health
from .forms import generate_form_schema
from .reports import arrange_report, edit_report_with_ai
from .vision import analyze_image

__all__ = [
    "analyze_image",
    "analyze_image_for_data",
    "arrange_report",
    "check_health",
    "describe_dataset",
    "describe_result",
    "edit_report_with_ai",
    "fallback_suggestions",
    "generate_code",
    "generate_corrected_code",
    "generate_form_schema",
    "interpret",
    "plan_next_step",
    "suggest",
    "transcribe_audio",
]
