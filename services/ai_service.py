"""
AI Service — Gemini + Whisper
- generate_metadata()  → AI title, description, tags from video filename/caption
- generate_captions()  → Whisper speech-to-text → .srt file
"""

import asyncio
import os
import re
import tempfile
from utils.logger import log


# ─── GEMINI ─────────────────────────────────────────────────────────────────

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
        # Strip markdown code fences if present
        raw = re.sub(r"```json|```", "", raw).strip()

        import json
        data = json.loads(raw)

        # Validate and sanitize
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


# ─── WHISPER ─────────────────────────────────────────────────────────────────

def _format_srt_time(seconds: float) -> str:
    """Convert float seconds to SRT timestamp format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _segments_to_srt(segments: list) -> str:
    """Convert Whisper segments list to SRT format string"""
    srt_lines = []
    for i, seg in enumerate(segments, start=1):
        start = _format_srt_time(seg["start"])
        end = _format_srt_time(seg["end"])
        text = seg["text"].strip()
        srt_lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(srt_lines)


async def generate_captions(
    video_path: str,
    language: str = None,
    output_dir: str = None
) -> dict:
    """
    Transcribe video audio using Whisper.
    Returns: {srt_path, language_detected, duration_seconds}

    language: ISO code e.g. "en", "ml", "hi" — None = auto-detect
    """
    try:
        try:
            import whisper
        except ImportError:
            raise Exception("openai-whisper is not installed. Run: pip install openai-whisper")

        from config import Config
        model_name = Config.WHISPER_MODEL

        log.info(f"Loading Whisper model: {model_name}")

        # RAM check — Whisper base needs ~500MB, small needs ~1GB
        import psutil
        available_mb = psutil.virtual_memory().available / (1024 * 1024)
        required = {"tiny": 400, "base": 500, "small": 1100, "medium": 3000, "large": 6000}
        needed = required.get(model_name, 500)
        if available_mb < needed:
            raise Exception(
                f"Not enough RAM for Whisper '{model_name}' model. "
                f"Need ~{needed}MB, available {available_mb:.0f}MB. "
                f"Set WHISPER_MODEL=tiny in .env"
            )

        model = await asyncio.to_thread(whisper.load_model, model_name)

        # Extract audio from video using ffmpeg
        audio_path = video_path.replace(".mp4", ".wav").replace(".mkv", ".wav")
        if audio_path == video_path:
            audio_path = video_path + ".wav"

        log.info(f"Extracting audio from: {video_path}")
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            audio_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()

        if proc.returncode != 0:
            raise Exception("ffmpeg audio extraction failed")

        # Transcribe
        log.info("Transcribing with Whisper...")
        transcribe_kwargs = {"verbose": False}
        if language:
            transcribe_kwargs["language"] = language

        result = await asyncio.to_thread(
            lambda: model.transcribe(audio_path, **transcribe_kwargs)
        )

        # Build SRT
        srt_content = _segments_to_srt(result["segments"])
        detected_lang = result.get("language", "en")
        duration = result["segments"][-1]["end"] if result["segments"] else 0

        # Save SRT file
        out_dir = output_dir or os.path.dirname(video_path) or "/tmp"
        srt_path = os.path.join(out_dir, f"captions_{detected_lang}.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        # Cleanup audio
        try:
            os.remove(audio_path)
        except Exception:
            pass

        log.info(f"Captions generated: {srt_path} ({detected_lang})")
        return {
            "srt_path": srt_path,
            "language_detected": detected_lang,
            "duration_seconds": duration,
            "segment_count": len(result["segments"])
        }

    except Exception as e:
        log.error(f"Whisper caption error: {e}")
        raise Exception(f"Caption generation failed: {e}")
