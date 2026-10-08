"""
CourtScribe AI - Flask Backend
Judicial Stenographer & Courtroom Speech-to-Text Application (English Only)

Supports:
1. Real-Time Streaming Dictation (Browser Web Speech API + Live Steno Rules)
2. Audio File & Recording Transcription (OpenAI Audio API with legal context)
3. Spoken Steno Shorthand Translation (e.g. "comma" -> ",", "full stop" -> ".")
4. Courtroom Legal Formatting & Normalization (PW-1, Ex.P1, MO-1, Section 302/34, RI 5 years)
5. Judge's Proceedings & Order Draft Generation
6. Word (.docx) and PDF Document Exports
"""

import os
from datetime import datetime
import io
from typing import Dict, Any

from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

# Load environment variables explicitly from .env file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"), override=True)

# Import core business logic
from utils.transcription import (
    transcribe_audio_file,
    process_voice_commands,
    generate_draft_proceedings,
    get_openai_client,
)
from utils.legal_vocabulary import (
    normalize_legal_terms,
    LEGAL_TERMS_EN,
)
from utils.exporters import export_to_docx, export_to_pdf
from utils.realtime_bridge import (
    get_or_create_session,
    close_session,
    _ACTIVE_SESSIONS,
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB maximum upload size
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# Dual-WebSocket Architecture: Flask-SocketIO Middleman
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Pre-defined Judicial Samples (English Only)
JUDICIAL_SAMPLES: Dict[str, Dict[str, str]] = {
    "data1": {
        "title": "High Court Murder Appeal Judgment (english_data_1.txt)",
        "description": "Criminal Appeal setting aside acquittal: PW-1 to PW-10, Ex.P1 to Ex.P21, MO-1 to MO-17, Inquest Mahazar, FSL report, Section 302 read with Section 34 IPC.",
        "text": (
            "S.C. Sharma, J.\n\n"
            "1. Mallappa S/o. Ningappa Kanner, Hanamanth S/o. Ningappa Kanner and Dharamanna S/o. Ningappa Kanner "
            "are the Appellants before us who were put on trial, as Accused Nos. 3, 4 and 5, for the commission of murder "
            "of deceased Marthandappa and were acquitted by the Trial Court/Fast Track Court-I at Gulbarga on 24.03.2005. "
            "The State of Karnataka preferred Criminal Appeal No. 1363/2005 before the High Court which reversed the order of acquittal and "
            "convicted the Appellants under Section 302 read with Section 34 of the Indian Penal Code.\n\n"
            "2. An FIR was registered against Accused persons as Crime No. 78/97 and sent through PW-1 to the JMFC, Shorapur. "
            "In the presence of Panchas (PW-7 and Malleshi), PW-10 conducted inquest mahazar on the dead body of Marthandappa as per Ex.P9. "
            "From the scene of offence, he seized MO-1 (bullock-cart peg), MO-12 (pair of chappal), MO-13 (towel) and MO-14 (blood stained mud). "
            "PW-5 (doctor) conducted post-mortem examination and found 9 ante-mortem injuries, issuing post-mortem report Ex.P3 stating the cause "
            "of death to be haemorrhage shock.\n\n"
            "3. FSL report was received as Ex.P19 and Ex.P20. The prosecution examined PW-1 to PW-10 and marked Ex.P1 to Ex.P21 as well as MOs 1 to 17. "
            "The defence marked Ex.D1. During cross-examination, PW-4 admitted material contradictions with the wound certificate Ex.P12. "
            "Per contra, learned counsel for the Respondent State submitted that PW-3 was an ocular witness and PW-4 was an injured witness.\n\n"
            "4. Accused Nos. 1 to 5 are brothers inter se. The chain of circumstances fails to establish mens rea or exclude reasonable doubt. "
            "The impugned judgment of the High Court is set aside, and the order of acquittal of the Trial Court is restored. "
            "The Appellants are acquitted of all charges and directed to be released forthwith."
        ),
    },
    "data2": {
        "title": "High Court Sentencing Modification Order (english_data_2.txt)",
        "description": "Criminal Appeal conviction modification: Tailoring scissors weapon, hostile witnesses, compromise deed, Section 307 vs 326 IPC, RI sentences.",
        "text": (
            "Rajesh Bindal, J.\n"
            "Leave granted.\n\n"
            "1. The Accused has filed the present appeal challenging his conviction and sentence. "
            "The impugned judgment of the High Court is under appeal vide which the judgment and order of sentence passed by the Trial Court was upheld. "
            "The conviction and sentence of the Appellant is as under:\n"
            "- Section 341 Indian Penal Code: RI 1 month.\n"
            "- Section 506B Indian Penal Code: RI 6 months.\n"
            "- Section 307 Indian Penal Code: RI 5 years and fine of ₹ 1,500/-, in default of payment to further undergo RI 1 year.\n\n"
            "2. The case of the prosecution as evident from the FIR is that the complainant Salikram was stopped and threatened by the Appellant. "
            "Rajkumar alias Munna (PW-6) was also with him. The Appellant caused incised injuries on the left thigh with scissors. "
            "The injured appeared as PW-1, whereas Kantilal (PW-8) and Radhey Shyam (PW-7) were declared hostile.\n\n"
            "3. Learned Counsel for the Appellant submitted that it is a case of sudden fight without mens rea, and placed on record a compromise deed dated 30.04.2019. "
            "The weapon used is small scissors used by tailors. In our view, the offence will not fall within Section 307 Indian Penal Code, but falls within "
            "the four corners of Section 326 Indian Penal Code as a sharp-edged weapon was used without intention to cause death.\n\n"
            "4. At the time of hearing, it was pointed out that the Appellant had already undergone actual sentence of 11 months and 24 days. "
            "In our view, the sentence awarded to the Appellant deserves to be reduced to the period already undergone. "
            "The amount of fine imposed is sustained. The impugned judgments passed by the Courts below are modified to the extent mentioned above and the appeal is allowed."
        ),
    },
    "dictation": {
        "title": "Judge's Oral Dictation in Open Court (Bail Application)",
        "description": "Realistic court dictation: Section 439 CrPC interim bail, surety bond, passport surrender, and adjournment.",
        "text": (
            "Order dictated in open court.\n\n"
            "1. The applicant is present before the Hon'ble Court and represented by Learned Counsel. "
            "This is an application for grant of interim bail filed under Section 439 of the CrPC.\n\n"
            "2. The Court has heard the submissions of both parties and perused the police case diary. "
            "The Learned Counsel for the applicant submits that the applicant has no prior criminal antecedents "
            "and undertakes to cooperate fully with the investigating officer.\n\n"
            "3. Considering the facts on record, the applicant is granted interim bail upon furnishing a personal bond "
            "of ₹ 25,000/- with one solvent surety in the like amount to the satisfaction of the Registrar.\n\n"
            "4. The applicant shall surrender his passport before the Court and shall not attempt to influence "
            "the prosecution witnesses PW-1 and PW-2. The respondent is granted two weeks time to file the reply affidavit.\n\n"
            "5. The matter is adjourned to the next date of hearing. All parties to act on an authenticated copy of this order."
        ),
    },
}


@app.route("/")
def index():
    """Renders the main English Judicial Stenographer web application."""
    has_api_key = bool(os.getenv("OPENAI_API_KEY", "").strip())
    return render_template(
        "index.html",
        has_api_key=has_api_key,
        samples=JUDICIAL_SAMPLES,
        legal_terms_count=len(LEGAL_TERMS_EN),
    )


@app.route("/health")
def health():
    """Container healthcheck endpoint for Coolify / Docker."""
    return jsonify({"status": "ok", "app": "CourtScribe AI (Flask English)", "port": 8501})


@app.route("/api/samples/<sample_id>")
def get_sample(sample_id: str):
    """Returns sample judicial transcript by ID."""
    sample = JUDICIAL_SAMPLES.get(sample_id)
    if not sample:
        return jsonify({"success": False, "error": f"Sample '{sample_id}' not found."}), 404
    return jsonify({
        "success": True,
        "sample_id": sample_id,
        "title": sample["title"],
        "text": sample["text"],
    })


@app.route("/api/transcribe", methods=["POST"])
def transcribe_audio():
    """
    Transcribes uploaded or recorded audio via OpenAI Audio API (English Only).
    Pipes result through voice commands and legal normalization.
    """
    if "audio_file" not in request.files:
        return jsonify({"success": False, "error": "No audio file provided in request."}), 400

    audio_file = request.files["audio_file"]
    if audio_file.filename == "":
        return jsonify({"success": False, "error": "Selected audio file has an empty filename."}), 400

    audio_bytes = audio_file.read()
    if not audio_bytes:
        return jsonify({"success": False, "error": "Audio file is empty (0 bytes)."}), 400

    # Optional custom API key from client request header or form
    custom_key = request.form.get("api_key", "").strip() or None
    target_model = request.form.get("model", "gpt-transcribe").strip()
    
    # English language code
    language_code = request.form.get("language_code", "en").strip().lower()
    if not language_code.startswith("en"):
        language_code = "en"

    # Execute transcription pipeline
    result = transcribe_audio_file(
        audio_bytes=audio_bytes,
        filename=audio_file.filename or "recording.webm",
        target_model=target_model,
        api_key=custom_key,
        language_code=language_code,
        apply_commands=True,
        apply_vocab=True,
    )

    return jsonify(result)


@app.route("/api/transcribe-live-chunk", methods=["POST"])
def transcribe_live_chunk():
    """
    Transcribes a live streaming microphone audio chunk via OpenAI Audio API (Whisper).
    Returns processed text with spoken steno commands and legal normalization.
    """
    audio_file = request.files.get("audio_chunk") or request.files.get("audio_file")
    if not audio_file:
        return jsonify({"success": False, "error": "No audio chunk received."}), 400

    audio_bytes = audio_file.read()
    if not audio_bytes or len(audio_bytes) < 100:
        return jsonify({"success": True, "text": "", "empty": True})

    custom_key = request.form.get("api_key", "").strip() or request.headers.get("X-OpenAI-Key", "").strip() or None
    target_model = request.form.get("model", "whisper-1").strip()
    language_code = "en"

    result = transcribe_audio_file(
        audio_bytes=audio_bytes,
        filename=audio_file.filename or "chunk.webm",
        target_model=target_model,
        api_key=custom_key,
        language_code=language_code,
        apply_commands=True,
        apply_vocab=True,
    )

    if not result.get("success"):
        return jsonify({
            "success": False,
            "error": result.get("error", "Transcription failed."),
            "model_used": result.get("model_used"),
        }), 400

    return jsonify({
        "success": True,
        "text": result.get("processed_text", ""),
        "raw_text": result.get("raw_text", ""),
        "model_used": result.get("model_used"),
    })


@app.route("/api/normalize", methods=["POST"])
def normalize_text():
    """
    Applies steno voice command translation ('comma' -> ',', 'full stop' -> '.')
    and legal vocabulary normalization (PW-1, Ex.P1, MO-1, Sections, RI) locally.
    """
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    if not text.strip():
        return jsonify({"success": False, "error": "No text provided to normalize."}), 400

    # Step 1: Voice command conversion
    with_commands = process_voice_commands(text, enabled=True)

    # Step 2: Legal vocabulary normalization (English)
    normalized = normalize_legal_terms(with_commands, enabled=True, language_code="en")

    return jsonify({
        "success": True,
        "original_text": text,
        "normalized_text": normalized,
    })


@app.route("/api/generate-draft", methods=["POST"])
def generate_draft():
    """
    Generates a structured Judge's Order / Court Proceedings draft from the transcript.
    Uses gpt-4o-mini if OpenAI is configured, with automatic offline template fallback.
    """
    data = request.get_json(silent=True) or {}
    transcript = data.get("transcript", "")
    custom_key = data.get("api_key", "").strip() or None

    if not transcript.strip():
        return jsonify({"success": False, "error": "Transcript content is empty."}), 400

    draft = generate_draft_proceedings(transcript, api_key=custom_key)
    return jsonify({
        "success": True,
        "draft": draft,
    })


@app.route("/api/export/docx", methods=["POST"])
def export_docx():
    """Exports the current transcript or draft to Microsoft Word (.docx)."""
    text = request.form.get("text", "") or (request.get_json(silent=True) or {}).get("text", "")
    title = request.form.get("title", "COURT PROCEEDINGS / JUDGE'S DICTATION") or "COURT PROCEEDINGS"
    case_no = request.form.get("case_no", "") or "Not Specified"

    if not text.strip():
        return jsonify({"success": False, "error": "No transcript content to export."}), 400

    metadata = {
        "title": title,
        "subtitle": "Official Judicial Stenographer Record (English)",
        "language": "English (Courtroom Stenography)",
        "case_no": case_no,
        "date": datetime.now().strftime("%d %B %Y, %I:%M %p"),
    }

    docx_io = export_to_docx(text, metadata=metadata)
    docx_io.seek(0)

    filename = f"Court_Transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    return send_file(
        docx_io,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.route("/api/export/pdf", methods=["POST"])
def export_pdf():
    """Exports the current transcript or draft to Court-formatted PDF."""
    text = request.form.get("text", "") or (request.get_json(silent=True) or {}).get("text", "")
    title = request.form.get("title", "COURT PROCEEDINGS / JUDGE'S DICTATION") or "COURT PROCEEDINGS"
    case_no = request.form.get("case_no", "") or "Not Specified"

    if not text.strip():
        return jsonify({"success": False, "error": "No transcript content to export."}), 400

    metadata = {
        "title": title,
        "subtitle": "Official Judicial Stenographer Record (English)",
        "language": "English (Courtroom Stenography)",
        "case_no": case_no,
        "date": datetime.now().strftime("%d %B %Y, %I:%M %p"),
    }

    pdf_io = export_to_pdf(text, metadata=metadata)
    pdf_io.seek(0)

    filename = f"Court_Transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(
        pdf_io,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )


