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
from dotenv import load_dotenv

# Ensure .env is explicitly loaded from application root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"), override=True)

from utils.legal_vocabulary import get_legal_prompt_context, normalize_legal_terms

# Configurable model names with defaults
DEFAULT_TRANSCRIPTION_MODEL = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "whisper-1")
DEFAULT_FINAL_MODEL = os.getenv("OPENAI_FINAL_TRANSCRIPTION_MODEL", "whisper-1")

# Cache for compiled steno commands from JSON files
_STENO_RULES_CACHE: Optional[List[Tuple[re.Pattern, str, str]]] = None

# Conversational phrase guards to avoid false positive command replacements
CONVERSATIONAL_GUARDS = [
    # Full stop (e.g. came to a full stop)
    (re.compile(r'(\b(?:a|an|the|complete)\s+)full\s+stop\b', re.IGNORECASE), lambda m: m.group(1) + '§§GUARD_FS§§'),
    # Period (e.g. period of limitation, grace period, period already undergone)
    (re.compile(r'(\b(?:a|an|the|this|that|to|such|grace|cooling|waiting|limitation|probation|intervening)\s+)period\b', re.IGNORECASE), lambda m: m.group(1) + '§§GUARD_PR§§'),
    (re.compile(r'\bperiod(\s+(?:of|for|in|from|to|already|undergone|elapsed|specified)\b)', re.IGNORECASE), lambda m: '§§GUARD_PR§§' + m.group(1)),
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
    # Space (e.g. parking space, open space, space between, storage space)
    (re.compile(r'(\b(?:outer|parking|open|office|living|storage|empty|intervening|confined|cyber|air|personal)\s+)space\b', re.IGNORECASE), lambda m: m.group(1) + '§§GUARD_SP§§'),
    (re.compile(r'\bspace(\s+(?:between|available|crunch|station|craft|shuttle|exploration|travel|time)\b)', re.IGNORECASE), lambda m: '§§GUARD_SP§§' + m.group(1)),
    # Paragraph (e.g. paragraph 4, paragraph above, in this paragraph)
    (re.compile(r'(\b(?:in|of|from|under|refer\s+to|see|this|that|the|first|second|third|fourth|fifth|preceding|following|above|below)\s+)paragraph\b', re.IGNORECASE), lambda m: m.group(1) + '§§GUARD_PG§§'),
    (re.compile(r'\bparagraph(\s+(?:no|number|above|below|referred|of)\b)', re.IGNORECASE), lambda m: '§§GUARD_PG§§' + m.group(1)),
    # Line (e.g. line of control, line above, first line)
    (re.compile(r'(\b(?:of|in|on|along|under|across|between|the|this|that|first|second|third|bottom|top|fine|front)\s+)line\b', re.IGNORECASE), lambda m: m.group(1) + '§§GUARD_LN§§'),
    (re.compile(r'\bline(\s+(?:of|above|below|cross|crossed|crossing)\b)', re.IGNORECASE), lambda m: '§§GUARD_LN§§' + m.group(1)),
]

