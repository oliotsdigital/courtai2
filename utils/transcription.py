"""
Transcription and Voice Command Processing Module.

Handles audio transcription via OpenAI API with configurable models,
fallback support, legal vocabulary prompt injection, voice command detection,
and draft legal notes generation.
"""

import io
import os
import re
from typing import Any, Dict, Optional, Tuple

import openai
from openai import OpenAI
from utils.legal_vocabulary import get_legal_prompt_context, normalize_legal_terms

# Configurable model names with defaults
DEFAULT_TRANSCRIPTION_MODEL = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-live-transcribe")
DEFAULT_FINAL_MODEL = os.getenv("OPENAI_FINAL_TRANSCRIPTION_MODEL", "gpt-transcribe")


def process_voice_commands(text: str, enabled: bool = True) -> str:
    """
    Translates spoken dictation commands into courtroom punctuation and paragraph formatting.
    
    Commands supported:
        - "full stop" / "period" -> .
        - "comma" -> ,
        - "colon" -> :
        - "semicolon" -> ;
        - "question mark" -> ?
        - "exclamation mark" / "exclamation point" -> !
        - "next paragraph" / "new paragraph" -> \\n\\n
        - "new line" / "next line" -> \\n
        - "open quote" -> "
        - "close quote" -> "
        - "quote" -> "
    
    Preserves normal speech when words appear in conversational phrases
    (e.g., 'came to a full stop', 'period of limitation').
    """
    if not enabled or not text:
        return text

    processed = text

    # Paragraph and line breaks first (to avoid breaking on individual punctuation later)
    # Support "next paragraph", "new paragraph", "paragraph break"
    processed = re.sub(
        r"(?i)\b(?:next\s+paragraph|new\s+paragraph|paragraph\s+break)\b",
        "\n\n",
        processed
    )
    
    # "new line" / "next line"
    processed = re.sub(
        r"(?i)\b(?:next\s+line|new\s+line)\b",
        "\n",
        processed
    )

    # Spoken full stop / period:
    # Preserve conversational phrases like "a full stop" or "period of limitation"
    def _full_stop_repl(m: re.Match) -> str:
        prev = m.group(1) or ""
        if prev.strip().lower() in ("a", "an", "the", "complete"):
            return m.group(0)
        return prev + "."

    processed = re.sub(
        r"(?i)(\b[a-z]+\s+)?\bfull\s+stop\b",
        _full_stop_repl,
        processed
    )

    def _period_repl(m: re.Match) -> str:
        prev = m.group(1) or ""
        post = m.group(2) or ""
        if prev.strip().lower() in ("a", "the", "this", "that", "grace", "cooling", "waiting") or post.strip().lower() in ("of", "for", "in", "from"):
            return m.group(0)
        return prev + "." + post

    processed = re.sub(
        r"(?i)(\b[a-z]+\s+)?\bperiod\b(\s+[a-z]+)?",
        _period_repl,
        processed
    )

    # Question mark & Exclamation mark
    processed = re.sub(r"(?i)\bquestion\s+mark\b", "?", processed)
    processed = re.sub(r"(?i)\bexclamation\s+(?:mark|point)\b", "!", processed)

    # Comma, Colon, Semicolon
    processed = re.sub(r"(?i)\bcomma\b", ",", processed)
    processed = re.sub(r"(?i)\bsemicolon\b", ";", processed)
    processed = re.sub(r"(?i)\bcolon\b(?!\s+(?:cancer|surgery|cleanse))", ":", processed)

    # Quotes
    processed = re.sub(r"(?i)\b(?:open\s+quote|quote\s+open)\b", '"', processed)
    processed = re.sub(r"(?i)\b(?:close\s+quote|quote\s+close)\b", '"', processed)
    processed = re.sub(r"(?i)\bquote\s+unquote\b", '"', processed)

    # Vernacular spoken paragraph & line breaks (Hindi & Marathi)
    processed = re.sub(
        r"(?:^|\s)(?:नवीन\s*परिच्छेद|पुढील\s*परिच्छेद|नवा\s*परिच्छेद|नया\s*पैराग्राफ|अगला\s*पैराग्राफ)(?=\s|$)",
        "\n\n",
        processed
    )
    processed = re.sub(
        r"(?:^|\s)(?:नवीन\s*ओळ|पुढील\s*ओळ|नई\s*लाइन|अगली\s*लाइन)(?=\s|$)",
        "\n",
        processed
    )

    # Indian vernacular spoken punctuation (Hindi/Marathi)
    processed = re.sub(r"(?:^|\s)(?:purna\s+viram|पूर्ण\s*विराम|पूर्णविराम|फुल\s*स्टॉप)(?=\s|[.,;:?!]|$)", ".", processed)
    processed = re.sub(r"(?:^|\s)(?:alpa\s+viram|अल्प\s*विराम|अल्पविराम|स्वल्प\s*विराम|स्वल्पविराम|कॉमा)(?=\s|[.,;:?!]|$)", ",", processed)
    processed = re.sub(r"(?:^|\s)(?:prashna\s+chinha|प्रश्न\s*चिन्ह|प्रश्नचिन्ह)(?=\s|[.,;:?!]|$)", "?", processed)
    processed = re.sub(r"(?:^|\s)(?:उद्गार\s*चिन्ह|उद्गारवाचक\s*चिन्ह|विस्मयादिबोधक\s*चिन्ह)(?=\s|[.,;:?!]|$)", "!", processed)
    processed = re.sub(r"(?:^|\s)(?:अपूर्ण\s*विराम|कोलन)(?=\s|[.,;:?!]|$)", ":", processed)
    processed = re.sub(r"(?:^|\s)(?:अर्ध\s*विराम|अर्धविराम)(?=\s|[.,;:?!]|$)", ";", processed)
    processed = re.sub(r"(?:^|\s)(?:उद्धरण\s*चिन्ह|अवतरण\s*चिन्ह)(?=\s|$)", ' "', processed)

    # Formatting and spacing cleanup:
    # 1. Remove spaces before punctuation marks
    processed = re.sub(r"\s+([.,;:?!])", r"\1", processed)

    # 2. Ensure a single space follows punctuation when followed by letters/digits (Latin & Devanagari)
    processed = re.sub(r"([.,;:?!])([A-Za-z0-9\u0900-\u097F])", r"\1 \2", processed)

    # 3. Clean up spaces around newlines
    processed = re.sub(r"[ \t]*\n[ \t]*", "\n", processed)
    processed = re.sub(r"\n{3,}", "\n\n", processed)

    # 4. Capitalize first letter of each sentence and after paragraph breaks (for Latin text)
    def capitalize_match(match: re.Match) -> str:
        prefix = match.group(1)
        char = match.group(2)
        return prefix + char.upper()

    # Beginning of text
    processed = re.sub(r"^(\s*)([a-z])", capitalize_match, processed)
    # After [.?!] followed by whitespace
    processed = re.sub(r"([.?!]\s+)([a-z])", capitalize_match, processed)
    # After newline
    processed = re.sub(r"(\n+)([a-z])", capitalize_match, processed)

    return processed.strip()


