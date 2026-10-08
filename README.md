# CourtScribe AI — English Judicial Stenographer Workstation

A professional courtroom transcription workstation built with **Flask** and the **OpenAI Speech API**, engineered specifically for high-accuracy judicial English stenography, legal normalization, and courtroom document preparation.

---

## Key Capabilities Demonstrated

1. **Live Continuous Dictation (Web Speech API)**: Native real-time streaming dictation directly in the browser (Chrome, Edge, Safari) with audio visualization.
2. **Audio File Transcription (Whisper API)**: Upload courtroom recordings (`.mp3`, `.wav`, `.m4a`, `.webm`, `.ogg`) for high-fidelity legal transcription.
3. **Spoken Steno Shorthand Translation**: Automatically converts spoken cues (*"comma"* -> `,`, *"full stop"* -> `.`, *"colon"* -> `:`, *"open bracket"* -> `(`, *"next paragraph"*, etc.) into proper punctuation.
4. **Legal Vocabulary & Witness Normalization**: Formats judicial terms and exhibits matching High Court standards (*PW-1*, *Ex.P1*, *MO-1*, *Section 302 IPC*, *RI 5 years*, *S/o.*).
5. **Pre-Loaded High Court Presets**: Load actual benchmark judgments (`english_data_1.txt`, `english_data_2.txt`, and Bail Dictation) with a single click.
6. **AI Judge's Order Draft**: Structures transcripts into an 8-part official judicial order outline.
7. **One-Click Courtroom Document Export**: Export live transcripts to Microsoft Word (`.docx`) and court-formatted PDF (`.pdf`).

---

## Project Structure

```text
court-stt-demo/
├── app.py                     # Flask web server & REST endpoints (Port 8501)
├── Dockerfile                 # Production Coolify Docker configuration
├── requirements.txt           # Python dependencies (Flask, Gunicorn, etc.)
├── static/
│   ├── css/style.css          # Judicial navy & gold design system
│   └── js/app.js              # Client audio streaming, steno engine & controller
├── templates/
│   └── index.html             # Main English Judicial Stenographer workstation UI
├── training/
│   ├── english_data_1.txt     # Murder Appeal High Court Judgment benchmark
│   ├── english_data_2.txt     # Sentence Modification Order benchmark
│   └── steno_english.json     # Spoken command to symbol mappings
└── utils/
    ├── transcription.py       # OpenAI Whisper audio transcription pipeline
    ├── legal_vocabulary.py    # English legal lexicon & normalization rules
    └── exporters.py           # Word (.docx) and PDF document generation
```

---

## Installation & Setup

### 1. Prerequisites
- Python 3.9+ (tested on Python 3.9 through 3.12)
- OpenAI API Key

### 2. Create Virtual Environment

On macOS / Linux:
```bash
cd court-stt-demo
python3 -m venv .venv
source .venv/bin/activate
```

On Windows (Command Prompt):
```cmd
cd court-stt-demo
python -m venv .venv
.venv\Scripts\activate.bat
```

On Windows (PowerShell):
```powershell
cd court-stt-demo
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Open `.env` and set your OpenAI API key:
```env
OPENAI_API_KEY=sk-...your_actual_key_here...
OPENAI_TRANSCRIPTION_MODEL=gpt-live-transcribe
OPENAI_FINAL_TRANSCRIPTION_MODEL=gpt-transcribe
```

> **Security Note**: Never expose or commit your `OPENAI_API_KEY`. Secrets are read exclusively server-side and never sent to client-side scripts.

---

## Running the Application

Launch the Streamlit demo with:

```bash
streamlit run app.py
```

The application will launch in your default web browser at `http://localhost:8501`.

---

## Microphone & Browser Permissions

1. When you first press the microphone button, your browser will prompt:
   **"Allow localhost:8501 to use your microphone?"**
2. Click **Allow**.
3. If permission was previously blocked:
   - **Chrome / Brave**: Click the padlock / settings icon in the address bar → Site Settings → Microphone → set to **Allow**.
   - **Safari**: Safari Preferences → Websites → Microphone → set to **Allow**.
   - **Firefox**: Click the microphone icon next to the URL bar and unblock.

---

## Transcription Architecture

```text
Spoken Audio (Browser Microphone)
                ↓
    Streamlit Native Audio Capture (st.audio_input)
                ↓
      Audio Bytes Buffer (16 kHz WAV)
                ↓
 OpenAI Audio Transcription API (`client.audio.transcriptions.create`)
    ├── Model: gpt-live-transcribe (or gpt-transcribe)
    ├── Prompt Context: Legal terminology prime context
    └── Language: Auto Detect / en / hi / mr
                ↓
         Raw Transcription
                ↓
     Voice Commands Processing Layer
    (e.g., "full stop" → ., "next paragraph" → \n\n)
                ↓
   Legal Vocabulary Normalization Layer
    (e.g., "Section one forty four" → Section 144, "c p c" → CPC)
                ↓
   Interactive Courtroom Transcript Editor
                ↓
  ┌───────────────────────┬───────────────────────┐
  │   Export Word (.docx) │   Export PDF (.pdf)   │
  └───────────────────────┴───────────────────────┘
```

