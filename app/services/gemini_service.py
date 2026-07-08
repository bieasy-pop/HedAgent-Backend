import json
import httpx
from app.config import settings


GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
)

# GPA grading scale for this institution (5.0 max)
GPA_SCALE = """
GPA Grading Scale (5.0 maximum):
- 4.50 – 5.00 → Best Result     (First Class)
- 4.00 – 4.49 → Good Result     (Second Class Upper)
- 3.50 – 3.99 → Fair Result     (Second Class Lower)
- 3.00 – 3.49 → Average Result  (Third Class)
- Below 3.00  → Poor Result     (At risk of academic failure)
"""

# Rule-based classification aligned to the GPA scale above
def _classify_by_gpa(gpa: float | None, attendance: float | None) -> tuple[str, float]:
    """
    Pre-classifies a student based on institutional GPA scale before Gemini refines it.
    Returns (label, risk_score 0-1).
    Higher risk_score = more urgent intervention needed.
    """
    if gpa is None:
        return "unclassified", 0.0

    if gpa >= 4.50:
        label, score = "high_potential", 0.05     # Best Result — First Class
    elif gpa >= 4.00:
        label, score = "on_track", 0.15            # Good Result — 2nd Class Upper
    elif gpa >= 3.50:
        label, score = "on_track", 0.30            # Fair Result — 2nd Class Lower
    elif gpa >= 3.00:
        label, score = "average", 0.50             # Average Result — Third Class
    elif gpa >= 2.00:
        label, score = "at_risk", 0.75             # Poor Result — at risk
    else:
        label, score = "critical", 0.95            # Critically poor — urgent intervention

    # Attendance penalty — poor attendance drops one level
    if attendance is not None and attendance < 0.70:
        order = ["high_potential", "on_track", "average", "at_risk", "critical"]
        idx = order.index(label) if label in order else 2
        label = order[min(idx + 1, len(order) - 1)]
        score = min(score + 0.15, 0.99)

    return label, round(score, 2)


def _gpa_description(gpa: float | None) -> str:
    """Returns the institutional grade description for a given GPA."""
    if gpa is None:
        return "not recorded"
    if gpa >= 4.50:
        return f"{gpa} — Best Result (First Class)"
    if gpa >= 4.00:
        return f"{gpa} — Good Result (Second Class Upper)"
    if gpa >= 3.50:
        return f"{gpa} — Fair Result (Second Class Lower)"
    if gpa >= 3.00:
        return f"{gpa} — Average Result (Third Class)"
    return f"{gpa} — Poor Result (at risk of academic failure)"


async def classify_student(student_data: dict, triggered_by: str = "system") -> dict:
    """
    Sends student data to Gemini for classification and actionable remarks.
    Uses the institutional 5.0 GPA scale for accurate context.
    Returns a structured dict ready to save to ai_classifications table.
    """
    gpa = student_data.get("gpa")
    attendance = student_data.get("attendance_rate")
    pre_label, pre_score = _classify_by_gpa(gpa, attendance)

    prompt = f"""You are an academic intervention advisor at a Nigerian university analysing a student's profile.

{GPA_SCALE}

Student profile:
- GPA: {_gpa_description(gpa)}
- Attendance rate: {round((attendance or 0) * 100, 1)}%
- Level: {student_data.get('level', 'unknown')}
- Department: {student_data.get('department', 'unknown')}
- Programme: {student_data.get('programme', 'unknown')}
- Courses enrolled: {student_data.get('course_count', 0)}
- Pre-classification: {pre_label}

Using the GPA grading scale above as your reference, provide a classification and intervention plan.

Respond ONLY with valid JSON. No markdown, no backticks, no extra text. Use this exact structure:
{{
  "risk_label": "one of: critical, at_risk, average, on_track, high_potential",
  "gpa_grade": "one of: Best Result, Good Result, Fair Result, Average Result, Poor Result",
  "summary": "2-3 sentences describing the student's current academic standing using the grading scale above",
  "remarks": "3-5 specific actionable steps this student should take right now to improve or maintain their standing",
  "educator_alert": "1-2 sentence urgent alert for the educator if GPA is below 3.0 or attendance is below 70%, otherwise null",
  "recommendations": [
    "Specific action item 1",
    "Specific action item 2",
    "Specific action item 3",
    "Specific action item 4"
  ]
}}

Classification guide:
- GPA 4.50–5.00 → high_potential (Best Result — encourage excellence, scholarship opportunities)
- GPA 4.00–4.49 → on_track (Good Result — maintain momentum, aim higher)
- GPA 3.50–3.99 → on_track (Fair Result — identify weak courses, improve consistency)
- GPA 3.00–3.49 → average (Average Result — targeted support needed, risk of dropping)
- GPA below 3.00 → at_risk or critical (Poor Result — urgent intervention required)

Be empathetic, specific, and practical. Reference the student's actual GPA grade in your response."""

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                GEMINI_URL,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 900,
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
            "gpa_grade": result.get("gpa_grade", _gpa_description(gpa).split("—")[-1].strip() if gpa else "Not recorded"),
            "summary": result.get("summary", ""),
            "remarks": result.get("remarks", ""),
            "educator_alert": result.get("educator_alert"),
            "recommendations": result.get("recommendations", []),
            "model_used": "gemini-1.5-flash",
            "triggered_by": triggered_by,
        }

    except Exception as e:
        # Fallback to rule-based classification if Gemini fails
        gpa_desc = _gpa_description(gpa)
        return {
            "risk_label": pre_label,
            "risk_score": pre_score,
            "gpa_grade": gpa_desc.split("—")[-1].strip() if gpa and "—" in gpa_desc else "Not recorded",
            "summary": f"Student has a GPA of {gpa_desc} with {round((attendance or 0) * 100)}% attendance.",
            "remarks": "Please ensure your course scores and attendance are up to date to receive personalised recommendations.",
            "educator_alert": (
                f"Student has a GPA of {gpa_desc} — urgent intervention required."
                if pre_label in ("at_risk", "critical") else None
            ),
            "recommendations": [
                "Review your weakest courses and seek help from your lecturer",
                "Improve attendance — aim for at least 75%",
                "Schedule a consultation with your academic advisor",
                "Create a study timetable focused on failing courses",
            ],
            "model_used": "rule_based_fallback",
            "triggered_by": triggered_by,
        }


async def generate_analytics_summary(cohort_data: dict) -> str:
    """Generates a natural language analytics summary for an educator's cohort."""
    prompt = f"""You are an academic analytics advisor at a Nigerian university.

{GPA_SCALE}

Summarise the following cohort data for an educator in 3-4 sentences.
Reference the GPA grading scale above when describing student performance levels.
Highlight the most important patterns and which students need urgent attention.

Cohort data: {json.dumps(cohort_data)}

Respond with plain text only. No JSON, no markdown."""

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                GEMINI_URL,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.4, "maxOutputTokens": 350},
                }
            )
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return "Analytics summary temporarily unavailable."
