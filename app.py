"""
CourtScribe AI — Real-time Courtroom Speech-to-Text
Professional Courtroom Transcription Workstation Streamlit Application.
"""

from datetime import datetime
import hashlib
import os
import sys
from typing import Optional

from dotenv import load_dotenv
import streamlit as st
import streamlit.components.v1 as components

# Ensure local utils can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Directory for live streaming component
_recorder_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "live_recorder")

from utils.exporters import export_to_docx, export_to_pdf
from utils.legal_vocabulary import LEGAL_TERMS, normalize_legal_terms
from utils.transcription import (
    DEFAULT_TRANSCRIPTION_MODEL,
    generate_draft_proceedings,
    get_openai_client,
    process_voice_commands,
    transcribe_audio_file,
)

# Load environment variables
load_dotenv()

# Streamlit Page Configuration
st.set_page_config(
    page_title="CourtScribe AI — Courtroom Speech-to-Text",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Professional Courtroom Workstation CSS
st.markdown(
    """
    <style>
    /* Global Background and Fonts */
    .stApp {
        background-color: #F8FAFC;
        color: #0F172A;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    /* Top Courtroom Header */
    .court-header {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 20px 24px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
    }
    .court-title-group h1 {
        color: #1B365D;
        font-size: 1.75rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0;
        display: inline-flex;
        align-items: center;
        gap: 10px;
    }
    .court-subtitle {
        color: #64748B;
        font-size: 0.95rem;
        margin-top: 4px;
        font-weight: 500;
    }
    .demo-badge {
        background-color: #EEF2F6;
        color: #1B365D;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        padding: 3px 8px;
        border-radius: 4px;
        border: 1px solid #CBD5E1;
        vertical-align: middle;
    }

    /* Status Indicators Bar */
    .status-bar {
        display: flex;
        gap: 16px;
        align-items: center;
        background-color: #F1F5F9;
        padding: 8px 14px;
        border-radius: 6px;
        border: 1px solid #E2E8F0;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .dot-ready {
        color: #10B981;
        font-size: 0.9rem;
    }
    .dot-lang {
        color: #3B82F6;
        font-size: 0.9rem;
    }
    .dot-connected {
        color: #059669;
        font-size: 0.9rem;
    }
    .dot-warning {
        color: #F59E0B;
        font-size: 0.9rem;
    }

    /* Disclaimer */
    .court-disclaimer {
        font-size: 0.8rem;
        color: #64748B;
        font-style: italic;
        margin-top: 6px;
        margin-bottom: 16px;
    }

    /* Card Panels */
    .court-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 18px 22px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
    }
    .court-card-title {
        color: #1B365D;
        font-size: 1.05rem;
        font-weight: 600;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #F1F5F9;
        padding-bottom: 8px;
    }

    /* Stats Pill */
    .stats-pill {
        background: #EEF2F6;
        color: #334155;
        font-size: 0.82rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 4px;
        border: 1px solid #E2E8F0;
    }

    /* Transcription Area Textarea */
    .stTextArea textarea {
        font-family: "Georgia", "Times New Roman", serif;
        font-size: 1.05rem !important;
        line-height: 1.6 !important;
        color: #0F172A !important;
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 6px !important;
        padding: 14px 16px !important;
    }
    .stTextArea textarea:focus {
        border-color: #1B365D !important;
        box-shadow: 0 0 0 2px rgba(27, 54, 93, 0.15) !important;
    }

    /* Button Primary Styling */
    .stButton button {
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.15s ease-in-out;
    }

    /* Demo Data Tag */
    .demo-tag {
        background-color: #FEF3C7;
        color: #92400E;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 3px;
        margin-left: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "raw_transcript" not in st.session_state:
    st.session_state.raw_transcript = ""
if "processed_audio_hashes" not in st.session_state:
    st.session_state.processed_audio_hashes = set()
if "session_start_time" not in st.session_state:
    st.session_state.session_start_time = datetime.now().strftime("%I:%M %p, %d %b %Y")
if "last_transcription_status" not in st.session_state:
    st.session_state.last_transcription_status = None
if "draft_notes" not in st.session_state:
    st.session_state.draft_notes = ""
if "show_clear_confirm" not in st.session_state:
    st.session_state.show_clear_confirm = False
if "demo_data_loaded" not in st.session_state:
    st.session_state.demo_data_loaded = False

# Sidebar Configuration
with st.sidebar:
    st.markdown(
        """
        <div style="padding-bottom: 12px; border-bottom: 1px solid #E2E8F0; margin-bottom: 16px;">
            <h2 style="color: #1B365D; font-size: 1.25rem; margin: 0; font-weight: 700;">
                ⚖️ CourtScribe AI
            </h2>
            <div style="color: #64748B; font-size: 0.8rem; margin-top: 2px;">
                Courtroom Transcription Console
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 🎙️ Transcription Settings")

    # Model Configuration
    env_default = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-transcribe")
    model_options = [
        "gpt-transcribe",
        "gpt-live-transcribe",
        "gpt-4o-transcribe",
        "gpt-4o-mini-transcribe",
    ]
    default_idx = model_options.index(env_default) if env_default in model_options else 0
    model_choice = st.selectbox(
        "Speech Model",
        options=model_options,
        index=default_idx,
        help="OpenAI speech-to-text model for courtroom transcription.",
    )

    # Language Selection
    language_choice = st.selectbox(
        "Spoken Language",
        options=["Auto Detect", "English", "Hindi", "Marathi"],
        index=0,
        help="Select language or Auto Detect for automatic detection and multilingual code-switching.",
    )
    lang_code_map = {
        "Auto Detect": None,
        "English": "en",
        "Hindi": "hi",
        "Marathi": "mr",
    }
    selected_lang_code = lang_code_map[language_choice]

    # Legal Vocabulary Assistance Toggle
    legal_vocab_enabled = st.toggle(
        "Legal Vocabulary Assistance",
        value=True,
        help="Injects legal terminology context into OpenAI API and normalizes statutory references (e.g. Section 144, CPC, CrPC).",
    )

    # Voice Commands Toggle
    voice_commands_enabled = st.toggle(
        "Voice Commands Processing",
        value=True,
        help="Interprets dictation commands such as 'full stop', 'comma', 'next paragraph', and 'new line'.",
    )

    st.markdown("---")

    # Session Metrics & Management
    st.markdown("### 📋 Session Information")
    st.caption(f"Session started: **{st.session_state.session_start_time}**")
    
    words_total = len(st.session_state.transcript.split()) if st.session_state.transcript else 0
    chars_total = len(st.session_state.transcript) if st.session_state.transcript else 0
    
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.metric("Total Words", words_total)
    with col_stat2:
        st.metric("Characters", chars_total)

    # Clear Transcript Button with Confirmation
    if not st.session_state.show_clear_confirm:
        if st.button("🗑️ Clear Transcript", use_container_width=True):
            st.session_state.show_clear_confirm = True
            st.rerun()
    else:
        st.warning("Are you sure you want to clear the transcript?")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Yes, Clear", type="primary", use_container_width=True):
                st.session_state.transcript = ""
                st.session_state.raw_transcript = ""
                st.session_state.draft_notes = ""
                st.session_state.last_transcription_status = None
                st.session_state.demo_data_loaded = False
                st.session_state.show_clear_confirm = False
                st.rerun()
        with col_no:
            if st.button("Cancel", use_container_width=True):
                st.session_state.show_clear_confirm = False
                st.rerun()

    st.markdown("---")

    # Export Section in Sidebar
    st.markdown("### 📥 Document Export")
    if st.session_state.transcript.strip():
        # Word (.docx)
        docx_bytes = export_to_docx(
            st.session_state.transcript,
            {
                "date": datetime.now().strftime("%d %B %Y, %I:%M %p"),
                "language": language_choice,
            },
        )
        st.download_button(
            label="📄 Export Word (.docx)",
            data=docx_bytes,
            file_name=f"Court_Transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

        # PDF (.pdf)
        pdf_bytes = export_to_pdf(
            st.session_state.transcript,
            {
                "date": datetime.now().strftime("%d %B %Y, %I:%M %p"),
                "language": language_choice,
            },
        )
        st.download_button(
            label="📑 Export PDF (.pdf)",
            data=pdf_bytes,
            file_name=f"Court_Transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.info("Record or load transcript to enable document export.")

    # Voice Commands Cheat Sheet
    with st.expander("🎙️ Spoken Commands Reference", expanded=False):
        st.markdown(
            """
            - **`"full stop"` / `"period"`** → `.`
            - **`"comma"`** → `,`
            - **`"colon"`** → `:`
            - **`"semicolon"`** → `;`
            - **`"question mark"`** → `?`
            - **`"exclamation mark"`** → `!`
            - **`"next paragraph"`** → Paragraph break
            - **`"new line"`** → New line
            - **`"open quote"` / `"close quote"`** → `"`
            """
        )

    with st.expander("⚖️ Legal Terms Reference", expanded=False):
        st.markdown(
            """
            *Applicant, Respondent, Petitioner, Counsel, Learned Counsel, Hon'ble Court, Section 144, Section 420, Section 302, CPC, CrPC, IPC, BNS, BNSS, BSA, Affidavit, Exhibit.*
            """
        )

# Main Screen Layout
# Header Block
openai_client = get_openai_client()
ai_status_dot = "dot-connected" if openai_client else "dot-warning"
ai_status_text = "AI Transcription: Connected" if openai_client else "AI Transcription: Key Missing"

st.markdown(
    f"""
    <div class="court-header">
        <div class="court-title-group">
            <h1>
                CourtScribe AI
                <span class="demo-badge">DEMO</span>
            </h1>
            <div class="court-subtitle">Real-time Courtroom Speech-to-Text & Judicial Transcription Workstation</div>
        </div>
        <div class="status-bar">
            <span class="status-pill"><span class="dot-ready">●</span> Microphone Ready</span>
            <span class="status-pill"><span class="dot-lang">●</span> Language: {language_choice}</span>
            <span class="status-pill"><span class="{ai_status_dot}">●</span> {ai_status_text}</span>
        </div>
    </div>
    <div class="court-disclaimer">
        ⚖️ Demo only — transcription should be reviewed by a human before being used as an official court record.
    </div>
    """,
    unsafe_allow_html=True,
)

# API Key Warning if not configured
if not openai_client:
    st.warning(
        """
        ⚠️ **OpenAI API Key Not Configured**
        
        To enable speech-to-text dictation, please set `OPENAI_API_KEY=your_key_here` in your `.env` file or environment.
        You can still test the editor, legal vocabulary normalization, voice commands, and document exports using the **Load Demo Transcript** button below.
        """,
        icon="⚠️",
    )

# Two-Column Workstation Layout
col_main, col_tools = st.columns([7, 3], gap="large")

with col_main:
    # 1. Courtroom Dictation Modes
    tab_live, tab_file = st.tabs([
        "⚡ Real-Time Streaming Dictation (Words Printed As You Talk)",
        "🎙️ Audio File Upload (OpenAI Model)"
    ])

    with tab_live:
        st.caption("Press **Start Live Dictation** below and begin speaking. Spoken words will print on screen in real-time as you talk, with live voice commands and legal terms.")
        live_html_path = os.path.join(_recorder_dir, "index.html")
        with open(live_html_path, "r", encoding="utf-8") as f:
            live_html = f.read()

        # Inject selected language from sidebar into live dictation engine
        lang_bcp47_map = {
            "English": "en-IN",
            "Hindi": "hi-IN",
            "Marathi": "mr-IN",
            "Auto Detect": "en-IN",
        }
        active_bcp47 = lang_bcp47_map.get(language_choice, "en-IN")
        live_html = live_html.replace("__DEFAULT_LANG__", active_bcp47)

        components.html(live_html, height=270, scrolling=False)
        st.markdown(
            "<div style='font-size: 0.82rem; color: #64748B; margin-top: -4px; margin-bottom: 8px;'>"
            "💡 <i>Tip: Click <b>📋 Copy to Record</b> on the card above to copy your real-time transcript directly into the editor below for Word & PDF export.</i>"
            "</div>",
            unsafe_allow_html=True
        )

    with tab_file:
        st.caption("Record continuous speech with your microphone and upload to OpenAI's speech-to-text model.")
        audio_record = st.audio_input(
            "🎙 Record Speech Audio File",
            key="courtroom_microphone",
            help="Captures audio from your browser microphone and sends it to OpenAI for courtroom transcription.",
        )

    # Handle Audio Input Processing
    if audio_record is not None:
        audio_bytes = audio_record.read()
        audio_hash = hashlib.md5(audio_bytes).hexdigest()

        # Only transcribe if this specific audio segment hasn't been transcribed yet
        if audio_hash not in st.session_state.processed_audio_hashes:
            st.session_state.processed_audio_hashes.add(audio_hash)

            status_placeholder = st.empty()
            with status_placeholder.container():
                st.markdown(
                    """
                    <div style="background-color: #FEF3C7; border: 1px solid #FCD34D; padding: 10px 14px; border-radius: 6px; color: #92400E; font-size: 0.9rem; font-weight: 500; margin-bottom: 10px;">
                        ⏳ <b>Transcribing audio...</b> Sending audio to OpenAI and applying legal normalization...
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            result = transcribe_audio_file(
                audio_bytes=audio_bytes,
                filename="court_recording.wav",
                language_code=selected_lang_code,
                apply_vocab=legal_vocab_enabled,
                apply_commands=voice_commands_enabled,
                preferred_model=model_choice,
            )

            status_placeholder.empty()

            if result["success"]:
                new_text = result["processed_text"]
                # Append to existing transcript with clean spacing
                if st.session_state.transcript.strip():
                    st.session_state.transcript = st.session_state.transcript.strip() + "\n\n" + new_text
                else:
                    st.session_state.transcript = new_text

                # Store raw transcript for inspection
                st.session_state.raw_transcript += ("\n" + result["raw_text"]).strip()
                st.session_state.demo_data_loaded = False
                
                # Feedback banner
                model_info = result["model_used"]
                success_msg = f"✓ Transcription updated using {model_info}."
                if result.get("routing_note"):
                    success_msg += f" ({result['routing_note']})"
                
                st.session_state.last_transcription_status = {
                    "type": "success",
                    "msg": success_msg,
                }
                st.rerun()
            else:
                st.session_state.last_transcription_status = {
                    "type": "error",
                    "msg": result["error"],
                }

    # Render Transcription Status Banner if any
    if st.session_state.last_transcription_status:
        status_info = st.session_state.last_transcription_status
        if status_info["type"] == "success":
            st.success(status_info["msg"], icon="✅")
        else:
            st.error(status_info["msg"], icon="⚠️")

    # 2. Courtroom Transcript Editor Section
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    
    word_count = len(st.session_state.transcript.split()) if st.session_state.transcript else 0
    char_count = len(st.session_state.transcript) if st.session_state.transcript else 0

    col_t_title, col_t_stats = st.columns([6, 4])
    with col_t_title:
        demo_tag = " <span class='demo-tag'>DEMO DATA</span>" if st.session_state.demo_data_loaded else ""
        st.markdown(
            f"<h3 style='color: #1B365D; margin: 0; font-size: 1.25rem; font-weight: 700;'>"
            f"📝 Official Transcript Record{demo_tag}</h3>",
            unsafe_allow_html=True,
        )
    with col_t_stats:
        st.markdown(
            f"<div style='text-align: right; padding-top: 4px; font-size: 0.9rem; font-weight: 600; color: #475569;'>"
            f"Words: <b style='color:#1B365D;'>{word_count}</b> &nbsp;|&nbsp; "
            f"Characters: <b style='color:#1B365D;'>{char_count:,}</b>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Large Editable Transcript Text Area with visible label and helpful placeholder
    updated_transcript = st.text_area(
        label="Court Proceedings (Live Editable Record)",
        value=st.session_state.transcript,
        height=340,
        placeholder="Speech-to-text transcription will appear here as you speak into the microphone...\n\nYou can also click '📋 Load Demo Transcript' below to instantly test the editor and document exports.",
        help="Review and edit the transcription directly. Any manual edits will be included in Word and PDF exports.",
    )
    if updated_transcript != st.session_state.transcript:
        st.session_state.transcript = updated_transcript

    # Action buttons under editor
    col_act1, col_act2, col_act3 = st.columns([3, 4, 3])
    with col_act1:
        if st.button("📋 Load Demo Transcript", help=f"Loads a realistic {language_choice} courtroom proceedings sample"):
            if language_choice == "Hindi":
                demo_text = (
                    "आवेदक उपस्थित हैं और विद्वान अधिवक्ता द्वारा उनका प्रतिनिधित्व किया जा रहा है। प्रतिवादी भी उपस्थित हैं। "
                    "यह मामला सीपीसी की धारा 144 के तहत दायर आवेदन से संबंधित है।\n\n"
                    "माननीय न्यायालय ने दोनों पक्षों की दलीलें सुनीं। आवेदक के विद्वान अधिवक्ता का निवेदन है कि "
                    "आसन्न खतरे को देखते हुए तत्काल अंतरिम राहत दी जानी चाहिए।\n\n"
                    "प्रतिवादी लिखित बयान दाखिल करने के लिए दो सप्ताह का समय मांगते हैं। "
                    "मामले को आगे की बहस के लिए अगली सुनवाई की तारीख तक स्थगित किया जाता है।"
                )
            elif language_choice == "Marathi":
                demo_text = (
                    "अर्जदार उपस्थित असून विद्वान वकीलांमार्फत त्यांचे प्रतिनिधित्व केले जात आहे. प्रतिवादी देखील उपस्थित आहेत. "
                    "सदर प्रकरण सीपीसी च्या कलम 144 अंतर्गत दाखल केलेल्या अर्जाशी संबंधित आहे.\n\n"
                    "नामदार न्यायालयाने दोन्ही बाजूंचे म्हणणे ऐकून घेतले. अर्जदाराच्या विद्वान वकिलांनी असा युक्तिवाद केला की "
                    "तातडीचा अंतरिम दिलासा देणे न्याय्य ठरेल.\n\n"
                    "प्रतिवादींनी लेखी जबाब दाखल करण्यासाठी दोन आठवड्यांची मुदत मागितली आहे. "
                    "पुढील युक्तिवादासाठी सुनावणी पुढील तारखेपर्यंत तहकूब करण्यात येत आहे."
                )
            else:
                demo_text = (
                    "The applicant is present and represented by learned counsel. The respondent is also present. "
                    "The matter concerns the application filed under Section 144 of the CPC.\n\n"
                    "The Court has heard the submissions of both parties. The learned counsel for the applicant "
                    "submits that urgent interim relief is warranted in view of the imminent threat.\n\n"
                    "The respondent seeks two weeks time to file the written statement. "
                    "The matter is adjourned to the next date of hearing for further arguments."
                )
            st.session_state.transcript = demo_text
            st.session_state.demo_data_loaded = True
            st.session_state.last_transcription_status = {
                "type": "success",
                "msg": f"Realistic {language_choice} demo transcript loaded into editor.",
            }
            st.rerun()

    with col_act2:
        if st.session_state.transcript.strip():
            # Quick normalize button to re-apply legal formatting after manual edits
            if st.button("✨ Apply Legal Normalization", help="Re-runs legal terminology and citation formatters on the current text"):
                st.session_state.transcript = normalize_legal_terms(
                    st.session_state.transcript,
                    language_code=selected_lang_code
                )
                st.rerun()

    with col_act3:
        if st.button("📝 Create Draft Notes", help="Structures the transcript into judicial proceedings draft notes"):
            with st.spinner("Structuring proceedings draft..."):
                draft = generate_draft_proceedings(st.session_state.transcript)
                st.session_state.draft_notes = draft
                st.rerun()

with col_tools:
    # Right Column: Document Exports & Draft Notes
    st.markdown(
        """
        <div class="court-card">
            <div class="court-card-title">
                <span>📑 Document Actions</span>
            </div>
            <p style="font-size: 0.85rem; color: #64748B; margin-top: -6px;">
                Download formatted court documents directly.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.transcript.strip():
        # Word Export
        docx_io = export_to_docx(
            st.session_state.transcript,
            {
                "date": datetime.now().strftime("%d %B %Y, %I:%M %p"),
                "language": language_choice,
            },
        )
        st.download_button(
            label="📄 Download Word (.docx)",
            data=docx_io,
            file_name=f"Court_Proceedings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary",
            use_container_width=True,
        )

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        # PDF Export
        pdf_io = export_to_pdf(
            st.session_state.transcript,
            {
                "date": datetime.now().strftime("%d %B %Y, %I:%M %p"),
                "language": language_choice,
            },
        )
        st.download_button(
            label="📑 Download PDF (.pdf)",
            data=pdf_io,
            file_name=f"Court_Proceedings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.info("Record audio or click 'Load Demo Transcript' to enable Word & PDF downloads.")

    # Draft Proceedings Box
    if st.session_state.draft_notes:
        st.markdown("---")
        st.markdown(
            """
            <div style="font-weight: 600; color: #1B365D; font-size: 0.95rem; margin-bottom: 6px;">
                ⚖️ Structured Proceedings Draft
            </div>
            <div style="font-size: 0.75rem; color: #64748B; font-style: italic; margin-bottom: 10px;">
                AI-generated draft — requires review by the presiding authority/legal professional.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.text_area(
            "Draft Content",
            value=st.session_state.draft_notes,
            height=280,
            label_visibility="collapsed",
        )

        # Download Draft as Docx
        draft_docx = export_to_docx(
            st.session_state.draft_notes,
            {
                "title": "COURT PROCEEDINGS — STRUCTURED DRAFT",
                "subtitle": "Judicial Proceedings & Judgment Notes",
                "date": datetime.now().strftime("%d %B %Y, %I:%M %p"),
                "language": language_choice,
            },
        )
        st.download_button(
            label="📥 Download Draft (.docx)",
            data=draft_docx,
            file_name=f"Draft_Proceedings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

    # Raw Debug Inspector (Collapsible)
    if st.session_state.raw_transcript:
        with st.expander("🔍 Raw Transcription Audio Log", expanded=False):
            st.caption("Verbatim raw response received from OpenAI prior to commands and normalization:")
            st.text(st.session_state.raw_transcript)
