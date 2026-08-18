"""Core AI data analysis, generation, and orchestration package."""

from __future__ import annotations

from .code_gen import (
    analyze_image_for_data,
    compress_schema,
    generate_code,
    generate_code_meta,
    generate_corrected_code,
)
from .interpreters import (
    describe_dataset,
    describe_result,
    interpret,
)
from .suggestions import (
    fallback_suggestions,
    plan_next_step,
    salvage_json_objects,
    suggest,
)

__all__ = [
    "analyze_image_for_data",
    "compress_schema",
    "describe_dataset",
    "describe_result",
    "fallback_suggestions",
    "generate_code",
    "generate_code_meta",
    "generate_corrected_code",
    "interpret",
    "plan_next_step",
    "salvage_json_objects",
    "suggest",
]
