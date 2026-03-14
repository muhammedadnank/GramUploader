"""
AI Service — Gemini
- generate_metadata()  → AI title, description, tags from video hint
- regenerate_title()   → Quick title regeneration
"""

import asyncio
import re
from utils.logger import log


def _get_gemini():
    from config import Config
    import google.generativeai as genai
    if not Config.GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY not set. Add it to .env")
    genai.configure(api_key=Config.GEMINI_API_KEY)
    return genai.GenerativeModel("gemini-1.5-flash")


async def generate_metadata(
    title_hint: str,
    description_hint: str = "",
    language: str = "en"
) -> dict:
    """
    Generate YouTube title, description, and tags using Gemini.
    Returns: {title, description, tags: []}
    """
    try:
        model = _get_gemini()

        lang_instruction = "Respond in Malayalam." if language == "ml" else "Respond in English."

        prompt = f"""You are a YouTube SEO expert. Generate metadata for a YouTube video.

Video hint: "{title_hint}"
Additional context: "{description_hint or 'None'}"

{lang_instruction}

Return ONLY a JSON object with these exact keys (no markdown, no explanation):
{{
  "title": "catchy YouTube title under 70 chars",
  "description": "engaging description 150-300 chars with relevant keywords",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"]
}}"""

        response = await asyncio.to_thread(
            lambda: model.generate_content(prompt)
        )

        raw = response.text.strip()
        raw = re.sub(r"```json|```", "", raw).strip()

        import json
        data = json.loads(raw)

        title = str(data.get("title", title_hint))[:100]
        description = str(data.get("description", ""))[:5000]
        tags = [str(t).strip() for t in data.get("tags", []) if t][:15]

        log.info(f"Gemini metadata generated for: {title_hint}")
        return {"title": title, "description": description, "tags": tags}

    except Exception as e:
        log.error(f"Gemini metadata error: {e}")
        raise Exception(f"AI metadata generation failed: {e}")


async def regenerate_title(current_title: str, language: str = "en") -> str:
    """Regenerate just the title — for quick retry"""
    try:
        model = _get_gemini()
        lang = "Malayalam" if language == "ml" else "English"
        prompt = (
            f'Generate a better YouTube title for a video called "{current_title}". '
            f'Respond in {lang}. Return ONLY the title text, nothing else. Max 70 chars.'
        )
        response = await asyncio.to_thread(lambda: model.generate_content(prompt))
        return response.text.strip()[:100]
    except Exception as e:
        raise Exception(f"Title regeneration failed: {e}")
