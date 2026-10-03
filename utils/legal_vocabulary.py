"""
Legal Vocabulary and Normalization for Courtroom Judicial Stenographer.

Contains curated legal terms, statutes, codes, and procedural terminology
in English, Marathi, and Hindi.
STRICT RULE:
- Transcribe verbatim as spoken without any cross-language translation.
- Spoken English is typed in English (Latin alphabet).
- Spoken Marathi is typed in Marathi (Devanagari script).
- Spoken Hindi is typed in Hindi (Devanagari script).
- Mixed code-switching is typed in mixed scripts verbatim.
"""

import re
from typing import Dict, List, Optional, Tuple

# Curated list of Indian courtroom terminology
LEGAL_TERMS_EN: List[str] = [
    # Judge & Bench
    "Hon'ble Court",
    "Honourable Court",
    "Presiding Officer",
    "Judge",
    "Magistrate",
    "Registrar",
    
    # Parties & Counsel
    "Applicant",
    "Respondent",
    "Petitioner",
    "Appellant",
    "Plaintiff",
    "Defendant",
    "Accused",
    "Complainant",
    "Witness",
    "Counsel",
    "Advocate",
    "Learned Counsel",
    "Learned Senior Counsel",
    "Public Prosecutor",
    "Amicus Curiae",
    
    # Filings & Pleadings
    "Affidavit",
    "Application",
    "Petition",
    "Written Statement",
    "Plaint",
    "Appeal",
    "Special Leave Petition",
    "Vakalatnama",
    "Caveat",
    "Submissions",
    "Rejoinder",
    "Exhibit",
    "Evidence",
    "Deposition",
    
    # Orders & Dispositions
    "Oral Dictation",
    "Order",
    "Judgment",
    "Decree",
    "Injunction",
    "Interim Relief",
    "Stay Order",
    "Bail",
    "Anticipatory Bail",
    "Adjournment",
    "Adjourned",
    
    # Statutory Codes & Acts
    "CPC",
    "CrPC",
    "IPC",
    "BNS",
    "BNSS",
    "BSA",
    "Civil Procedure Code",
    "Criminal Procedure Code",
    "Indian Penal Code",
    "Bharatiya Nyaya Sanhita",
    "Bharatiya Nagarik Suraksha Sanhita",
    "Bharatiya Sakshya Adhiniyam",
    "Constitution of India",
    "Negotiable Instruments Act",
    
    # Common Statutory Provisions
    "Section 144",
    "Section 420",
    "Section 302",
    "Section 138",
    "Section 482",
    "Section 439",
    "Section 9",
    "Article 226",
    "Article 32",
    "Article 21",
    "Order 39 Rule 1",
    "Order 39 Rule 2",
]

LEGAL_TERMS_MR: List[str] = [
    "नामदार न्यायालय", "माननीय न्यायालय", "न्यायाधीश", "दंडाधिकारी", "अर्जदार", "प्रतिवादी",
    "याचिकाकर्ता", "आरोपी", "तक्रारदार", "साक्षीदार", "वकील", "विद्वान वकील", "विद्वान वरिष्ठ वकील",
    "सरकारी वकील", "प्रतिज्ञापत्र", "लेखी जबाब", "अर्ज", "युक्तिवाद", "पुरावा", "कामकाज",
    "मौखिक आदेश", "आदेश", "निकाल", "जामीन", "अगाऊ जामीन", "अंतरिम दिलासा", "तहकूब",
    "कलम 144", "कलम 420", "कलम 302", "कलम 138", "कलम 482", "कलम 439",
    "सीपीसी", "सीआरपीसी", "आयपीसी", "बीएनएस", "बीएनएसएस", "बीएसए",
    "दिवाणी प्रक्रिया संहिता", "फौजदारी प्रक्रिया संहिता", "भारतीय संविधान", "उच्च न्यायालय", "सर्वोच्च न्यायालय"
]

LEGAL_TERMS_HI: List[str] = [
    "माननीय न्यायालय", "न्यायाधीश", "दंडाधिकारी", "आवेदक", "प्रतिवादी", "याचिकाकर्ता",
    "अभियुक्त", "शिकायतकर्ता", "गवाह", "अधिवक्ता", "विद्वान अधिवक्ता", "विद्वान वरिष्ठ अधिवक्ता",
    "लोक अभियोजक", "शपथ पत्र", "लिखित बयान", "याचिका", "दलीलें", "साक्ष्य", "कार्यवाही",
    "मौखिक आदेश", "आदेश", "निर्णय", "जमानत", "अग्रिम जमानत", "अंतरिम राहत", "स्थगन",
    "धारा 144", "धारा 420", "धारा 302", "धारा 138", "धारा 482", "धारा 439",
    "सीपीसी", "सीआरपीसी", "आईपीसी", "बीएनएस", "बीएनएसएस", "बीएसए",
    "दीवानी प्रक्रिया संहिता", "दंड प्रक्रिया संहिता", "भारतीय संविधान", "उच्च न्यायालय", "सर्वोच्च न्यायालय"
]