### Speech Models

- **`gpt-live-transcribe`**: Primary real-time courtroom dictation and transcription model.
- **`gpt-transcribe`**: High-accuracy speech transcription model for finalized records.
- Configurable directly via `OPENAI_TRANSCRIPTION_MODEL` and the sidebar model selector.

---

## Voice Commands Reference

| Spoken Phrase | Output | Behavior / Notes |
| :--- | :--- | :--- |
| `"full stop"` / `"period"` | `.` | Inserts period, trims space before punctuation, capitalizes next sentence. |
| `"comma"` | `,` | Inserts comma and attaches to previous token. |
| `"colon"` | `:` | Inserts colon. |
| `"semicolon"` | `;` | Inserts semicolon. |
| `"question mark"` | `?` | Inserts question mark and capitalizes next sentence. |
| `"exclamation mark"` | `!` | Inserts exclamation point. |
| `"next paragraph"` / `"new paragraph"` | `\n\n` | Creates double line paragraph break. |
| `"new line"` | `\n` | Inserts single line break. |
| `"open quote"` / `"close quote"` | `"` | Inserts quotation marks. |

---

## Legal Vocabulary Normalization

The system injects a comprehensive Indian & Common-Law lexicon into the model's prompt context and provides post-processing normalization:

- **Sections & Statutes**:
  - Spoken `"Section one forty four"` → `Section 144`
  - Spoken `"Section four twenty"` → `Section 420`
  - Spoken `"Section three zero two"` → `Section 302`
  - Spoken `"Section one thirty eight"` → `Section 138`
  - Spoken `"Section four eighty two"` → `Section 482`
  - Spoken `"Article two twenty six"` → `Article 226`
- **Procedural Codes**:
  - Spoken `"C P C"` / `"c.p.c."` → `CPC`
  - Spoken `"Cr P C"` / `"cr.p.c."` → `CrPC`
  - Spoken `"I P C"` / `"i.p.c."` → `IPC`
  - Spoken `"B N S"` → `BNS` (Bharatiya Nyaya Sanhita)
  - Spoken `"B N S S"` → `BNSS` (Bharatiya Nagarik Suraksha Sanhita)
  - Spoken `"B S A"` → `BSA` (Bharatiya Sakshya Adhiniyam)
- **Honorifics & Parties**:
  - Standardizes capitalization for `Learned Counsel`, `Hon'ble Court`, `Applicant`, `Respondent`, `Petitioner`.

---

## Manual Testing Checklist

| Step | Action | Expected Result |
| :--- | :--- | :--- |
| **1. UI Load** | Launch `streamlit run app.py` | Professional courtroom workstation appears with status indicators: Microphone Ready, Language: Auto, AI Transcription status. |
| **2. Demo Data** | Click **Load Demo Transcript** | Realistic legal transcript appears in editor with Word count and Character count metrics. |
| **3. Word Export** | Click **Download Word (.docx)** | Clean `.docx` downloads with courtroom headers, date, metadata table, and paragraphs. |
| **4. PDF Export** | Click **Download PDF (.pdf)** | Professional A4 PDF opens with clean margins, running header, and "Page 1 of 1" footer. |
| **5. Live Dictation** | Press mic, say: *"The applicant is present full stop next paragraph The respondent is absent full stop"* | Audio records, uploads, transcribes, voice commands convert to `.` and paragraph breaks. |
| **6. Legal Terms** | Say: *"The application is filed under Section one forty four of the c p c comma before the learned counsel full stop"* | Transcribes accurately into `Section 144 of the CPC, before the Learned Counsel.` |
| **7. Multilingual** | Say in Hindi/Marathi: *"Applicant ने आज application submit केली आहे."* | Preserves multilingual code-switching without forced translation. |
| **8. Clear Action** | Click **Clear Transcript** | Prompts confirmation modal; clicking "Yes, Clear" resets session safely. |

---

## Known Limitations

- **Browser Audio Permissions**: Web browsers require explicit user permission to access the microphone.
- **Audio Capture Latency**: Push-to-talk capture waits until the user finishes the recording segment before sending to OpenAI REST API.
- **Human Verification Notice**: This demo is intended for demonstration purposes. Any transcript must be reviewed and certified by a competent judicial clerk or presiding officer before becoming an official court record.