# =====================================================================
# Dual-WebSocket Socket.IO Event Handlers
# =====================================================================

@socketio.on("connect")
def handle_socket_connect():
    """Client connected to Flask-SocketIO."""
    sid = request.sid
    # Connected successfully


@socketio.on("start_realtime_dictation")
def handle_start_realtime(data=None):
    """
    Client requested start of live real-time dictation session.
    Spawns RealtimeTranscriptionSession connecting to OpenAI wss://.
    """
    data = data or {}
    lang = data.get("language_code", "en")
    sid = request.sid

    session = get_or_create_session(sid, socketio, language_code=lang)
    emit("realtime_status", {"status": "starting", "model": session.model_name})


@socketio.on("audio_chunk")
def handle_audio_chunk(data):
    """
    Receives raw 16-bit linear PCM audio chunk from client microphone
    and pushes it to the OpenAI Realtime background queue.
    """
    sid = request.sid
    session = _ACTIVE_SESSIONS.get(sid)
    if not session:
        return

    if isinstance(data, (bytes, bytearray)):
        session.push_audio_chunk(bytes(data))
    elif isinstance(data, dict) and "chunk" in data:
        import base64
        raw = base64.b64decode(data["chunk"])
        session.push_audio_chunk(raw)


@socketio.on("stop_realtime_dictation")
def handle_stop_realtime():
    """Client stopped live dictation; closes OpenAI Realtime WebSocket."""
    sid = request.sid
    close_session(sid)
    emit("realtime_status", {"status": "stopped"})


@socketio.on("disconnect")
def handle_socket_disconnect():
    """Client disconnected; clean up session."""
    sid = request.sid
    close_session(sid)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8501"))
    debug = os.getenv("FLASK_ENV", "production").lower() == "development"
    print(f"\n=======================================================")
    print(f"🏛️  CourtScribe AI - English Judicial Stenographer Server")
    print(f"📍 Local URL: http://localhost:{port}")
    print(f"🔒 Mode: English Language Only (Dual-WebSocket Realtime Engine)")
    print(f"=======================================================\n")
    socketio.run(app, host="0.0.0.0", port=port, debug=debug, allow_unsafe_werkzeug=True)