LEGAL_TERMS: List[str] = LEGAL_TERMS_EN + LEGAL_TERMS_MR + LEGAL_TERMS_HI


def get_legal_prompt_context(language_code: Optional[str] = None) -> str:
    """
    Constructs a concise legal prompt for the OpenAI Audio API.
    CRITICAL STENOGRAPHY INSTRUCTION:
    - Never translate.
    - Spoken English is typed in English.
    - Spoken Marathi is typed in Marathi (Devanagari).
    - Spoken Hindi is typed in Hindi (Devanagari).
    - Mixed language is typed verbatim in both scripts.
    """
    lang = (language_code or "").lower()

    if lang in ("mr", "mr-in"):
        return (
            "न्यायाधीशांचे मौखिक डिक्टेशन / न्यायालयीन कामकाज प्रतिलेख: नामदार न्यायालय, अर्जदार, प्रतिवादी, "
            "विद्वान वकील, प्रतिज्ञापत्र, युक्तिवाद, पुरावा, कलम 144, कलम 420, कलम 302, कलम 138, कलम 482, कलम 439, "
            "सीपीसी, सीआरपीसी, आयपीसी, बीएनएस, जामीन मंजूर, अंतरिम दिलासा, आदेश, निकाल. "
            "Strict instruction: Transcribe exactly as spoken without translation. Marathi in Devanagari, English in English."
        )
    elif lang in ("hi", "hi-in"):
        return (
            "न्यायाधीश महोदय का मौखिक डिक्टेशन / न्यायालयीन कार्यवाही प्रतिलेख: माननीय न्यायालय, आवेदक, प्रतिवादी, "
            "विद्वान अधिवक्ता, शपथ पत्र, दलीलें, साक्ष्य, धारा 144, धारा 420, धारा 302, धारा 138, धारा 482, "
            "सीपीसी, सीआरपीसी, आईपीसी, बीएनएस, जमानत, अंतरिम राहत, आदेश, निर्णय। "
            "Strict instruction: Transcribe exactly as spoken without translation. Hindi in Devanagari, English in English."
        )
    elif lang in ("en", "en-in"):
        return (
            "Verbatim judicial stenographer record of Judge's oral statement and court dictation: "
            "Hon'ble Court, Judge, Order, Applicant, Respondent, Petitioner, Counsel, Learned Counsel, "
            "Affidavit, Submissions, Exhibit, Proceedings, Section 144, Section 420, Section 302, Section 138, "
            "CPC, CrPC, IPC, BNS, BNSS, BSA, Bail, Adjourned. Transcribe verbatim as spoken without translation."
        )
    else:
        # Mixed (English + Marathi / Hindi) - DEFAULT FOR INDIAN COURTS
        return (
            "Official judicial stenographer verbatim record of Judge's oral dictation and court proceedings. "
            "CRITICAL RULE: Transcribe exactly as spoken without any translation. "
            "Type English speech in English (Latin script). "
            "Type Marathi speech in Marathi (Devanagari script). "
            "Type Hindi speech in Hindi (Devanagari script). "
            "If the Judge speaks mixed English and Marathi or switches languages, transcribe the mixed language verbatim. "
            "Do NOT translate Marathi to English or English to Marathi. "
            "Terms: Hon'ble Court, Order, Adjourned, Section 144, Section 420, Section 439, CPC, CrPC, IPC, BNS, Exhibit, "
            "नामदार न्यायालय, अर्जदार, प्रतिवादी, विद्वान वकील, कलम 144, कलम 420, कलम 439, सीपीसी, सीआरपीसी, जामीन मंजूर, अंतरिम दिलासा, निकाल, "
            "माननीय न्यायालय, आवेदक, धारा 144, जमानत."
        )


# Devanagari digits to Arabic mapping
_DEV_DIGITS_MAP = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
}


def _replace_dev_digits(match: re.Match) -> str:
    prefix = match.group(1)
    digits = match.group(2)
    arabic_digits = "".join(_DEV_DIGITS_MAP.get(c, c) for c in digits)
    return f"{prefix} {arabic_digits}"