GUARD_RESTORATIONS = [
    ('§§GUARD_FS§§', 'full stop'),
    ('§§GUARD_PR§§', 'period'),
    ('§§GUARD_ENT§§', 'enter'),
    ('§§GUARD_RET§§', 'return'),
    ('§§GUARD_PT§§', 'point'),
    ('§§GUARD_CLN§§', 'colon'),
    ('§§GUARD_SP§§', 'space'),
    ('§§GUARD_PG§§', 'paragraph'),
    ('§§GUARD_LN§§', 'line'),
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
        # Spoken bracket variations
        ("in to the bracket", "("),
        ("in to the brackets", "("),
        ("into the bracket", "("),
        ("into the brackets", "("),
        ("in to bracket", "("),
        ("into bracket", "("),
        ("in the bracket", "("),
        ("in the brackets", "("),
        ("open bracket", "("),
        ("open the bracket", "("),
        ("bracket open", "("),
        ("brackets open", "("),
        ("start bracket", "("),
        ("bracket closed", ")"),
        ("brackets closed", ")"),
        ("bracket close", ")"),
        ("brackets close", ")"),
        ("close the bracket", ")"),
        ("close the brackets", ")"),
        ("close bracket", ")"),
        ("close brackets", ")"),
        ("bracket complete", ")"),
        ("bracket completed", ")"),
        ("bracket end", ")"),
        ("brackets end", ")"),
        ("out of bracket", ")"),
        ("out of the bracket", ")"),
        ("out of brackets", ")"),
        ("out of the brackets", ")"),
        
        # Commas & periods
        ("commas", ","),
        ("comma", ","),
        ("coma", ","),
        ("koma", ","),
        ("full stop", "."),
        ("full stops", "."),
        ("fullstop", "."),
        ("purna viram", "."),
        ("period", "."),
        
        # Quotes & inverted commas
        ("in to the quote", '"'),
        ("into the quote", '"'),
        ("in to the quotes", '"'),
        ("into the quotes", '"'),
        ("in to quotes", '"'),
        ("into quotes", '"'),
        ("in quotes", '"'),
        ("open quote", '"'),
        ("open quotes", '"'),
        ("quote open", '"'),
        ("quotes open", '"'),
        ("quote closed", '"'),
        ("quotes closed", '"'),
        ("close quote", '"'),
        ("close quotes", '"'),
        ("open inverted commas", '"'),
        ("close inverted commas", '"'),
        ("open inverted comma", '"'),
        ("close inverted comma", '"'),
        
        # Punctuation & math
        ("colon", ":"),
        ("colons", ":"),
        ("semicolon", ";"),
        ("semicolons", ";"),
        ("semi colon", ";"),
        ("semi colons", ";"),
        ("question mark", "?"),
        ("question marks", "?"),
        ("exclamation mark", "!"),
        ("exclamation point", "!"),
        ("hyphen", "-"),
        ("dash", "-"),
        
        # Spoken Vernacular (Transliterated)
        ("alpa viram", ","),
        ("alpaviram", ","),
        ("swalpa viram", ","),
        ("swalpaviram", ","),
        ("prashna chinha", "?"),
        ("udgar chinha", "!"),
        ("फुल स्टॉप", "."),
        ("कॉमा", ","),
        ("स्वल्पविराम", ","),
        ("अल्पविराम", ","),
        ("कंसात", "("),
        ("कंस सुरू", "("),
        ("कंस पूर्ण", ")"),
        ("कंस बंद", ")"),
        
        # Line & paragraph breaks & spaces
        ("start a new paragraph", "\n\n"),
        ("start new paragraph", "\n\n"),
        ("a next paragraph", "\n\n"),
        ("a new paragraph", "\n\n"),
        ("next paragraph", "\n\n"),
        ("new paragraph", "\n\n"),
        ("paragraph break", "\n\n"),
        ("start a new line", "\n"),
        ("start new line", "\n"),
        ("a next line", "\n"),
        ("a new line", "\n"),
        ("next line", "\n"),
        ("new line", "\n"),
        ("line break", "\n"),
        ("press enter", "\n"),
        ("blank space", " "),
        ("white space", " "),
        ("single space", " "),
        ("space bar", " "),
        ("a space", " "),
        ("give space", " "),
        ("add space", " "),
        ("insert space", " "),
        ("space", " "),
        ("tab space", "    "),
        ("tab key", "    "),
        ("indent", "    "),
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

    # Step 2b: Explicit guarantee: Convert any spoken 'comma' / 'commas' command variations into ','
    processed = re.sub(
        r"(?<![A-Za-z0-9\u0900-\u097F])(?:commas?|komas?|comas?|alpa\s+viram|alpaviram|swalpa\s+viram|swalpaviram|कॉमा|स्वल्पविराम|अल्पविराम)(?![A-Za-z0-9\u0900-\u097F])",
        ",",
        processed,
        flags=re.IGNORECASE,
    )
    # Deduplicate consecutive commas resulting from speech pauses (e.g. ", ,")
    processed = re.sub(r",\s*,+", ",", processed)

    # Step 2c: Explicit guarantee: Brackets ("in to the bracket", "into bracket", "open bracket" -> "(")
    processed = re.sub(
        r"(?<![A-Za-z0-9\u0900-\u097F])(?:in\s*to\s+(?:the\s+)?brackets?|into\s+(?:the\s+)?brackets?|in\s+(?:the\s+)?brackets?|open\s+(?:the\s+)?brackets?|brackets?\s+open|start\s+(?:the\s+)?brackets?|open\s+parenthes(?:is|es)|parenthes(?:is|es)\s+open)(?![A-Za-z0-9\u0900-\u097F])",
        "(",
        processed,
        flags=re.IGNORECASE,
    )
    # ("bracket closed", "brackets closed", "bracket close", "close bracket" -> ")")
    processed = re.sub(
        r"(?<![A-Za-z0-9\u0900-\u097F])(?:brackets?\s+closed|brackets?\s+close|close\s+(?:the\s+)?brackets?|close\s+brackets?|brackets?\s+complete[d]?|brackets?\s+end|out\s+of\s+(?:the\s+)?brackets?|close\s+parenthes(?:is|es)|parenthes(?:is|es)\s+closed)(?![A-Za-z0-9\u0900-\u097F])",
        ")",
        processed,
        flags=re.IGNORECASE,
    )

    # Step 2d: Explicit guarantee: Quotes ("in to the quote", "open quote" -> '"', "quote closed", "close quote" -> '"')
    processed = re.sub(
        r"(?<![A-Za-z0-9\u0900-\u097F])(?:in\s*to\s+(?:the\s+)?quotes?|into\s+(?:the\s+)?quotes?|open\s+(?:double\s+)?quotes?|quotes?\s+open|open\s+inverted\s+commas?|inverted\s+commas?\s+open)(?![A-Za-z0-9\u0900-\u097F])",
        '"',
        processed,
        flags=re.IGNORECASE,
    )
    processed = re.sub(
        r"(?<![A-Za-z0-9\u0900-\u097F])(?:quotes?\s+closed|quotes?\s+close|close\s+(?:the\s+)?quotes?|close\s+(?:double\s+)?quotes?|out\s+of\s+(?:the\s+)?quotes?|close\s+inverted\s+commas?|inverted\s+commas?\s+closed)(?![A-Za-z0-9\u0900-\u097F])",
        '"',
        processed,
        flags=re.IGNORECASE,
    )

    # Step 2e: Explicit guarantee: Full stops
    processed = re.sub(
        r"(?<![A-Za-z0-9\u0900-\u097F])(?:full\s*stops?|fullstops?)(?![A-Za-z0-9\u0900-\u097F])",
        ".",
        processed,
        flags=re.IGNORECASE,
    )

    # Step 2f: Explicit guarantee: Paragraph breaks ("next paragraph", "a new paragraph", "new paragraph", etc.)
    processed = re.sub(
        r"(?<![A-Za-z0-9\u0900-\u097F])(?:(?:start\s+)?(?:a\s+)?(?:next|new)\s+paragraphs?|paragraphs?\s+break)(?![A-Za-z0-9\u0900-\u097F])",
        "\n\n",
        processed,
        flags=re.IGNORECASE,
    )

    # Step 2g: Explicit guarantee: Line breaks ("next line", "new line", "a new line", "line break", etc.)
    processed = re.sub(
        r"(?<![A-Za-z0-9\u0900-\u097F])(?:(?:start\s+)?(?:a\s+)?(?:next|new)\s+lines?|lines?\s+break|press\s+enter|hit\s+enter)(?![A-Za-z0-9\u0900-\u097F])",
        "\n",
        processed,
        flags=re.IGNORECASE,
    )

    # Step 2h: Explicit guarantee: Spoken spaces ("blank space", "a space", "white space", "space bar", etc.)
    processed = re.sub(
        r"(?<![A-Za-z0-9\u0900-\u097F])(?:(?:add|give|insert)\s+(?:a\s+)?space|blank\s+space|white\s+space|single\s+space|space\s+bar|a\s+space)(?![A-Za-z0-9\u0900-\u097F])",
        " ",
        processed,
        flags=re.IGNORECASE,
    )
    # Standalone 'space' after punctuation mark
    processed = re.sub(r"(?<=[.,;:?!])\s*space(?![A-Za-z0-9\u0900-\u097F])", " ", processed, flags=re.IGNORECASE)

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

    # If the output consists purely of whitespace/breaks, preserve intentional break symbol
    if re.fullmatch(r"[\r\n\t ]*", processed):
        if "\n\n" in processed:
            return "\n\n"
        elif "\n" in processed:
            return "\n"
        elif " " in processed:
            return " "
        return ""

    # Strip horizontal spaces/tabs, preserving leading and trailing newlines
    return processed.strip(" \t")


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
    target_model: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Sends recorded audio to OpenAI's speech-to-text API (whisper-1).
    
    Features:
        - Uses requested speech model (defaults to whisper-1)
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
            "error": "OpenAI API key not configured. Please ensure OPENAI_API_KEY is properly set in your .env file.",
            "raw_text": "",
            "processed_text": "",
            "model_used": None,
        }

    target_model = preferred_model or target_model or os.getenv("OPENAI_TRANSCRIPTION_MODEL", DEFAULT_TRANSCRIPTION_MODEL) or "whisper-1"
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
        # If model is not recognized or returns 404, fallback to whisper-1
        if ("404" in err_msg or "Invalid URL" in err_msg or "model_not_found" in err_msg.lower() or "does not exist" in err_msg.lower() or target_model == "gpt-live-transcribe"):
            for fallback_model in ["whisper-1", "gpt-transcribe"]:
                if fallback_model == target_model:
                    continue
                try:
                    audio_buffer.seek(0)
                    params["model"] = fallback_model
                    model_used = fallback_model
                    routing_note = f"Processed via {fallback_model}."
                    response = client.audio.transcriptions.create(**params)
                    raw_text = response if isinstance(response, str) else getattr(response, "text", str(response))
                    break
                except Exception:
                    continue
            if not raw_text:
                return {
                    "success": False,
                    "error": f"OpenAI API Error: {err_msg}",
                    "raw_text": "",
                    "processed_text": "",
                    "model_used": model_used,
                }
        if "401" in err_msg or "invalid" in err_msg.lower() or "authentication" in err_msg.lower():
            return {
                "success": False,
                "error": "OpenAI API Key is invalid or expired (Error 401). Please check the OPENAI_API_KEY in your .env file, or switch Live Engine to 'Browser Native'.",
                "raw_text": "",
                "processed_text": "",
                "model_used": target_model,
            }
        elif "429" in err_msg or "rate limit" in err_msg.lower() or "quota" in err_msg.lower():
            return {
                "success": False,
                "error": "OpenAI API quota / credits exhausted (Error 429). Please check your OpenAI account credits or switch Live Engine to 'Browser Native'.",
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
3. Maintain language fidelity: The transcript and proceedings are strictly in Indian English. Preserve all citations, sections, and legal terminology verbatim.
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
                    {"role": "system", "content": "You are a precise Judicial Stenographer adhering strictly to the Judge's spoken Indian English record. You transcribe courtroom English verbatim."},
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
