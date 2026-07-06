from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = """You are an academic intervention advisor for a school management system.
You analyse student performance data and suggest targeted, actionable interventions.
Be concise, empathetic, and evidence-based. Always consider the student's context."""


async def generate_student_insight(student_data: dict) -> str:
    """
    Generates an AI insight and risk assessment for a student.
    Called when a student profile is updated or flagged.
    """
    prompt = f"""Analyse this student's academic data and provide:
1. A brief summary of their current situation (2-3 sentences)
2. Key risk factors (bullet points)
3. Recommended interventions (bullet points)

Student data:
{student_data}"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        max_tokens=settings.OPENAI_MAX_TOKENS,
        temperature=0.4,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


async def generate_intervention_plan(
    student_data: dict,
    intervention_type: str,
    description: str,
) -> str:
    """
    Generates a specific action plan for a raised intervention.
    """
    prompt = f"""An educator has raised a '{intervention_type}' intervention for a student.

Student profile:
{student_data}

Educator's note:
{description}

Provide a structured action plan with:
1. Immediate steps (this week)
2. Short-term goals (next 4 weeks)
3. Suggested resources or referrals
4. Success indicators"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        max_tokens=settings.OPENAI_MAX_TOKENS,
        temperature=0.3,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


async def educator_chat(conversation: list[dict]) -> str:
    """
    Multi-turn chat for educators asking follow-up questions about a student.
    `conversation` is a list of {"role": "user"|"assistant", "content": "..."} dicts.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation
    response = await client.chat.completions.create(
        model="gpt-4o",
        max_tokens=settings.OPENAI_MAX_TOKENS,
        temperature=0.5,
        messages=messages,
    )
    return response.choices[0].message.content