def normalize_legal_terms(text: str, enabled: bool = True, language_code: Optional[str] = None) -> str:
    """
    Applies conservative legal formatting without translating across languages.
    Preserves English in English, Marathi in Marathi, and Hindi in Hindi.
    """
    if not enabled or not text:
        return text

    normalized = text

    # 1. Standardize Devanagari numerals in section citations while preserving the language word
    # e.g. "कलम १४४" -> "कलम 144", "धारा १४४" -> "धारा 144"
    normalized = re.sub(r"(धारा|कलम)\s*([०-९]+)", _replace_dev_digits, normalized)

    # 2. Marathi Statutory Sections & Honorifics (NO translation to English)
    mr_patterns: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"कलम\s*(?:एकशे\s*चव्वेचाळीस|एक\s*शे\s*चव्वेचाळीस)", re.IGNORECASE), "कलम 144"),
        (re.compile(r"कलम\s*(?:चारशे\s*वीस|चार\s*शे\s*वीस)", re.IGNORECASE), "कलम 420"),
        (re.compile(r"कलम\s*(?:तीनशे\s*दोन|तीन\s*शे\s*दोन)", re.IGNORECASE), "कलम 302"),
        (re.compile(r"कलम\s*(?:एकशे\s*अडतीस|एक\s*शे\s*अडतीस)", re.IGNORECASE), "कलम 138"),
        (re.compile(r"कलम\s*(?:चारशे\s*ब्याऐंशी|चार\s*शे\s*ब्याऐंशी)", re.IGNORECASE), "कलम 482"),
        (re.compile(r"कलम\s*(?:चारशे\s*एकोणचाळीस|चार\s*शे\s*एकोणचाळीस)", re.IGNORECASE), "कलम 439"),
        (re.compile(r"(?:नामदार\s+कोर्ट|माननीय\s+कोर्ट)", re.IGNORECASE), "नामदार न्यायालय"),
        (re.compile(r"विद्वान\s+अधिवक्ता", re.IGNORECASE), "विद्वान वकील"),
    ]
    for pattern, replacement in mr_patterns:
        normalized = pattern.sub(replacement, normalized)

    # 3. Hindi Statutory Sections & Honorifics (NO translation to English)
    hi_patterns: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"धारा\s*(?:एक\s*सौ\s*चवालीस|एक\s*सौ\s*चौवालीस)", re.IGNORECASE), "धारा 144"),
        (re.compile(r"धारा\s*(?:चार\s*सौ\s*बीस)", re.IGNORECASE), "धारा 420"),
        (re.compile(r"धारा\s*(?:तीन\s*सौ\s*दो)", re.IGNORECASE), "धारा 302"),
        (re.compile(r"धारा\s*(?:एक\s*सौ\s*अड़तीस|एक\s*सौ\s*अडतीस)", re.IGNORECASE), "धारा 138"),
        (re.compile(r"धारा\s*(?:चार\s*सौ\s*बयासी)", re.IGNORECASE), "धारा 482"),
        (re.compile(r"धारा\s*(?:चार\s*सौ\s*उनतालीस)", re.IGNORECASE), "धारा 439"),
        (re.compile(r"(?:माननीय\s+कोर्ट|नामदार\s+कोर्ट)", re.IGNORECASE), "माननीय न्यायालय"),
    ]
    for pattern, replacement in hi_patterns:
        normalized = pattern.sub(replacement, normalized)

    # 4. Vernacular Legal Acronyms
    acronym_vernacular: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"(?:\b|^|\s)(?:सी\.?\s*पी\.?\s*सी\.?|सी\s+पी\s+सी|सीपीसी)(?=\b|\s|[.,;:?!]|$)", re.IGNORECASE), " सीपीसी"),
        (re.compile(r"(?:\b|^|\s)(?:सी\.?\s*आर\.?\s*पी\.?\s*सी\.?|सी\s*आर\s*पी\s*सी|सीआरपीसी)(?=\b|\s|[.,;:?!]|$)", re.IGNORECASE), " सीआरपीसी"),
        (re.compile(r"(?:\b|^|\s)(?:आय\.?\s*पी\.?\s*सी\.?|आयपीसी)(?=\b|\s|[.,;:?!]|$)", re.IGNORECASE), " आयपीसी"),
        (re.compile(r"(?:\b|^|\s)(?:आई\.?\s*पी\.?\s*सी\.?|आईपीसी)(?=\b|\s|[.,;:?!]|$)", re.IGNORECASE), " आईपीसी"),
        (re.compile(r"(?:\b|^|\s)(?:बी\.?\s*एन\.?\s*एस\.?|बी\s*एन\s*एस|बीएनएस)(?=\b|\s|[.,;:?!]|$)", re.IGNORECASE), " बीएनएस"),
        (re.compile(r"(?:\b|^|\s)(?:बी\.?\s*एन\.?\s*एस\.?\s*एस\.?|बीएनएसएस)(?=\b|\s|[.,;:?!]|$)", re.IGNORECASE), " बीएनएसएस"),
        (re.compile(r"(?:\b|^|\s)(?:बी\.?\s*एस\.?\s*ए\.?|बीएसए)(?=\b|\s|[.,;:?!]|$)", re.IGNORECASE), " बीएसए"),
    ]
    for pattern, replacement in acronym_vernacular:
        normalized = pattern.sub(replacement, normalized)

    # 5. English Statutory Sections (NO translation to Marathi/Hindi)
    section_patterns: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"\b(?:section|sec\.?)\s+one\s+forty[- ]?four\b", re.IGNORECASE), "Section 144"),
        (re.compile(r"\b(?:section|sec\.?)\s+four\s+twenty\b", re.IGNORECASE), "Section 420"),
        (re.compile(r"\b(?:section|sec\.?)\s+(?:three\s+zero\s+two|three\s+hundred\s+(?:and\s+)?two)\b", re.IGNORECASE), "Section 302"),
        (re.compile(r"\b(?:section|sec\.?)\s+one\s+thirty[- ]?eight\b", re.IGNORECASE), "Section 138"),
        (re.compile(r"\b(?:section|sec\.?)\s+four\s+eighty[- ]?two\b", re.IGNORECASE), "Section 482"),
        (re.compile(r"\b(?:section|sec\.?)\s+four\s+thirty[- ]?nine\b", re.IGNORECASE), "Section 439"),
        (re.compile(r"\bsection\s+(\d+[A-Z]?)\b", re.IGNORECASE), r"Section \1"),
        (re.compile(r"\bsec(?:tion)?\.?\s+(\d+[A-Z]?)\b", re.IGNORECASE), r"Section \1"),
        (re.compile(r"\barticle\s+(two\s+twenty[- ]?six|226)\b", re.IGNORECASE), "Article 226"),
        (re.compile(r"\barticle\s+(thirty[- ]?two|32)\b", re.IGNORECASE), "Article 32"),
        (re.compile(r"\barticle\s+(twenty[- ]?one|21)\b", re.IGNORECASE), "Article 21"),
        (re.compile(r"\barticle\s+(\d+[A-Z]?)\b", re.IGNORECASE), r"Article \1"),
        (re.compile(r"\border\s+(\d+)\s+rule\s+(\d+)\b", re.IGNORECASE), r"Order \1 Rule \2"),
    ]
    for pattern, replacement in section_patterns:
        normalized = pattern.sub(replacement, normalized)

    # 6. English Legal Acronyms
    acronym_patterns: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"\b(?:C\.?\s*P\.?\s*C\.?|c\s+p\s+c)\b", re.IGNORECASE), "CPC"),
        (re.compile(r"\b(?:Cr\.?\s*P\.?\s*C\.?|cr\s+p\s+c)\b", re.IGNORECASE), "CrPC"),
        (re.compile(r"\b(?:I\.?\s*P\.?\s*C\.?|i\s+p\s+c)\b", re.IGNORECASE), "IPC"),
        (re.compile(r"\b(?:B\.?\s*N\.?\s*S\.?|b\s+n\s+s)\b", re.IGNORECASE), "BNS"),
        (re.compile(r"\b(?:B\.?\s*N\.?\s*S\.?\s*S\.?|b\s+n\s+s\s+s)\b", re.IGNORECASE), "BNSS"),
        (re.compile(r"\b(?:B\.?\s*S\.?\s*A\.?|b\s+s\s+a)\b", re.IGNORECASE), "BSA"),
        (re.compile(r"\b(?:F\.?\s*I\.?\s*R\.?|f\s+i\s+r)\b", re.IGNORECASE), "FIR"),
    ]
    for pattern, replacement in acronym_patterns:
        normalized = pattern.sub(replacement, normalized)

    # 7. English Court Honorifics
    honorific_patterns: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"\b(?:honourable\s+court|honorable\s+court|hon'ble\s+court)\b", re.IGNORECASE), "Hon'ble Court"),
        (re.compile(r"\blearned\s+counsel\b", re.IGNORECASE), "Learned Counsel"),
        (re.compile(r"\blearned\s+senior\s+counsel\b", re.IGNORECASE), "Learned Senior Counsel"),
        (re.compile(r"\blearned\s+advocate\b", re.IGNORECASE), "Learned Advocate"),
        (re.compile(r"\bpublic\s+prosecutor\b", re.IGNORECASE), "Public Prosecutor"),
        (re.compile(r"\bamicus\s+curiae\b", re.IGNORECASE), "Amicus Curiae"),
    ]
    for pattern, replacement in honorific_patterns:
        normalized = pattern.sub(replacement, normalized)

    # 8. Clean up spaces around punctuation
    normalized = re.sub(r"\s+([.,;:?!])", r"\1", normalized)
    normalized = re.sub(r"([.,;:?!])([A-Za-z0-9\u0900-\u097F])", r"\1 \2", normalized)

    return normalized.strip()
