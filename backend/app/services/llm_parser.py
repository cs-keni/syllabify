"""
Hybrid parser: LLM-structured parsing of syllabus content.
Uses OpenAI GPT-4o-mini with JSON schema for reliable structured output.
"""
import json
import os
import re

# Model: GPT-4o-mini for cost-effective structured extraction
LLM_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are a syllabus parser. Extract course info, meeting times, and assessments from the provided syllabus sections.

Output strictly valid JSON matching the schema. Use ISO 8601 for dates (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS for times).
Infer academic year from term (e.g. Fall 2025 -> 2025). Assign confidence 0.0-1.0 per assessment based on how clearly the syllabus states it. Use 0.9+ only when you see explicit due date and/or weight. Use 0.5-0.7 when inferring from schedule context.
If unclear, use null. Do not invent data. day_of_week must be MO, TU, WE, TH, FR, SA, or SU. type for assessments must be assignment, midterm, final, quiz, project, or participation.

Do NOT include as assessments: grade scale entries (A 90, B 80, C 70, D 60), policy text (accommodation for religious observances, grades are assigned according to...), sentence fragments, section headers, or anything that is not an actual graded deliverable (homework, project, exam, quiz, etc.). Meeting location must be a room/building, not a section title like "Prerequisites"."""

# JSON schema for structured output (OpenAI strict mode)
SYLLABUS_JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "syllabus_parse",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "course": {
                    "type": "object",
                    "properties": {
                        "course_code": {"type": "string"},
                        "course_title": {"type": "string"},
                        "term": {"type": "string"},
                        "timezone": {"type": "string"},
                        "instructors": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "email": {"type": "string"},
                                },
                                "required": ["id", "name"],
                                "additionalProperties": False,
                            },
                        },
                        "meeting_times": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "day_of_week": {"type": "string"},
                                    "start_time": {"type": "string"},
                                    "end_time": {"type": "string"},
                                    "location": {"type": "string"},
                                    "type": {"type": "string"},
                                },
                                "required": ["day_of_week", "type"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["course_code", "course_title", "term", "instructors", "meeting_times"],
                    "additionalProperties": False,
                },
                "assessments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "category_id": {"type": "string"},
                            "type": {"type": "string"},
                            "due_datetime": {"type": "string"},
                            "all_day": {"type": "boolean"},
                            "weight_percent": {"type": "number"},
                            "confidence": {"type": "number"},
                            "source_excerpt": {"type": "string"},
                        },
                        "required": ["id", "title", "category_id", "type", "confidence", "source_excerpt"],
                        "additionalProperties": False,
                    },
                },
                "assessment_categories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "weight_percent": {"type": "number"},
                        },
                        "required": ["id", "name"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["course", "assessments", "assessment_categories"],
            "additionalProperties": False,
        },
    },
}


def _build_user_prompt(intermediate: dict) -> str:
    """Build user prompt from structured extraction."""
    sections = intermediate.get("sections") or []
    tables = intermediate.get("tables") or []
    raw = intermediate.get("raw_text") or ""
    candidate_dates = intermediate.get("candidate_dates") or []
    candidate_pct = intermediate.get("candidate_percentages") or []

    parts = ["Parse this syllabus into the schema.\n"]
    for s in sections[:8]:
        h = s.get("heading", "Content")
        c = (s.get("content") or "").strip()[:1500]
        if c:
            parts.append(f"\n[SECTION: {h}]\n{c}")
    if tables:
        parts.append("\n[TABLES]")
        for i, t in enumerate(tables[:3]):
            rows = t[:15] if isinstance(t[0], (list, tuple)) else [t]
            for row in rows:
                if isinstance(row, (list, tuple)):
                    parts.append(" | ".join(str(c) for c in row if c))
                else:
                    parts.append(str(row))
    if candidate_dates:
        parts.append("\n[DATES MENTIONED]")
        for d in candidate_dates[:15]:
            parts.append(f"  {d.get('raw', '')} (context: {d.get('context', '')[:60]})")
    if candidate_pct:
        parts.append("\n[PERCENTAGES MENTIONED]")
        for p in candidate_pct[:15]:
            parts.append(f"  {p.get('value')}% - {p.get('context', '')[:60]}")
    if len(parts) == 1 and raw:
        parts.append(raw[:6000])
    return "\n".join(parts)


def parse_with_llm(intermediate: dict) -> dict | None:
    """
    Call OpenAI to parse syllabus content into schema.
    intermediate: from document_utils.extract_structured_from_file()
    Returns full parse dict (course, assessments, assessment_categories) or None on failure.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None

    user_content = _build_user_prompt(intermediate)
    if len(user_content) > 28000:
        user_content = user_content[:28000] + "\n[...truncated]"

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format=SYLLABUS_JSON_SCHEMA,
            temperature=0.1,
        )
    except Exception:
        return None

    msg = response.choices[0].message if response.choices else None
    if not msg or not msg.content:
        return None
    content = msg.content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None

    return _validate_and_normalize(data)


def _validate_and_normalize(data: dict) -> dict:
    """Ensure schema compliance, normalize enums, add IDs."""
    course = data.get("course") or {}
    assessments = data.get("assessments") or []
    categories = data.get("assessment_categories") or []

    # Normalize day_of_week: Tuesday -> TU, Th -> TH, etc.
    day_map = {
        "monday": "MO", "tuesday": "TU", "wednesday": "WE", "thursday": "TH",
        "friday": "FR", "saturday": "SA", "sunday": "SU",
        "mon": "MO", "tue": "TU", "wed": "WE", "thu": "TH", "fri": "FR",
        "mo": "MO", "tu": "TU", "we": "WE", "th": "TH", "fr": "FR", "sa": "SA", "su": "SU",
    }
    for m in course.get("meeting_times") or []:
        d = (m.get("day_of_week") or "").strip().lower()
        m["day_of_week"] = day_map.get(d, day_map.get(d[:2], d.upper()[:2] if len(d) >= 2 else d))

    # Ensure IDs
    cat_ids = {c.get("id") for c in categories if c.get("id")}
    for i, a in enumerate(assessments):
        if not a.get("id"):
            a["id"] = f"llm_{i+1}"
        cid = a.get("category_id")
        if cid and cid not in cat_ids and categories:
            a["category_id"] = categories[0].get("id", "general")

    return {
        "course": {
            "course_code": course.get("course_code"),
            "course_title": course.get("course_title"),
            "term": course.get("term"),
            "timezone": course.get("timezone") or "America/Los_Angeles",
            "instructors": course.get("instructors") or [],
            "meeting_times": course.get("meeting_times") or [],
        },
        "assessments": assessments,
        "assessment_categories": categories,
        "late_pass_policy": data.get("late_pass_policy") or {"total_allowed": None, "extension_days": None},
    }