def get_openai_client(api_key: Optional[str] = None) -> Optional[OpenAI]:
    """
    Initializes and returns an OpenAI client if a valid API key is present.
    """
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key or key.strip() in ("", "your_key_here", "your_openai_api_key"):
        return None
    return OpenAI(api_key=key.strip())


def transcribe_audio_file(
    audio_bytes: bytes,
    filename: str = "court_recording.wav",
    language_code: Optional[str] = None,
    apply_vocab: bool = True,
    apply_commands: bool = True,
    api_key: Optional[str] = None,
    preferred_model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sends recorded audio to OpenAI's speech-to-text API using gpt-live-transcribe.
    
    Features:
        - Uses requested speech model (defaults to gpt-live-transcribe)
        - Injects legal terminology prompt context into OpenAI API
        - Applies voice command processing
        - Applies legal vocabulary normalization
        - Preserves raw transcript and error details
    """
    if not audio_bytes or len(audio_bytes) < 100:
        return {
            "success": False,
            "error": "The recorded audio is empty or too short. Please speak clearly into your microphone.",
            "raw_text": "",
            "processed_text": "",
            "model_used": None,
        }

    client = get_openai_client(api_key)
    if client is None:
        return {
            "success": False,
            "error": "OpenAI API key not configured. Please add OPENAI_API_KEY to your .env file or environment.",
            "raw_text": "",
            "processed_text": "",
            "model_used": None,
        }

    target_model = preferred_model or os.getenv("OPENAI_TRANSCRIPTION_MODEL", DEFAULT_TRANSCRIPTION_MODEL)
    legal_prompt = get_legal_prompt_context(language_code)

    # Prepare file-like object in memory
    audio_buffer = io.BytesIO(audio_bytes)
    audio_buffer.name = filename

    # Build parameters for OpenAI Audio Transcriptions
    params: Dict[str, Any] = {
        "file": audio_buffer,
        "model": target_model,
        "prompt": legal_prompt,
        "response_format": "text",
    }
    
    # Pass language only if specified (Auto detect omits language parameter)
    if language_code and language_code.lower() not in ("auto", "auto detect", "none"):
        params["language"] = language_code.lower()

    raw_text = ""
    model_used = target_model
    routing_note = None

    try:
        response = client.audio.transcriptions.create(**params)
        raw_text = response if isinstance(response, str) else getattr(response, "text", str(response))
    except Exception as err:
        err_msg = str(err)
        # If gpt-live-transcribe returns 404 (endpoint only accepts gpt-transcribe / gpt-4o-transcribe for POST audio)
        if ("404" in err_msg or "Invalid URL" in err_msg) and target_model == "gpt-live-transcribe":
            try:
                audio_buffer.seek(0)
                params["model"] = "gpt-transcribe"
                model_used = "gpt-transcribe"
                routing_note = "gpt-live-transcribe requires WebSockets; processed via gpt-transcribe."
                response = client.audio.transcriptions.create(**params)
                raw_text = response if isinstance(response, str) else getattr(response, "text", str(response))
            except Exception as retry_err:
                return {
                    "success": False,
                    "error": f"OpenAI API Error: {str(retry_err)}",
                    "raw_text": "",
                    "processed_text": "",
                    "model_used": model_used,
                }
        elif "AuthenticationError" in err_msg or "Invalid API Key" in err_msg:
            return {
                "success": False,
                "error": "Invalid OpenAI API Key. Please verify your OPENAI_API_KEY in .env.",
                "raw_text": "",
                "processed_text": "",
                "model_used": target_model,
            }
        elif "RateLimitError" in err_msg or "rate limit" in err_msg.lower():
            return {
                "success": False,
                "error": "OpenAI API rate limit exceeded. Please check your account quota and billing.",
                "raw_text": "",
                "processed_text": "",
                "model_used": target_model,
            }
        else:
            return {
                "success": False,
                "error": f"OpenAI API Error ({target_model}): {err_msg}",
                "raw_text": "",
                "processed_text": "",
                "model_used": target_model,
            }

    # Step 1: Voice command translation
    command_processed = process_voice_commands(raw_text, enabled=apply_commands)

    # Step 2: Legal vocabulary normalization
    final_text = normalize_legal_terms(command_processed, enabled=apply_vocab, language_code=language_code)

    return {
        "success": True,
        "error": None,
        "raw_text": raw_text.strip(),
        "processed_text": final_text.strip(),
        "model_used": model_used,
        "routing_note": routing_note,
    }


def generate_draft_proceedings(transcript: str, api_key: Optional[str] = None) -> str:
    """
    Generates a structured Draft Proceedings / Judgment Notes document from the transcript.
    Strictly follows the courtroom structure requested:
        - Case Summary
        - Appearances
        - Submissions
        - Evidence / Statements
        - Issues Discussed
        - Orders / Directions Mentioned
        - Important Dates
        - Transcript Reference
    
    If OpenAI API is available, uses gpt-4o-mini to organize the facts faithfully
    without fabricating facts. If offline/unavailable, formats the transcript
    into a structured template.
    """
    if not transcript or not transcript.strip():
        return "No transcript content available to generate a draft."

    client = get_openai_client(api_key)
    
    prompt = f"""You are a courtroom legal secretary assisting a judicial bench.
Create a structured 'COURT PROCEEDINGS — DRAFT' based ONLY on the following official spoken transcript.

CRITICAL INSTRUCTIONS:
1. Do NOT invent or assume any facts, dates, names, or statutes not present in the transcript.
2. If a section has no details in the transcript, write 'Not specified in proceedings'.
3. Label clearly: 'AI-generated draft — requires review by the presiding authority/legal professional.'
4. Adhere strictly to this exact outline:

COURT PROCEEDINGS — DRAFT
-------------------------
[Disclaimer: AI-generated draft — requires review by the presiding authority/legal professional.]

1. Case Summary
2. Appearances (Learned Counsel / Parties Present)
3. Submissions (Key arguments made by parties)
4. Evidence / Statements
5. Issues Discussed
6. Orders / Directions Mentioned
7. Important Dates (Next hearing date, filing deadlines)
8. Transcript Reference (Verbatim key excerpt)

TRANSCRIPT:
{transcript}
"""

    if client:
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a precise judicial clerk adhering strictly to the court record."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )
            content = completion.choices[0].message.content
            return content or "Failed to generate draft content."
        except Exception:
            pass  # Fallback to local template below

    # Deterministic local structuring fallback
    lines = [line.strip() for line in transcript.split("\n") if line.strip()]
    summary_excerpt = lines[0] if lines else "Courtroom proceedings recorded."
    
    return f"""COURT PROCEEDINGS — DRAFT
-------------------------
[Disclaimer: AI-generated draft — requires review by the presiding authority/legal professional.]

1. Case Summary
   {summary_excerpt}

2. Appearances
   - Applicant / Learned Counsel: Refer to recorded submissions.
   - Respondent: Refer to recorded submissions.

3. Submissions
   - Recorded submissions made during the hearing as noted in transcript below.

4. Evidence / Statements
   - Pleadings, affidavits, and exhibits referenced during proceedings.

5. Issues Discussed
   - Matters arising from current applications and statutory provisions cited.

6. Orders / Directions Mentioned
   - Directions issued by the Hon'ble Bench as stated in the record.

7. Important Dates
   - Next hearing and compliance dates as communicated by the Bench.

8. Transcript Reference
   "{transcript.strip()}"
"""
