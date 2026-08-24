"""Starter survey templates for the Forms flywheel.

Pure data — no Flet imports. Each template fills the creation prompt so the
AI schema generator has a strong starting instruction; users can edit before
generating.
"""

from __future__ import annotations

TEMPLATES: list[dict] = [
    {
        "icon": "star",
        "title": "Product Feedback",
        "prompt": (
            "Create a product feedback survey: overall satisfaction (rating), "
            "what they liked most (checkbox with options quality/price/packaging/"
            "ease of use), what to improve (long text), would buy again (radio "
            "yes/maybe/no), and recommend to a friend (rating 1-5)."
        ),
    },
    {
        "icon": "event",
        "title": "Event Registration",
        "prompt": (
            "Create an event registration form: full name (text, required), email "
            "(email, required), phone (phone), organization (text), session track "
            "(radio: technical/business/general), dietary needs (checkbox options "
            "none/vegetarian/vegan/gluten-free/other), plus any special requests "
            "(textarea)."
        ),
    },
    {
        "icon": "school",
        "title": "Course Evaluation",
        "prompt": (
            "Create a course evaluation survey: instructor clarity (rating), "
            "course pace (radio too slow/about right/too fast), most valuable "
            "topic (text), least valuable topic (text), materials quality "
            "(rating), would recommend (radio yes/no), and open feedback "
            "(textarea)."
        ),
    },
    {
        "icon": "science",
        "title": "Research Screening",
        "prompt": (
            "Create a research participant screening form: age group (radio 18-24/"
            "25-34/35-44/45-54/55+), gender (radio male/female/non-binary/prefer "
            "not to say), location region (select with 6 regions), highest "
            "education (select), prior participation (radio yes/no), consent to "
            "be contacted (checkbox)."
        ),
    },
    {
        "icon": "inventory",
        "title": "Inventory Count",
        "prompt": (
            "Create an inventory count form: item name (text, required), category "
            "(select: electronics/apparel/food/supplies/other), counted quantity "
            "(number, required), unit condition (radio new/good/damaged/expired), "
            "counted by (text), location or shelf code (text), notes (textarea)."
        ),
    },
]
