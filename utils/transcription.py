"""
Transcription and Voice Command Processing Module.

Handles audio transcription via OpenAI API with configurable models,
fallback support, legal vocabulary prompt injection, voice command detection,
and draft legal notes generation.
"""

import io
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import openai
from openai import OpenAI
from utils.legal_vocabulary import get_legal_prompt_context, normalize_legal_terms

# Configurable model names with defaults
DEFAULT_TRANSCRIPTION_MODEL = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-live-transcribe")
DEFAULT_FINAL_MODEL = os.getenv("OPENAI_FINAL_TRANSCRIPTION_MODEL", "gpt-transcribe")

# Cache for compiled steno commands from JSON files
_STENO_RULES_CACHE: Optional[List[Tuple[re.Pattern, str, str]]] = None

# Conversational phrase guards to avoid false positive command replacements
CONVERSATIONAL_GUARDS = [
    # Full stop (e.g. came to a full stop)
    (re.compile(r'(\b(?:a|an|the|complete)\s+)full\s+stop\b', re.IGNORECASE), lambda m: m.group(1) + '§§GUARD_FS§§'),
    # Period (e.g. period of limitation, grace period)
    (re.compile(r'(\b(?:a|an|the|this|that|grace|cooling|waiting)\s+)period\b', re.IGNORECASE), lambda m: m.group(1) + '§§GUARD_PR§§'),
    (re.compile(r'\bperiod(\s+(?:of|for|in|from)\b)', re.IGNORECASE), lambda m: '§§GUARD_PR§§' + m.group(1)),
    # Enter (e.g. did not enter into agreement, to enter appearance)
    (re.compile(r'(\b(?:to|shall|did|not|will|cannot|may|might)\s+)enter\b', re.IGNORECASE), lambda m: m.group(1) + '§§GUARD_ENT§§'),
    (re.compile(r'\benter(\s+(?:into|upon|appearance|plea)\b)', re.IGNORECASE), lambda m: '§§GUARD_ENT§§' + m.group(1)),
    # Return (e.g. income tax return, return of plaint)
    (re.compile(r'(\b(?:tax|income|in|to|shall|file|filing)\s+)return\b', re.IGNORECASE), lambda m: m.group(1) + '§§GUARD_RET§§'),
    (re.compile(r'\breturn(\s+(?:of|to|from)\b)', re.IGNORECASE), lambda m: '§§GUARD_RET§§' + m.group(1)),
    # Point (e.g. point of law, next point)
    (re.compile(r'(\b(?:this|that|the|next|first|second|third|to)\s+)point\b', re.IGNORECASE), lambda m: m.group(1) + '§§GUARD_PT§§'),
    (re.compile(r'\bpoint(\s+(?:of|out|for|is|raised)\b)', re.IGNORECASE), lambda m: '§§GUARD_PT§§' + m.group(1)),
    # Colon (e.g. colon cancer, colon surgery)
    (re.compile(r'\bcolon(\s+(?:cancer|surgery|cleanse)\b)', re.IGNORECASE), lambda m: '§§GUARD_CLN§§' + m.group(1)),
]

GUARD_RESTORATIONS = [
    ('§§GUARD_FS§§', 'full stop'),
    ('§§GUARD_PR§§', 'period'),
    ('§§GUARD_ENT§§', 'enter'),
    ('§§GUARD_RET§§', 'return'),
    ('§§GUARD_PT§§', 'point'),
    ('§§GUARD_CLN§§', 'colon'),
]


