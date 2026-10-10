/**
 * CourtScribe AI — English Judicial Stenographer Client Controller
 * 
 * Features:
 * - Dual Engine Live Dictation:
 *   1. OpenAI Whisper API Live Streaming (Server-side AI transcription model)
 *   2. Native Browser Web Speech API (Offline fallback)
 * - Real-time spoken steno shorthand conversion ("in to the bracket" -> "(", "bracket closed" -> ")", "commas" -> ",")
 * - Audio file & recording transcription via Whisper API
 * - 8-part Judge's Order and Court Proceedings draft generation
 * - Courtroom Word (.docx) and PDF document exports
 * - Theme toggle (Light Mode default / Dark Mode)
 */

document.addEventListener("DOMContentLoaded", () => {
  // ==========================================
  // DOM Elements
  // ==========================================
  const languageSelect = document.getElementById("languageSelect");
  const engineSelect = document.getElementById("engineSelect");
  const liveEngineStatus = document.getElementById("liveEngineStatus");
  const engineStatusText = document.getElementById("engineStatusText");
  const micStateBadge = document.getElementById("micStateBadge");
  const liveDictationCard = document.getElementById("liveDictationCard");

  const liveStreamBox = document.getElementById("liveStreamBox");
  const liveStreamPlaceholder = document.getElementById("liveStreamPlaceholder");
  const finalTranscriptBuffer = document.getElementById("finalTranscriptBuffer");
  const interimTranscriptBuffer = document.getElementById("interimTranscriptBuffer");
  const openaiLiveIndicator = document.getElementById("openaiLiveIndicator");
  const audioVisualizer = document.getElementById("audioVisualizer");

  const btnStartLive = document.getElementById("btnStartLive");
  const btnStopLive = document.getElementById("btnStopLive");
  const btnAppendLive = document.getElementById("btnAppendLive");
  const btnCopyLive = document.getElementById("btnCopyLive");
  const btnClearLive = document.getElementById("btnClearLive");
  const liveWordCount = document.getElementById("liveWordCount");

  const transcriptTextarea = document.getElementById("transcriptTextarea");
  const statWords = document.getElementById("statWords");
  const statChars = document.getElementById("statChars");
  const statParagraphs = document.getElementById("statParagraphs");

  const btnCopyEditor = document.getElementById("btnCopyEditor");
  const btnClearEditor = document.getElementById("btnClearEditor");
  const btnNormalize = document.getElementById("btnNormalize");
  const btnGenerateDraft = document.getElementById("btnGenerateDraft");
  const btnExportDocx = document.getElementById("btnExportDocx");
  const btnExportPdf = document.getElementById("btnExportPdf");

  const uploadDropzone = document.getElementById("uploadDropzone");
  const audioFileInput = document.getElementById("audioFileInput");
  const selectedFileInfo = document.getElementById("selectedFileInfo");
  const selectedFileName = document.getElementById("selectedFileName");
  const selectedFileSize = document.getElementById("selectedFileSize");
  const btnRemoveFile = document.getElementById("btnRemoveFile");
  const btnTranscribeFile = document.getElementById("btnTranscribeFile");

  const draftPanel = document.getElementById("draftPanel");
  const btnCopyDraft = document.getElementById("btnCopyDraft");
  const btnInsertDraft = document.getElementById("btnInsertDraft");

  const btnThemeToggle = document.getElementById("btnThemeToggle");
  const themeToggleIcon = document.getElementById("themeToggleIcon");
  const themeToggleText = document.getElementById("themeToggleText");

  const toastContainer = document.getElementById("toastContainer");

  // ==========================================
  // Application State
  // ==========================================
  let isListening = false;
  let finalSpeechText = "";
  let selectedAudioFile = null;

  // Web Audio & Dual-WebSocket state
  let micStream = null;
  let audioContext = null;
  let audioProcessor = null;
  let analyser = null;
  let visualizerAnimFrame = null;
  let socket = null;

  // Web Speech recognition instance
  let webSpeechRecognition = null;

  // Clear any legacy custom key from local storage so backend .env is always authoritative
  try { localStorage.removeItem("courtscribe_openai_key"); } catch (e) {}

  // ==========================================
  // Live Viewport Scroll & Stats Helpers
  // ==========================================
  function scrollLiveStreamToBottom() {
    if (liveStreamBox) {
      liveStreamBox.scrollTop = liveStreamBox.scrollHeight;
    }
  }

  function updateLiveStats() {
    if (liveWordCount) {
      const fullText = (finalSpeechText + " " + (interimTranscriptBuffer ? interimTranscriptBuffer.textContent : "")).trim();
      const count = fullText ? fullText.split(/\s+/).filter(Boolean).length : 0;
      liveWordCount.textContent = `${count} word${count === 1 ? "" : "s"}`;
    }
  }

  // ==========================================
  // Socket.IO Dual-WebSocket Controller
  // ==========================================
  if (typeof io !== "undefined") {
    socket = io({
      transports: ["websocket", "polling"],
      autoConnect: true,
    });

    socket.on("connect", () => {
      console.log("[SocketIO] Connected to CourtScribe backend server.");
    });

    socket.on("realtime_status", (data) => {
      console.log("[RealtimeStatus]", data);
      if (data.status === "speaking") {
        if (openaiLiveIndicator) {
          openaiLiveIndicator.style.display = "inline-flex";
          openaiLiveIndicator.textContent = "🎙️ Speaking...";
        }
      } else if (data.status === "transcribing") {
        if (openaiLiveIndicator) {
          openaiLiveIndicator.textContent = "⚡ Streaming...";
        }
      } else if (data.status === "ready") {
        if (openaiLiveIndicator) {
          openaiLiveIndicator.style.display = "none";
        }
      }
    });

    socket.on("transcript_update", (data) => {
      // Live interim token stream with instant spoken steno replacements
      if (data && data.buffer) {
        interimTranscriptBuffer.textContent = data.buffer;
        scrollLiveStreamToBottom();
        updateLiveStats();
      }
    });

    socket.on("transcript_final", (data) => {
      // Completed utterance with steno rules & legal normalization applied
      if (data && data.text) {
        const text = data.text;
        finalSpeechText = appendToTranscript(finalSpeechText, text);
        finalTranscriptBuffer.textContent = finalSpeechText;
        interimTranscriptBuffer.textContent = "";
        scrollLiveStreamToBottom();
        updateLiveStats();

        // Synchronize directly into main judicial editor
        transcriptTextarea.value = appendToTranscript(transcriptTextarea.value, text);
        updateEditorStats();
      }
    });

    socket.on("realtime_error", (data) => {
      console.error("[RealtimeError]", data);
      showToast(data.error || "OpenAI Realtime error", "error", 5000);
      if (openaiLiveIndicator) openaiLiveIndicator.style.display = "none";
    });
  }

  // Audio resampling & 16-bit linear PCM conversion helper (target 24kHz)
  function floatTo16BitPCM(input, inputSampleRate, targetSampleRate = 24000) {
    let samples = input;
    if (inputSampleRate !== targetSampleRate) {
      const ratio = inputSampleRate / targetSampleRate;
      const newLength = Math.round(input.length / ratio);
      const resampled = new Float32Array(newLength);
      let offsetResult = 0;
      let offsetSource = 0;
      while (offsetResult < resampled.length) {
        const nextOffsetSource = Math.round((offsetResult + 1) * ratio);
        let accum = 0, count = 0;
        for (let i = offsetSource; i < nextOffsetSource && i < input.length; i++) {
          accum += input[i];
          count++;
        }
        resampled[offsetResult] = count > 0 ? accum / count : 0;
        offsetResult++;
        offsetSource = nextOffsetSource;
      }
      samples = resampled;
    }

    const output = new Int16Array(samples.length);
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return output;
  }

  // ==========================================
  // Theme Controller (Light Mode Default)
  // ==========================================
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("courtscribe_theme", theme);
    if (themeToggleIcon && themeToggleText) {
      if (theme === "light") {
        themeToggleIcon.textContent = "☀️";
        themeToggleText.textContent = "Light Mode";
      } else {
        themeToggleIcon.textContent = "🌙";
        themeToggleText.textContent = "Dark Mode";
      }
    }
  }

  const savedTheme = localStorage.getItem("courtscribe_theme") || "light";
  applyTheme(savedTheme);

  if (btnThemeToggle) {
    btnThemeToggle.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "light";
      const nextTheme = current === "light" ? "dark" : "light";
      applyTheme(nextTheme);
      showToast(`Switched to ${nextTheme === "light" ? "Light" : "Dark"} Mode`, "info", 1800);
    });
  }

  // ==========================================
  // Toast Notification System
  // ==========================================
  function showToast(message, type = "info", durationMs = 4000) {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    const icon = type === "success" ? "✅" : type === "error" ? "❌" : "ℹ️";
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;

    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(50px)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, durationMs);
  }

  // ==========================================
  // Transcript Appender Helper
  // Handles new paragraphs, lines, spaces, and punctuation correctly
  // ==========================================
  function appendToTranscript(existing, incoming) {
    if (incoming === undefined || incoming === null || incoming === "") return existing;
    if (!existing) {
      return incoming.replace(/^[ \t]+/, "");
    }

    // Pure paragraph break command
    if (incoming === "\n\n") {
      if (existing.endsWith("\n\n")) return existing;
      if (existing.endsWith("\n")) return existing + "\n";
      return existing + "\n\n";
    }

    // Pure line break command
    if (incoming === "\n") {
      if (existing.endsWith("\n")) return existing;
      return existing + "\n";
    }

    // Pure space command
    if (incoming === " ") {
      if (existing.endsWith(" ") || existing.endsWith("\n")) return existing;
      return existing + " ";
    }

    // If incoming starts with paragraph breaks
    if (incoming.startsWith("\n\n")) {
      const remainder = incoming.replace(/^\n+/, "");
      if (existing.endsWith("\n\n")) {
        return existing + remainder;
      } else if (existing.endsWith("\n")) {
        return existing + "\n" + remainder;
      } else {
        return existing + "\n\n" + remainder;
      }
    }

    // If incoming starts with a single line break
    if (incoming.startsWith("\n")) {
      const remainder = incoming.replace(/^\n+/, "");
      if (existing.endsWith("\n")) {
        return existing + remainder;
      } else {
        return existing + "\n" + remainder;
      }
    }

    // If existing text already ends with a newline, line break, or space
    if (existing.endsWith("\n") || existing.endsWith(" ")) {
      return existing + incoming;
    }

    // If incoming text starts with punctuation like comma, period, colon, semicolon, etc.
    if (/^[.,;:?!%)\]}]/.test(incoming)) {
      return existing + incoming;
    }

    // Standard word continuation: single space separator
    return existing + " " + incoming;
  }

  // ==========================================
  // Live Steno Shorthand Translator (Client-side)
  // Converts spoken commands to punctuation & symbols
  // ==========================================
  function applyLiveStenoShothand(text) {
    if (!text) return "";

    let cleaned = text;

    const stenoRules = [
      // 1. Spoken Brackets & Parentheses: "("
      { regex: /\b(in\s*to\s+the\s+brackets?|into\s+the\s+brackets?|in\s+to\s+brackets?|into\s+brackets?|in\s+the\s+brackets?|in\s+brackets?|inside\s+(?:the\s+)?brackets?|open\s+(?:the\s+)?brackets?|start\s+(?:the\s+)?brackets?|put\s+(?:in|into|in\s+to)\s+(?:the\s+)?brackets?|brackets?\s+open|open\s+parenthes(?:is|es)|parenthes(?:is|es)\s+open|left\s+bracket|left\s+paren|start\s+parenthesis|round\s+bracket\s+open)\b/gi, replacement: "(" },
      
      // 2. Spoken Closing Brackets: ")"
      { regex: /\b(brackets?\s+closed|brackets?\s+close|close\s+(?:the\s+)?brackets?|close\s+brackets?|brackets?\s+complete(?:d)?|brackets?\s+end|end\s+(?:the\s+)?brackets?|close\s+off\s+bracket|out\s+of\s+(?:the\s+)?brackets?|close\s+parenthes(?:is|es)|parenthes(?:is|es)\s+closed|right\s+bracket|right\s+paren|end\s+parenthesis|round\s+bracket\s+closed)\b/gi, replacement: ")" },

      // 3. Square Brackets: "[" and "]"
      { regex: /\b(in\s*to\s+(?:the\s+)?square\s+brackets?|into\s+(?:the\s+)?square\s+brackets?|open\s+(?:the\s+)?square\s+brackets?|square\s+brackets?\s+open|open\s+box\s+bracket)\b/gi, replacement: "[" },
      { regex: /\b(square\s+brackets?\s+closed|square\s+brackets?\s+close|close\s+(?:the\s+)?square\s+brackets?|out\s+of\s+(?:the\s+)?square\s+brackets?|box\s+bracket\s+closed)\b/gi, replacement: "]" },

      // 4. Curly Braces: "{" and "}"
      { regex: /\b(in\s*to\s+(?:the\s+)?curly\s+brace(?:s)?|into\s+(?:the\s+)?curly\s+brace(?:s)?|open\s+(?:the\s+)?curly\s+brace(?:s)?|curly\s+brace(?:s)?\s+open|curly\s+bracket\s+open)\b/gi, replacement: "{" },
      { regex: /\b(curly\s+brace(?:s)?\s+closed|curly\s+bracket\s+closed|curly\s+brace(?:s)?\s+close|close\s+(?:the\s+)?curly\s+brace(?:s)?|out\s+of\s+(?:the\s+)?curly\s+brace(?:s)?)\b/gi, replacement: "}" },

      // 5. Commas: "," (singular, plural, misspellings, vernacular)
      { regex: /\b(commas?|comas?|komas?|alpa\s+viram|alpaviram|swalpa\s+viram|swalpaviram)\b/gi, replacement: "," },

      // 6. Full stop / period: "."
      { regex: /\b(full\s*stops?|fullstops?|periods?|purna\s+viram)\b/gi, replacement: "." },

      // 7. Quotes & Inverted Commas: '"'
      { regex: /\b(in\s*to\s+(?:the\s+)?quotes?|into\s+(?:the\s+)?quotes?|in\s+quotes?|open\s+(?:double\s+)?quotes?|quote\s*open|quotes\s*open|start\s+quotes?|open\s+inverted\s+commas?|inverted\s+commas?\s+open)\b/gi, replacement: '"' },
      { regex: /\b(quotes?\s+closed|quote\s*closed|quotes?\s+close|quote\s*close|close\s+(?:the\s+)?quotes?|close\s+(?:double\s+)?quotes?|end\s+quotes?|out\s+of\s+(?:the\s+)?quotes?|close\s+inverted\s+commas?|inverted\s+commas?\s+closed)\b/gi, replacement: '"' },
      { regex: /\b(open\s+single\s+quote|single\s+quote\s+open)\b/gi, replacement: "'" },
      { regex: /\b(close\s+single\s+quote|single\s+quote\s+closed|single\s+quote\s+close)\b/gi, replacement: "'" },

      // 8. Colon & Semicolon
      { regex: /\b(semi\s*colons?)\b/gi, replacement: ";" },
      { regex: /\b(colons?)\b/gi, replacement: ":" },

      // 9. Question mark & Exclamation
      { regex: /\b(question\s*marks?|mark\s+of\s+interrogation)\b/gi, replacement: "?" },
      { regex: /\b(exclamation\s*marks?|exclamation\s*points?)\b/gi, replacement: "!" },

      // 10. Hyphen, Dash, Slashes
      { regex: /\b(hyphens?|dashes?)\b/gi, replacement: "-" },
      { regex: /\b(forward\s*slash|slash|oblique)\b/gi, replacement: "/" },
      { regex: /\b(back\s*slash)\b/gi, replacement: "\\" },

      // 11. Currency & Math
      { regex: /\b(rupees?|rupee\s*sign)\b/gi, replacement: "₹" },
      { regex: /\b(percent\s*sign|percentage)\b/gi, replacement: "%" },
      { regex: /\b(and\s*sign|ampersand)\b/gi, replacement: "&" },
      { regex: /\b(plus\s*sign)\b/gi, replacement: "+" },
      { regex: /\b(equals?\s*(?:to|sign)?)\b/gi, replacement: "=" },

      // 12. Formatting breaks: Next paragraph, new paragraph, next line, new line, space, tab
      { regex: /\b(start\s+(?:a\s+)?new\s+paragraph|start\s+(?:a\s+)?next\s+paragraph|a\s+next\s+paragraph|a\s+new\s+paragraph|next\s+paragraph|new\s+paragraph|paragraph\s+break)\b/gi, replacement: "\n\n" },
      { regex: /\b(start\s+(?:a\s+)?new\s+line|start\s+(?:a\s+)?next\s+line|a\s+next\s+line|a\s+new\s+line|next\s+line|new\s+line|line\s+break|press\s+enter|hit\s+enter)\b/gi, replacement: "\n" },
      { regex: /\b(blank\s+space|white\s+space|single\s+space|space\s+bar|give\s+(?:a\s+)?space|add\s+(?:a\s+)?space|insert\s+(?:a\s+)?space|a\s+space)\b/gi, replacement: " " },
      { regex: /(?<=[.,;:?!])\s*\bspace\b/gi, replacement: " " },
      { regex: /\b(tab\s+space|tab\s+key|indent)\b/gi, replacement: "    " },

      // 13. Kinship, Parentage, Marital Status & Residency Shorthand
      { regex: /\b(son\s+of|s\s*[/.]\s*o\.?)\b/gi, replacement: "S/o." },
      { regex: /\b(daughter\s+of|d\s*[/.]\s*o\.?)\b/gi, replacement: "D/o." },
      { regex: /\b(wife\s+of|w\s*[/.]\s*o\.?)\b/gi, replacement: "W/o." },
      { regex: /\b(husband\s+of|h\s*[/.]\s*o\.?)\b/gi, replacement: "H/o." },
      { regex: /\b(widow\s+of|wd\s*[/.]\s*o\.?|w\s*\/\s*d\s*\/\s*o\.?)\b/gi, replacement: "Wd/o." },
      { regex: /\b(care\s+of|c\s*[/.]\s*o\.?)\b/gi, replacement: "C/o." },
      { regex: /\b(resident\s+of|residing\s+at|residing\s+in|resident\s+at|r\s*[/.]\s*o\.?)\b/gi, replacement: "R/o." },
      { regex: /\b(father\s+of|f\s*[/.]\s*o\.?)\b/gi, replacement: "F/o." },
      { regex: /\b(mother\s+of|m\s*[/.]\s*o\.?)\b/gi, replacement: "M/o." },
      { regex: /\b(also\s+known\s+as|a\.?\s*k\.?\s*a\.?)\b/gi, replacement: "alias" },

      // 14. Common Courtroom Witness, Party, Case & Exhibit Shorthand
      { regex: /\b(p\s*w|prosecution\s*witness)\s*([0-9]+)\b/gi, replacement: "PW-$2" },
      { regex: /\b(d\s*w|defence\s*witness|defense\s*witness)\s*([0-9]+)\b/gi, replacement: "DW-$2" },
      { regex: /\b(c\s*w|court\s*witness)\s*([0-9]+)\b/gi, replacement: "CW-$2" },
      { regex: /\b(exhibit\s*p|ex\s*p)\s*([0-9]+)\b/gi, replacement: "Ex.P$2" },
      { regex: /\b(exhibit\s*d|ex\s*d)\s*([0-9]+)\b/gi, replacement: "Ex.D$2" },
      { regex: /\b(material\s*object|m\s*o)\s*([0-9]+)\b/gi, replacement: "MO-$2" },
      { regex: /\b(material\s*objects|m\s*o\s*s)\s*([0-9]+)\s*(?:to|-)\s*([0-9]+)\b/gi, replacement: "MOs $2 to $3" },
      { regex: /\b(accused\s*no\b|accused\s*number)\s*([0-9]+)\s*(?:to|-)\s*(?:accused\s*no\b|accused\s*number\s*)?([0-9]+)\b/gi, replacement: "Accused Nos. $2 to $3" },
      { regex: /\b(accused\s*nos\b|accused\s*numbers)\s*([0-9]+)\b/gi, replacement: "Accused Nos. $2" },
      { regex: /\b(accused\s*no\b|accused\s*number|accused)\s*([0-9]+)\b/gi, replacement: "Accused No. $2" },
      { regex: /\b(appellant\s*no\b|appellant\s*number|appellant)\s*([0-9]+)\b/gi, replacement: "Appellant No. $2" },
      { regex: /\b(respondent\s*no\b|respondent\s*number|respondent)\s*([0-9]+)\b/gi, replacement: "Respondent No. $2" },
      { regex: /\b(petitioner\s*no\b|petitioner\s*number|petitioner)\s*([0-9]+)\b/gi, replacement: "Petitioner No. $2" },
      { regex: /\b(crime\s*no\b|crime\s*number)\s*([0-9]+)\s*\/\s*([0-9]+)\b/gi, replacement: "Crime No. $2/$3" },
      { regex: /\b(crime\s*no\b|crime\s*number)\s*([0-9]+)\b/gi, replacement: "Crime No. $2" },
      { regex: /\b(fir\s*no\b|fir\s*number)\s*([0-9]+)\s*(?:\/|of)\s*([0-9]+)\b/gi, replacement: "FIR No. $2/$3" },
      { regex: /\b(fir\s*no\b|fir\s*number)\s*([0-9]+)\b/gi, replacement: "FIR No. $2" },
      { regex: /\b(rigorous\s+imprisonment)\s*([0-9]+)\s*(month|months|year|years|day|days)\b/gi, replacement: "RI $2 $3" },
      { regex: /\b(simple\s+imprisonment)\s*([0-9]+)\s*(month|months|year|years|day|days)\b/gi, replacement: "SI $2 $3" },
      { regex: /\bsection\s+([0-9]+[a-z]?)\s+ipc\b/gi, replacement: "Section $1 IPC" },
      { regex: /\bsection\s+([0-9]+[a-z]?)\s+crpc\b/gi, replacement: "Section $1 CrPC" },
      { regex: /\bA\s*[-]?\s*([0-9]+)\s+to\s+A\s*[-]?\s*([0-9]+)\b/gi, replacement: "A$1 to A$2" },
      { regex: /\b(?:police\s+station|p\.?\s*s\.?)\s+([A-Z][a-z]+)\b/gi, replacement: "P.S. $1" },
      { regex: /\b(?:investigating\s+officer|i\.?\s*o\.?)\s*(?:p\.?\s*w\.?|pw)\s*[- ]?([0-9]+)\b/gi, replacement: "IO PW-$1" },
      { regex: /\b(?:police\s+constable|p\.?\s*c\.?)\s*(?:\(\s*)?(?:p\.?\s*w\.?|pw)\s*[- ]?([0-9]+)(?:\s*\))?\b/gi, replacement: "PC (PW$1)" },
      { regex: /\b(?:Hon(?:'ble)?\s+)?([A-Z][a-z]+(?:\s+[A-Z]\.?)*)\s+and\s+([A-Z][a-z]+(?:\s+[A-Z]\.?)*),?\s*J\.?\s*J\.?\b/gi, replacement: "$1 and $2, JJ." },
      { regex: /\b(?:heading\s+)?judgment\b/gi, replacement: "JUDGMENT\n\n" },
      { regex: /\b(?:heading\s+)?prosecution\s+case\b/gi, replacement: "PROSECUTION CASE\n\n" },
      { regex: /\b(?:heading\s+)?facts\s*:\b/gi, replacement: "FACTS:\n\n" },
      { regex: /\b(?:heading\s+)?held\s*:\b/gi, replacement: "HELD:\n\n" },
      { regex: /\bthe\s+captioned\s+appeal\s+stands\s+disposed\s+of\s+in\s+the\s+aforesaid\s+terms[.,;:?!]*/gi, replacement: "The captioned appeal stands disposed of in the aforesaid terms." },
      { regex: /\binterim\s+applications\s*,?\s*if\s+any\s*,?\s*shall\s+also\s+stand\s+disposed\s+of[.,;:?!]*/gi, replacement: "Interim applications, if any, shall also stand disposed of." },
      { regex: /\bthe\s+appellants\s+are\s+directed\s+to\s+be\s+released\s+forthwith\s*,?\s*if\s+lying\s+in\s+custody[.,;:?!]*/gi, replacement: "The Appellants are directed to be released forthwith, if lying in custody." },
      { regex: /\bthe\s+impugned\s+order\s+and\s+judgment\s+are\s+set\s+aside[.,;:?!]*/gi, replacement: "The impugned order and judgment are set aside." },
      { regex: /\bconsequently\s*,?\s*the\s+appellants\s+are\s+acquitted\s+from\s+all\s+the\s+charges\s+levelled\s+upon\s+them[.,;:?!]*/gi, replacement: "Consequently, the Appellants are acquitted from all the charges levelled upon them." },
    ];

    for (const rule of stenoRules) {
      cleaned = cleaned.replace(rule.regex, rule.replacement);
    }

    // Clean up spacing around inserted punctuation and brackets
    cleaned = cleaned
      .replace(/([(\[{])\s+/g, "$1") // remove spaces after opening brackets
      .replace(/\s+([)\]}])/g, "$1") // remove spaces before closing brackets
      .replace(/\s+([,.:;?!])/g, "$1") // remove spaces before punctuation
      .replace(/([,.:;?!])(?=[A-Za-z0-9])/g, "$1 ") // ensure space after punctuation if followed by word/number
      .replace(/([)\]}])(?=[A-Za-z0-9])/g, "$1 ") // ensure space after closing bracket if followed by word/number
      .replace(/"\s+([^"\n]+?)\s+"/g, '"$1"') // clean spaces inside double quotes
      .replace(/,\s*,+/g, ",") // deduplicate consecutive commas
      .replace(/[ \t]+\n/g, "\n")
      .replace(/(\n+)([a-z])/g, (m, p1, p2) => p1 + p2.toUpperCase()) // Capitalize words after newline
      .replace(/\b(S|D|W|H|Wd|C|R|F|M)\/o\.\s*(?=[A-Za-z0-9])/g, "$1/o. ")
      .replace(/\b(S|D|W|H|Wd|C|R|F|M)\/o\.\s*$/g, "$1/o.")
      .replace(/\b(S|D|W|H|Wd|C|R|F|M)\/o\.\s*,\s*/g, "$1/o., ");

    // If pure whitespace or break, preserve it exactly
    if (/^[\r\n\t ]+$/.test(cleaned)) {
      if (cleaned.includes("\n\n")) return "\n\n";
      if (cleaned.includes("\n")) return "\n";
      return " ";
    }

    return cleaned.trim();
  }

  // ==========================================
  // Engine Mode Switcher
  // ==========================================
  function updateEngineStatusUI() {
    const isOpneAI = (engineSelect && engineSelect.value === "openai");
    if (isOpneAI) {
      engineStatusText.textContent = "OpenAI Whisper Ready";
      liveEngineStatus.className = "status-badge";
      liveEngineStatus.style.background = "rgba(16, 185, 129, 0.1)";
      liveEngineStatus.style.color = "var(--accent-emerald)";
      liveEngineStatus.style.borderColor = "rgba(16, 185, 129, 0.3)";
    } else {
      engineStatusText.textContent = "Browser Engine Ready";
      liveEngineStatus.className = "status-badge";
      liveEngineStatus.style.background = "rgba(37, 99, 235, 0.1)";
      liveEngineStatus.style.color = "var(--accent-blue)";
      liveEngineStatus.style.borderColor = "rgba(37, 99, 235, 0.3)";
    }
  }

  if (engineSelect) {
    engineSelect.addEventListener("change", () => {
      if (isListening) {
        stopLiveDictation();
      }
      updateEngineStatusUI();
      const modeName = engineSelect.value === "openai" ? "OpenAI Whisper AI Model" : "Browser Native Speech API";
      showToast(`Live Engine set to ${modeName}`, "info", 2500);
    });
  }
  updateEngineStatusUI();

  // ==========================================
  // Pipeline 1: OpenAI Realtime Low-Latency Dual-WebSocket
  // Streams 16-bit PCM at 24kHz via Socket.IO to backend bridge
  // ==========================================
  async function startOpenAILiveDictation() {
    try {
      micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      // Hook up live audio waveform visualizer and PCM streaming via Web Audio API
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      audioContext = new AudioCtx();
      const source = audioContext.createMediaStreamSource(micStream);
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 64;
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const waveBars = audioVisualizer.querySelectorAll(".wave-bar");

      function updateWaveform() {
        if (!isListening) return;
        analyser.getByteFrequencyData(dataArray);
        for (let i = 0; i < 9; i++) {
          const val = dataArray[i] || 0;
          const barHeight = Math.max(6, Math.min(30, (val / 255) * 36));
          if (waveBars[i]) {
            waveBars[i].style.height = `${barHeight}px`;
          }
        }
        visualizerAnimFrame = requestAnimationFrame(updateWaveform);
      }
      updateWaveform();

      // Establish real-time session on backend
      if (socket && socket.connected) {
        socket.emit("start_realtime_dictation", {
          language_code: "en",
        });
      }

      // Audio processor for streaming PCM chunks to server
      // bufferSize 4096 gives ~85-93ms latency chunks
      audioProcessor = audioContext.createScriptProcessor(4096, 1, 1);
      audioProcessor.onaudioprocess = (e) => {
        if (!isListening) return;
        const inputData = e.inputBuffer.getChannelData(0);
        const pcm16 = floatTo16BitPCM(inputData, audioContext.sampleRate, 24000);
        if (socket && socket.connected) {
          socket.emit("audio_chunk", pcm16.buffer);
        }
      };

      source.connect(audioProcessor);
      audioProcessor.connect(audioContext.destination);

      isListening = true;
      btnStartLive.classList.add("btn-record-active");
      btnStartLive.disabled = true;
      btnStopLive.disabled = false;

      micStateBadge.textContent = "OPENAI REALTIME";
      micStateBadge.style.background = "rgba(239, 68, 68, 0.15)";
      micStateBadge.style.color = "var(--accent-rose)";
      micStateBadge.style.borderColor = "rgba(239, 68, 68, 0.4)";

      audioVisualizer.classList.add("listening");
      liveDictationCard.classList.add("listening");
      liveStreamPlaceholder.style.display = "none";

      showToast("OpenAI Realtime low-latency dictation active. Speak into microphone.", "info", 3000);
    } catch (err) {
      console.error("Microphone capture error:", err);
      showToast("Microphone access denied or audio input unavailable.", "error", 5000);
      stopOpenAILiveDictation();
    }
  }

  function stopOpenAILiveDictation() {
    isListening = false;
    if (openaiLiveIndicator) openaiLiveIndicator.style.display = "none";

    // Notify backend to close OpenAI Realtime session
    if (socket && socket.connected) {
      socket.emit("stop_realtime_dictation");
    }

    if (audioProcessor) {
      try {
        audioProcessor.disconnect();
      } catch (e) {}
      audioProcessor = null;
    }

    if (micStream) {
      try {
        micStream.getTracks().forEach((track) => track.stop());
      } catch (e) {}
      micStream = null;
    }

    if (visualizerAnimFrame) {
      cancelAnimationFrame(visualizerAnimFrame);
      visualizerAnimFrame = null;
    }

    if (audioContext && audioContext.state !== "closed") {
      try {
        audioContext.close();
      } catch (e) {}
    }

    btnStartLive.classList.remove("btn-record-active");
    btnStartLive.disabled = false;
    btnStopLive.disabled = true;

    micStateBadge.textContent = "Standby";
    micStateBadge.style.background = "rgba(37,99,235,0.15)";
    micStateBadge.style.color = "var(--accent-blue)";
    micStateBadge.style.borderColor = "rgba(37,99,235,0.3)";

    audioVisualizer.classList.remove("listening");
    liveDictationCard.classList.remove("listening");
    const waveBars = audioVisualizer.querySelectorAll(".wave-bar");
    waveBars.forEach((bar) => (bar.style.height = "6px"));

    if (!finalSpeechText.trim()) {
      liveStreamPlaceholder.style.display = "inline";
    }
  }

  // ==========================================
  // Pipeline 2: Browser Web Speech API
  // ==========================================
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (SpeechRecognition) {
    webSpeechRecognition = new SpeechRecognition();
    webSpeechRecognition.continuous = true;
    webSpeechRecognition.interimResults = true;
    webSpeechRecognition.lang = languageSelect.value || "en-IN";

    webSpeechRecognition.onstart = () => {
      isListening = true;
      btnStartLive.classList.add("btn-record-active");
      btnStartLive.disabled = true;
      btnStopLive.disabled = false;

      micStateBadge.textContent = "BROWSER LIVE";
      micStateBadge.style.background = "rgba(239, 68, 68, 0.15)";
      micStateBadge.style.color = "var(--accent-rose)";
      micStateBadge.style.borderColor = "rgba(239, 68, 68, 0.4)";

      audioVisualizer.classList.add("listening");
      liveDictationCard.classList.add("listening");
      liveStreamPlaceholder.style.display = "none";
      showToast("Browser live dictation active. Speak into microphone.", "info", 2500);
    };

    webSpeechRecognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const transcriptPart = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          const converted = applyLiveStenoShothand(transcriptPart);
          finalSpeechText = appendToTranscript(finalSpeechText, converted);

          // Synchronize directly into main judicial editor
          transcriptTextarea.value = appendToTranscript(transcriptTextarea.value, converted);
          updateEditorStats();
        } else {
          interim += transcriptPart;
        }
      }

      finalTranscriptBuffer.textContent = finalSpeechText;
      interimTranscriptBuffer.textContent = interim ? " " + interim : "";
      scrollLiveStreamToBottom();
      updateLiveStats();
    };

    webSpeechRecognition.onerror = (event) => {
      if (event.error === "not-allowed") {
        showToast("Microphone access denied. Please grant permission in browser.", "error", 5000);
        stopWebSpeechDictation();
      } else if (event.error !== "no-speech") {
        showToast(`Dictation notification: ${event.error}`, "info", 3000);
      }
    };

    webSpeechRecognition.onend = () => {
      if (isListening && engineSelect.value === "browser") {
        try {
          webSpeechRecognition.start();
        } catch (e) {
          stopWebSpeechDictation();
        }
      } else {
        stopWebSpeechDictation();
      }
    };
  }

  function startWebSpeechDictation() {
    if (!webSpeechRecognition) {
      showToast("Web Speech API is not supported in this browser. Please use OpenAI Whisper engine.", "error", 5000);
      return;
    }
    try {
      webSpeechRecognition.lang = languageSelect.value || "en-IN";
      webSpeechRecognition.start();
    } catch (err) {
      console.error("Start WebSpeech error:", err);
    }
  }

  function stopWebSpeechDictation() {
    isListening = false;
    if (webSpeechRecognition) {
      try {
        webSpeechRecognition.stop();
      } catch (e) {}
    }

    btnStartLive.classList.remove("btn-record-active");
    btnStartLive.disabled = false;
    btnStopLive.disabled = true;

    micStateBadge.textContent = "Standby";
    micStateBadge.style.background = "rgba(37,99,235,0.15)";
    micStateBadge.style.color = "var(--accent-blue)";
    micStateBadge.style.borderColor = "rgba(37,99,235,0.3)";

    audioVisualizer.classList.remove("listening");
    liveDictationCard.classList.remove("listening");
    interimTranscriptBuffer.textContent = "";
    updateLiveStats();

    if (!finalSpeechText.trim()) {
      liveStreamPlaceholder.style.display = "inline";
    }
  }

  // ==========================================
  // Unified Live Dictation Controls
  // ==========================================
  function startLiveDictation() {
    const selectedEngine = engineSelect ? engineSelect.value : "openai";
    if (selectedEngine === "openai") {
      startOpenAILiveDictation();
    } else {
      startWebSpeechDictation();
    }
  }

  function stopLiveDictation() {
    const selectedEngine = engineSelect ? engineSelect.value : "openai";
    if (selectedEngine === "openai") {
      stopOpenAILiveDictation();
    } else {
      stopWebSpeechDictation();
    }
  }

  btnStartLive.addEventListener("click", startLiveDictation);
  btnStopLive.addEventListener("click", stopLiveDictation);

  if (btnCopyLive) {
    btnCopyLive.addEventListener("click", async () => {
      const fullText = (finalSpeechText + " " + (interimTranscriptBuffer ? interimTranscriptBuffer.textContent : "")).trim();
      if (!fullText) {
        showToast("Live dictation buffer is empty.", "error", 2000);
        return;
      }
      try {
        await navigator.clipboard.writeText(fullText);
        showToast("Live transcription copied to clipboard!", "success", 2000);
      } catch (err) {
        showToast("Failed to copy live transcription.", "error", 2000);
      }
    });
  }

  btnClearLive.addEventListener("click", () => {
    finalSpeechText = "";
    finalTranscriptBuffer.textContent = "";
    interimTranscriptBuffer.textContent = "";
    updateLiveStats();
    if (!isListening) {
      liveStreamPlaceholder.style.display = "inline";
    }
    showToast("Live dictation buffer cleared.", "info", 2000);
  });

  btnAppendLive.addEventListener("click", () => {
    const textToAppend = finalSpeechText.trim();
    if (!textToAppend) {
      showToast("No live transcript to append. Dictate something first.", "error", 2500);
      return;
    }

    const currentText = transcriptTextarea.value.trim();
    transcriptTextarea.value = currentText ? currentText + "\n\n" + textToAppend : textToAppend;
    updateEditorStats();
    showToast("Appended live transcript to Courtroom Editor.", "success", 2500);

    finalSpeechText = "";
    finalTranscriptBuffer.textContent = "";
    interimTranscriptBuffer.textContent = "";
    updateLiveStats();
    if (!isListening) {
      liveStreamPlaceholder.style.display = "inline";
    }
  });

  // Language change
  languageSelect.addEventListener("change", () => {
    if (webSpeechRecognition) {
      webSpeechRecognition.lang = languageSelect.value;
    }
    showToast(`Recognition language: ${languageSelect.options[languageSelect.selectedIndex].text}`, "info", 2000);
  });

  // ==========================================
  // Courtroom Editor Counters & Helpers
  // ==========================================
  function updateEditorStats() {
    const text = transcriptTextarea.value.trim();
    const words = text ? text.split(/\s+/).filter(Boolean).length : 0;
    const chars = text.length;
    const paras = text ? text.split(/\n+/).filter((p) => p.trim().length > 0).length : 0;

    statWords.textContent = `${words} word${words === 1 ? "" : "s"}`;
    statChars.textContent = `${chars} character${chars === 1 ? "" : "s"}`;
    statParagraphs.textContent = `${paras} paragraph${paras === 1 ? "" : "s"}`;
  }

  transcriptTextarea.addEventListener("input", updateEditorStats);

  btnCopyEditor.addEventListener("click", async () => {
    const text = transcriptTextarea.value;
    if (!text.trim()) {
      showToast("Editor is empty.", "error", 2000);
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      showToast("Transcript copied to clipboard!", "success", 2000);
    } catch (err) {
      showToast("Failed to copy transcript.", "error", 2000);
    }
  });

  btnClearEditor.addEventListener("click", () => {
    if (confirm("Are you sure you want to clear the courtroom transcript editor?")) {
      transcriptTextarea.value = "";
      updateEditorStats();
      showToast("Editor cleared.", "info", 2000);
    }
  });

  // ==========================================
  // Backend API Actions: Normalization & Draft
  // ==========================================
  btnNormalize.addEventListener("click", async () => {
    const text = transcriptTextarea.value.trim();
    if (!text) {
      showToast("Please enter or dictate some text to normalize.", "error", 2500);
      return;
    }

    const originalBtnHtml = btnNormalize.innerHTML;
    btnNormalize.disabled = true;
    btnNormalize.innerHTML = `<span>⏳</span> Normalizing...`;

    try {
      const response = await fetch("/api/normalize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      const data = await response.json();
      if (data.success && data.normalized_text) {
        transcriptTextarea.value = data.normalized_text;
        updateEditorStats();
        showToast("Steno & legal terms normalized successfully!", "success", 3000);
      } else {
        showToast(data.error || "Failed to normalize transcript.", "error", 3000);
      }
    } catch (err) {
      console.error("Normalize error:", err);
      showToast("Connection error while normalizing text.", "error", 3000);
    } finally {
      btnNormalize.disabled = false;
      btnNormalize.innerHTML = originalBtnHtml;
    }
  });

  btnGenerateDraft.addEventListener("click", async () => {
    const transcript = transcriptTextarea.value.trim();
    if (!transcript) {
      showToast("Please provide transcript content to generate an order draft.", "error", 2500);
      return;
    }

    const originalBtnHtml = btnGenerateDraft.innerHTML;
    btnGenerateDraft.disabled = true;
    btnGenerateDraft.innerHTML = `<span>⏳</span> Structuring Draft...`;

    try {
      const response = await fetch("/api/generate-draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript,
        }),
      });

      const data = await response.json();
      if (data.success && data.draft) {
        draftPanel.textContent = data.draft;
        showToast("Judge's Order Draft generated successfully!", "success", 3500);
        draftPanel.scrollIntoView({ behavior: "smooth", block: "center" });
      } else {
        showToast(data.error || "Failed to generate draft.", "error", 3000);
      }
    } catch (err) {
      console.error("Generate draft error:", err);
      showToast("Connection error while generating draft.", "error", 3000);
    } finally {
      btnGenerateDraft.disabled = false;
      btnGenerateDraft.innerHTML = originalBtnHtml;
    }
  });

  btnCopyDraft.addEventListener("click", async () => {
    const draftText = draftPanel.textContent.trim();
    if (!draftText) {
      showToast("No draft to copy.", "error", 2000);
      return;
    }
    try {
      await navigator.clipboard.writeText(draftText);
      showToast("Order draft copied to clipboard!", "success", 2000);
    } catch (err) {
      showToast("Failed to copy draft.", "error", 2000);
    }
  });

  btnInsertDraft.addEventListener("click", () => {
    const draftText = draftPanel.textContent.trim();
    if (!draftText) {
      showToast("No draft generated yet.", "error", 2000);
      return;
    }
    transcriptTextarea.value = draftText;
    updateEditorStats();
    showToast("Order draft placed into Main Courtroom Editor.", "success", 2500);
    transcriptTextarea.scrollIntoView({ behavior: "smooth", block: "center" });
  });

  // ==========================================
  // Document Exports (.docx and PDF)
  // ==========================================
  async function downloadDocument(url, filenameDefault) {
    const text = transcriptTextarea.value.trim();
    if (!text) {
      showToast("Cannot export an empty transcript.", "error", 2500);
      return;
    }

    const formData = new FormData();
    formData.append("text", text);
    formData.append("title", "COURT PROCEEDINGS / JUDGE'S RECORD");
    formData.append("case_no", "Official Record");

    try {
      showToast("Preparing document download...", "info", 2000);
      const res = await fetch(url, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        showToast(errorData.error || "Export failed.", "error", 3000);
        return;
      }

      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = filenameDefault;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
      showToast("Document downloaded successfully!", "success", 3000);
    } catch (err) {
      console.error("Export error:", err);
      showToast("Error downloading document.", "error", 3000);
    }
  }

  btnExportDocx.addEventListener("click", () => {
    downloadDocument("/api/export/docx", `Court_Transcript_${new Date().toISOString().slice(0, 10)}.docx`);
  });

  btnExportPdf.addEventListener("click", () => {
    downloadDocument("/api/export/pdf", `Court_Transcript_${new Date().toISOString().slice(0, 10)}.pdf`);
  });

  // ==========================================
  // Audio File Upload & Transcription
  // ==========================================
  function handleFileSelection(file) {
    if (!file) return;

    if (!file.type.startsWith("audio/") && !/\.(mp3|wav|m4a|webm|ogg|aac|flac)$/i.test(file.name)) {
      showToast("Please select a valid audio file (.mp3, .wav, .m4a, .webm, .ogg).", "error", 4000);
      return;
    }

    if (file.size > 64 * 1024 * 1024) {
      showToast("File size exceeds 64MB limit.", "error", 4000);
      return;
    }

    selectedAudioFile = file;
    selectedFileName.textContent = file.name;
    selectedFileSize.textContent = `(${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
    selectedFileInfo.style.display = "flex";
    btnTranscribeFile.disabled = false;
    showToast(`Loaded audio file: ${file.name}`, "info", 2500);
  }

  audioFileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelection(e.target.files[0]);
    }
  });

  uploadDropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadDropzone.classList.add("dragover");
  });

  uploadDropzone.addEventListener("dragleave", () => {
    uploadDropzone.classList.remove("dragover");
  });

  uploadDropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadDropzone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  });

  btnRemoveFile.addEventListener("click", (e) => {
    e.stopPropagation();
    selectedAudioFile = null;
    audioFileInput.value = "";
    selectedFileInfo.style.display = "none";
    btnTranscribeFile.disabled = true;
    showToast("Audio file removed.", "info", 2000);
  });

  btnTranscribeFile.addEventListener("click", async () => {
    if (!selectedAudioFile) {
      showToast("No audio file selected.", "error", 2500);
      return;
    }

    const originalBtnHtml = btnTranscribeFile.innerHTML;
    btnTranscribeFile.disabled = true;
    btnTranscribeFile.innerHTML = `<span>⏳</span> Transcribing Audio...`;

    const formData = new FormData();
    formData.append("audio_file", selectedAudioFile);
    formData.append("model", "whisper-1");
    formData.append("language_code", "en");

    try {
      showToast("Sending audio to OpenAI Whisper pipeline...", "info", 3000);
      const res = await fetch("/api/transcribe", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (data.success && data.text) {
        const currentText = transcriptTextarea.value.trim();
        transcriptTextarea.value = currentText ? currentText + "\n\n" + data.text : data.text;
        updateEditorStats();
        showToast("Audio transcription completed successfully!", "success", 4000);
        
        // Auto-switch to Courtroom Editor tab to show the transcript
        switchTab("tab-editor");
        transcriptTextarea.scrollIntoView({ behavior: "smooth", block: "center" });
      } else {
        showToast(data.error || "Failed to transcribe audio file.", "error", 4500);
      }
    } catch (err) {
      console.error("Transcribe audio error:", err);
      showToast("Network error during audio transcription.", "error", 4000);
    } finally {
      btnTranscribeFile.disabled = false;
      btnTranscribeFile.innerHTML = originalBtnHtml;
    }
  });

  // ==========================================
  // Benchmark Presets Loader (English Only)
  // ==========================================
  const presetCards = document.querySelectorAll(".preset-card");
  presetCards.forEach((card) => {
    card.addEventListener("click", async () => {
      const sampleId = card.dataset.sampleId;
      try {
        const res = await fetch(`/api/samples/${sampleId}`);
        const data = await res.json();
        if (data.success && data.text) {
          transcriptTextarea.value = data.text;
          updateEditorStats();
          showToast(`Loaded: ${data.title}`, "success", 3000);

          // Auto-switch to Courtroom Editor tab to show the loaded preset
          switchTab("tab-editor");
          transcriptTextarea.scrollIntoView({ behavior: "smooth", block: "center" });
        } else {
          showToast("Failed to load preset sample.", "error", 2500);
        }
      } catch (err) {
        console.error("Sample load error:", err);
        showToast("Error loading preset.", "error", 2500);
      }
    });
  });

  // ==========================================
  // Tab Navigation Controller
  // Tab 1: Live Stenographer Dictation (Default)
  // Tab 2: Courtroom Editor & Order Draft
  // Tab 3: Audio Transcription & Reference
  // ==========================================
  const courtTabButtons = document.querySelectorAll(".court-tab-btn");
  const courtTabPanes = document.querySelectorAll(".tab-pane");

  function switchTab(targetTabId) {
    if (!targetTabId) return;

    courtTabButtons.forEach((btn) => {
      const isTarget = btn.dataset.tab === targetTabId;
      btn.classList.toggle("active", isTarget);
      btn.setAttribute("aria-selected", isTarget ? "true" : "false");
    });

    courtTabPanes.forEach((pane) => {
      const isTarget = pane.id === targetTabId;
      pane.classList.toggle("active", isTarget);
      pane.style.display = isTarget ? "block" : "none";
    });

    // If switching to live tab, auto-scroll to bottom of chat
    if (targetTabId === "tab-live") {
      setTimeout(scrollLiveStreamToBottom, 50);
    }
  }

  courtTabButtons.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const targetTabId = btn.dataset.tab;
      if (targetTabId) {
        switchTab(targetTabId);
      }
    });
  });

  // Ensure Tab 1 (Live Stenographer Dictation) is active and selected by default
  switchTab("tab-live");

  // Initial stats call
  updateEditorStats();
  updateLiveStats();
});
