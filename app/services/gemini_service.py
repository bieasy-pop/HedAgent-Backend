import json
import httpx
from app.config import settings


GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
)

RISK_LABELS = {
    "critical":       (0.0, 1.5),    # GPA < 1.5
    "at_risk":        (1.5, 2.0),    # GPA 1.5 – 2.0
    "average":        (2.0, 3.0),    # GPA 2.0 – 3.0
    "on_track":       (3.0, 3.5),    # GPA 3.0 – 3.5
    "high_potential": (3.5, 5.0),    # GPA > 3.5
}


def _classify_by_gpa(gpa: float | None, attendance: float | None) -> tuple[str, float]:
    """
    Rule-based pre-classification before sending to Gemini.
    Returns (label, score 0-1).
    """
    if gpa is None:
        return "unclassified", 0.0

    label = "average"
    for l, (low, high) in RISK_LABELS.items():
        if low <= gpa < high:
            label = l
            break

    # Attendance penalty — drop one level if attendance is poor
    if attendance is not None and attendance < 0.7:
        order = ["high_potential", "on_track", "average", "at_risk", "critical"]
        idx = order.index(label) if label in order else 2
        label = order[min(idx + 1, len(order) - 1)]

    score_map = {
        "high_potential": 0.1,
        "on_track": 0.3,
        "average": 0.5,
        "at_risk": 0.75,
        "critical": 0.95,
    }
    return label, score_map.get(label, 0.5)


async def classify_student(student_data: dict, triggered_by: str = "system") -> dict:
    """
    Sends student data to Gemini for classification and actionable remarks.
    Returns a structured dict ready to save to ai_classifications table.
    """
    pre_label, pre_score = _classify_by_gpa(
        student_data.get("gpa"),
        student_data.get("attendance_rate"),
    )

    prompt = f"""You are an academic intervention advisor analysing a university student's profile.

Student data:
- GPA: {student_data.get('gpa', 'not recorded')} (scale: 0.0–5.0)
- Attendance rate: {round((student_data.get('attendance_rate') or 0) * 100, 1)}%
- Level: {student_data.get('level', 'unknown')}
- Department: {student_data.get('department', 'unknown')}
- Programme: {student_data.get('programme', 'unknown')}
- Pre-classification: {pre_label}
- Courses enrolled: {student_data.get('course_count', 0)}

Respond ONLY with valid JSON. No markdown, no backticks. Use this exact structure:
{{
  "risk_label": "{pre_label}",
  "summary": "2-3 sentence summary of the student's current academic situation",
  "remarks": "3-5 specific, actionable steps the student should take right now",
  "educator_alert": "1-2 sentence alert for the student's educator if urgent attention is needed, or null if not urgent",
  "recommendations": [
    "Specific action item 1",
    "Specific action item 2",
    "Specific action item 3"
  ]
}}

The risk_label must be one of: critical, at_risk, average, on_track, high_potential.
Be empathetic, practical and specific. Avoid generic advice."""

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                GEMINI_URL,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 800,
                    },
                }
            )
        data = response.json()

        if "error" in data:
            raise Exception(data["error"].get("message", "Gemini API error"))

        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
        raw_text = raw_text.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(raw_text)

        return {
            "risk_label": result.get("risk_label", pre_label),
            "risk_score": pre_score,
            "summary": result.get("summary", ""),
            "remarks": result.get("remarks", ""),
            "educator_alert": result.get("educator_alert"),
            "recommendations": result.get("recommendations", []),
            "model_used": "gemini-1.5-flash",
            "triggered_by": triggered_by,
        }

    except Exception as e:
        # Fallback to rule-based classification if Gemini fails
        return {
            "risk_label": pre_label,
            "risk_score": pre_score,
            "summary": f"Student has a GPA of {student_data.get('gpa')} with {round((student_data.get('attendance_rate') or 0) * 100)}% attendance.",
            "remarks": "Please update your course scores and attendance to receive personalised recommendations.",
            "educator_alert": "AI classification temporarily unavailable. Manual review recommended." if pre_label in ("at_risk", "critical") else None,
            "recommendations": ["Update GPA records", "Improve attendance", "Consult your lecturer"],
            "model_used": "rule_based_fallback",
            "triggered_by": triggered_by,
        }


async def generate_analytics_summary(cohort_data: dict) -> str:
    """Generates a natural language analytics summary for an educator's cohort."""
    prompt = f"""You are an academic analytics advisor. Summarise the following cohort data for an educator in 3-4 sentences. Be concise and highlight the most important patterns.

Cohort data: {json.dumps(cohort_data)}

Respond with plain text only. No JSON, no markdown."""

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                GEMINI_URL,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.4, "maxOutputTokens": 300},
                }
            )
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return "Analytics summary temporarily unavailable."