def load_steno_rules(force_reload: bool = False) -> List[Tuple[re.Pattern, str, str]]:
    """
    Loads spoken stenography commands from training/steno_english.json
    and training/steno_marathi.json, compiles them into regex patterns,
    and returns a cached list sorted descending by command complexity.
    """
    global _STENO_RULES_CACHE
    if _STENO_RULES_CACHE is not None and not force_reload:
        return _STENO_RULES_CACHE

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    en_path = os.path.join(base_dir, "training", "steno_english.json")
    mr_path = os.path.join(base_dir, "training", "steno_marathi.json")

    raw_rules: List[Tuple[str, str]] = []

    # 1. Load English training JSON
    if os.path.exists(en_path):
        try:
            with open(en_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    cmd = item.get("spoken_command", "").strip()
                    sym = item.get("output_symbol", "")
                    if cmd:
                        raw_rules.append((cmd, sym))
        except Exception as e:
            print(f"Warning: Failed to load {en_path}: {e}")

    # 2. Load Marathi training JSON
    if os.path.exists(mr_path):
        try:
            with open(mr_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    cmd = item.get("spoken_command", "").strip()
                    sym = item.get("output_symbol", "")
                    if cmd:
                        raw_rules.append((cmd, sym))
        except Exception as e:
            print(f"Warning: Failed to load {mr_path}: {e}")

    # 3. Courtroom speech synonyms & variations
    court_synonyms = [
        ("next paragraph", "\n\n"),
        ("next line", "\n"),
        ("purna viram", "."),
        ("alpa viram", ","),
        ("prashna chinha", "?"),
        ("udgar chinha", "!"),
        ("फुल स्टॉप", "."),
        ("कॉमा", ","),
        ("पुढील परिच्छेद", "\n\n"),
        ("पुढील ओळ", "\n"),
        ("नवा परिच्छेद", "\n\n"),
        ("नया पैराग्राफ", "\n\n"),
        ("अगला पैराग्राफ", "\n\n"),
        ("नई लाइन", "\n"),
        ("अगली लाइन", "\n"),
        ("उद्धरण चिन्ह", '"'),
        ("विस्मयादिबोधक चिन्ह", "!"),
    ]
    for cmd, sym in court_synonyms:
        raw_rules.append((cmd, sym))

    # Deduplicate while preserving earliest rule
    seen = set()
    unique_rules: List[Tuple[str, str]] = []
    for cmd, sym in raw_rules:
        norm = cmd.lower()
        if norm not in seen:
            seen.add(norm)
            unique_rules.append((cmd, sym))

    # Sort descending by word count, then character length
    # This guarantees multi-word commands (e.g., 'into the square bracket', 'चौकोनी कंस सुरू')
    # match and convert before partial substrings (e.g., 'bracket', 'कंस सुरू')
    unique_rules.sort(key=lambda x: (len(x[0].split()), len(x[0])), reverse=True)

    compiled: List[Tuple[re.Pattern, str, str]] = []
    for cmd, sym in unique_rules:
        words = cmd.split()
        escaped_words = [re.escape(w) for w in words]
        body = r"\s+".join(escaped_words)
        # Unicode-safe boundaries that work for Latin, Devanagari, and diacritics
        pattern = re.compile(
            r"(?<![A-Za-z0-9\u0900-\u097F])" + body + r"(?![A-Za-z0-9\u0900-\u097F])",
            re.IGNORECASE,
        )
        compiled.append((pattern, sym, cmd))

    _STENO_RULES_CACHE = compiled
    return _STENO_RULES_CACHE


def process_voice_commands(text: str, enabled: bool = True) -> str:
    """
    Translates spoken dictation commands into courtroom punctuation, brackets,
    quotes, arithmetic, currency, and line/paragraph formatting based on
    training/steno_english.json and training/steno_marathi.json.

    Converts:
        - Parentheses, brackets, curly braces:
          "into bracket", "open bracket", "close parenthesis", "open square bracket",
          "into the square bracket", "into the curly brace", "कंसात", "कंस सुरू",
          "कंस पूर्ण", "चौकोनी कंस सुरू", "चौकोनी कंस बंद", "महिरपी कंस सुरू", etc.
        - Punctuation & Quotes:
          "full stop", "comma", "colon", "semicolon", "question mark", "exclamation mark",
          "open quote", "close quote", "single quote", "पूर्णविराम", "स्वल्पविराम",
          "प्रश्नचिन्ह", "उद्गारवाचक चिन्ह", "एकेरी अवतरण चिन्ह", "दुहेरी अवतरण चिन्ह", etc.
        - Math & Currency:
          "plus sign", "minus sign", "times sign", "divided by", "equals sign", "percent sign",
          "रुपये चिन्ह", "रु", "अधिक", "वजा", "गुणिले", "भागिले", "बरोबर", etc.
        - Line breaks & Paragraphs:
          "new line", "next line", "new paragraph", "paragraph break",
          "नवीन ओळ", "नवीन परिच्छेद", "पॅराग्राफ", etc.

    Conversational phrases (e.g. 'came to a full stop', 'period of limitation',
    'did not enter into agreement', 'income tax return') are carefully preserved.
    """
    if not enabled or not text:
        return text

    processed = text

    # Step 1: Guard conversational phrases to prevent false positive conversions
    for pat, repl in CONVERSATIONAL_GUARDS:
        processed = pat.sub(repl, processed)

    # Step 2: Apply steno command conversions from training JSONs
    rules = load_steno_rules()
    for pat, sym, _ in rules:
        processed = pat.sub(lambda m, s=sym: s, processed)

    # Step 3: Restore conversational phrases
    for placeholder, original in GUARD_RESTORATIONS:
        processed = processed.replace(placeholder, original)

    # Step 4: Formatting and spacing cleanups
    # 4a. Remove spaces after opening brackets
    processed = re.sub(r"([(\[{])\s+", r"\1", processed)

    # 4b. Remove spaces before closing brackets
    processed = re.sub(r"\s+([)\]}])", r"\1", processed)

    # 4c. Remove spaces before punctuation marks
    processed = re.sub(r"\s+([.,;:?!])", r"\1", processed)

    # 4d. Ensure single space follows punctuation / closing brackets if followed by word/number
    processed = re.sub(r"([.,;:?!])([A-Za-z0-9\u0900-\u097F])", r"\1 \2", processed)
    processed = re.sub(r"([)\]}])([A-Za-z0-9\u0900-\u097F])", r"\1 \2", processed)

    # 4e. Clean up spaces inside quotes
    processed = re.sub(r'"\s+([^"\n]+?)\s+"', r'"\1"', processed)
    processed = re.sub(r"'\s+([^'\n]+?)\s+'", r"'\1'", processed)

    # 4f. Clean up whitespace around newlines
    processed = re.sub(r"[ \t]*\n[ \t]*", "\n", processed)
    processed = re.sub(r"\n{3,}", "\n\n", processed)

    # 4g. Capitalize first letter of Latin sentences at start or after punctuation / newline
    def capitalize_match(match: re.Match) -> str:
        prefix = match.group(1)
        char = match.group(2)
        return prefix + char.upper()

    processed = re.sub(r"^(\s*)([a-z])", capitalize_match, processed)
    processed = re.sub(r"([.?!]\s+)([a-z])", capitalize_match, processed)
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
    
    # Pass language only if a specific single language is selected (Mixed / Auto detect omits language parameter to prevent forced translation)
    if language_code and language_code.lower() not in ("auto", "auto detect", "none", "mixed", "code-switching"):
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
    
    prompt = f"""You are an official Court Stenographer typing the Hon'ble Judge's dictated court order and proceedings.
Create a structured 'JUDGE'S DICTATION / COURT PROCEEDINGS — DRAFT' based ONLY on the following official spoken transcript.

CRITICAL INSTRUCTIONS:
1. Do NOT invent or assume any facts, dates, names, or statutes not present in the transcript.
2. If a section has no details in the transcript, write 'Not specified in proceedings'.
3. Maintain language fidelity: If the Judge's transcript is in English, write in English. If in Marathi, write in Marathi. If mixed English-Marathi code-switching, preserve the mixed language verbatim. NEVER translate.
4. Label clearly: 'Official Stenographer Draft — requires signature/review by the Hon'ble Presiding Judge.'
5. Adhere strictly to this exact outline:

JUDGE'S DICTATION & COURT PROCEEDINGS — DRAFT
---------------------------------------------
[Official Stenographer Draft — requires review by the Hon'ble Presiding Judge]

1. Order / Case Summary
2. Coram & Appearances (Hon'ble Judge, Counsel for Parties)
3. Submissions Recorded
4. Evidence / Exhibits / Affidavits Cited
5. Findings & Observations of the Bench
6. Operative Order / Directions Issued
7. Next Hearing Date & Compliance Schedule
8. Verbatim Key Dictation Excerpt

TRANSCRIPT:
{transcript}
"""

    if client:
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a precise Judicial Stenographer adhering strictly to the Judge's spoken record. You preserve original languages verbatim without translating."},
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
