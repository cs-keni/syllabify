"""
Late pass policy extraction: total_allowed, extension_days.
"""
import re


def parse_late_policy(text: str) -> dict:
    """Extract late pass policy: total_allowed, extension_days."""
    policy = {"total_allowed": None, "extension_days": None}
    m = re.search(r"(\d+)\s*[\"'\u201C\u201D]?\s*(?:late\s+)?pass(?:es)?", text[:15000], re.I)
    if m:
        policy["total_allowed"] = int(m.group(1))
    if policy["total_allowed"] is None:
        m = re.search(r'["\u201C\u201D]?\s*late\s+account\s*["\u201C\u201D]?\s+of\s+(\d+)\s+days?', text[:15000], re.I)
        if m:
            policy["total_allowed"] = int(m.group(1))
    # "Up to two missed individual obligations" -> total_allowed: 2
    if policy["total_allowed"] is None and re.search(r"(?:up to |allow(?:ed|s)?\s+)?(?:two|2)\s+missed\s+(?:individual\s+)?(?:obligations?|deadlines?|assignments?|activities?)", text[:15000], re.I):
        policy["total_allowed"] = 2
    late_pass_patterns = [
        r"(?:one|1)\s+late\s+(?:project|assignment)", r"(?:one|1)\s+(?:project|assignment)\s+late",
        r"turn in (?:one|1) (?:project|assignment) late", r"(?:one|1)\s*[\"'\u201C\u201D]?\s*late\s*submission\s*token",
        r"have\s+(?:one|1)\s+.{0,15}late\s*submission", r"one[\"'\u201C\u201D]?\s*latesubmissiontoken",
        r"(?:one|1)\s*[\"'\u201C\u201D]?\s*latesubmissiontoken",
        r"first\s+time\s+you\s+request\s+(?:this|it)\s+I\s+will\s+automatically\s+grant",
        r"one\s+free\s+pass", r"first\s+\.\.\.\s+automatically\s+grant",
    ]
    for pat in late_pass_patterns:
        if re.search(pat, text[:15000], re.I) and policy["total_allowed"] is None:
            policy["total_allowed"] = 1
            break
    m = re.search(r"(\d+)\s*(?:hour|hours)\s*(?:each|extension|late|extensions?)", text[:15000], re.I)
    if m:
        policy["extension_days"] = int(m.group(1))
    if policy["extension_days"] is None:
        m = re.search(r"(\d+)\s*(?:day|days)\s*(?:each|extension|late)", text[:15000], re.I)
        if m:
            policy["extension_days"] = int(m.group(1))
    return policy
