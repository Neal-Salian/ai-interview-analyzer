import anthropic
import json
from app.core.config import settings
from app.db.crud import get_job

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

def extract_job_context(job_id: str) -> str:
    job = get_job(job_id)
    if not job:
        return ""
    return f"Role: {job.title}\nSeniority: {job.seniority_level}\nDescription: {job.raw_description[:1000]}"

def generate_analysis(transcript: str, job_id: str) -> dict:
    job_context = extract_job_context(job_id)

    prompt = f"""You are assisting a recruiter conducting a job interview.

Job Context:
{job_context}

The candidate just said:
"{transcript}"

Return ONLY a JSON object with this exact structure, no preamble:
{{
    "fact_check": {{
        "has_issue": true or false,
        "correction": "one sentence correction or null"
    }},
    "pressure_question": "one tough follow-up question",
    "lifeline_question": "one supportive follow-up question",
    "star_feedback": "which STAR component is missing or null if complete",
    "confidence_score": a number from 1 to 10
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text
    # delete transcript from memory immediately
    del transcript

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}