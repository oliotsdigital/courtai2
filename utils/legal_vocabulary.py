"""
Legal Vocabulary and Normalization for Courtroom Speech-to-Text.

Contains curated legal terms, statutes, codes, and procedural terminology
in English, Hindi, and Marathi, along with conservative normalization rules
to preserve fidelity while correcting common speech-to-text legal misinterpretations.
"""

import re
from typing import Dict, List, Optional, Tuple

# Curated list of Indian and Common-Law legal terminology
LEGAL_TERMS_EN: List[str] = [
    # Parties & Roles
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
    "Presiding Officer",
    "Magistrate",
    "Registrar",
    "Hon'ble Court",
    "Honourable Court",
    
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
    "Sur-rejoinder",
    "Exhibit",
    "Evidence",
    "Deposition",
    "Examination-in-chief",
    "Cross-examination",
    "Re-examination",
    
    # Proceedings & Dispositions
    "Hearing",
    "Proceedings",
    "Judgment",
    "Order",
    "Decree",
    "Injunction",
    "Interim Relief",
    "Stay Order",
    "Bail",
    "Anticipatory Bail",
    "Adjournment",
    "Quashment",
    "Cognizance",
    "Chargesheet",
    "First Information Report",
    "FIR",
    
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
    "Arbitration and Conciliation Act",
    "Specific Relief Act",
    "Limitation Act",
    "Evidence Act",
    
    # Courts & Jurisdictions
    "Supreme Court",
    "Supreme Court of India",
    "High Court",
    "District Court",
    "Sessions Court",
    "Metropolitan Magistrate",
    "Chief Judicial Magistrate",
    "Civil Judge",
    "Family Court",
    "Tribunal",
    "Commercial Court",
    
    # Common Statutory Provisions
    "Section 144",
    "Section 420",
    "Section 302",
    "Section 138",
    "Section 482",
    "Section 9",
    "Section 11",
    "Section 34",
    "Article 226",
    "Article 32",
    "Article 21",
    "Order 39 Rule 1",
    "Order 39 Rule 2",
    "Order 7 Rule 11",
]

# Curated Hindi and Marathi courtroom terms
LEGAL_TERMS_HI: List[str] = [
    "माननीय न्यायालय", "आवेदक", "प्रतिवादी", "याचिकाकर्ता", "अधिवक्ता", "विद्वान अधिवक्ता",
    "विद्वान वरिष्ठ अधिवक्ता", "लोक अभियोजक", "न्यायाधीश", "दंडाधिकारी", "शपथ पत्र",
    "लिखित बयान", "याचिका", "दलीलें", "साक्ष्य", "कार्यवाही", "जमानत", "अग्रिम जमानत",
    "अंतरिम राहत", "स्थगन", "आदेश", "निर्णय", "धारा 144", "धारा 420", "धारा 302",
    "धारा 138", "धारा 482", "सीपीसी", "सीआरपीसी", "आईपीसी", "बीएनएस", "बीएनएसएस", "बीएसए",
    "दीवानी प्रक्रिया संहिता", "दंड प्रक्रिया संहिता", "भारतीय संविधान", "उच्च न्यायालय", "सर्वोच्च न्यायालय"
]

LEGAL_TERMS_MR: List[str] = [
    "नामदार न्यायालय", "माननीय न्यायालय", "अर्जदार", "प्रतिवादी", "याचिकाकर्ता", "वकील",
    "विद्वान वकील", "विद्वान वरिष्ठ वकील", "सरकारी वकील", "न्यायाधीश", "दंडाधिकारी",
    "प्रतिज्ञापत्र", "लेखी जबाब", "अर्ज", "युक्तिवाद", "पुरावा", "कामकाज", "जामीन",
    "अगाऊ जामीन", "अंतरिम दिलासा", "तहकूब", "आदेश", "निकाल", "कलम 144", "कलम 420",
    "कलम 302", "कलम 138", "कलम 482", "सीपीसी", "सीआरपीसी", "आयपीसी", "बीएनएस", "बीएनएसएस", "बीएसए",
    "दिवाणी प्रक्रिया संहिता", "फौजदारी प्रक्रिया संहिता", "भारतीय संविधान", "उच्च न्यायालय", "सर्वोच्च न्यायालय"
]

LEGAL_TERMS: List[str] = LEGAL_TERMS_EN + LEGAL_TERMS_HI + LEGAL_TERMS_MR


def get_legal_prompt_context(language_code: Optional[str] = None) -> str:
    """
    Constructs a concise legal prompt to provide context to the OpenAI Audio API.
    OpenAI audio transcription models use the prompt parameter to prime
    correct spelling of domain-specific proper nouns, acronyms, and legal terminology
    in English, Hindi, or Marathi based on the selected language.
    """
    lang = (language_code or "").lower()
    
    if "hi" in lang:
        return (
            "न्यायालयीन कार्यवाही प्रतिलेख: माननीय न्यायालय, आवेदक, प्रतिवादी, याचिकाकर्ता, "
            "विद्वान अधिवक्ता, शपथ पत्र, दलीलें, साक्ष्य, कार्यवाही, धारा 144, धारा 420, धारा 302, "
            "धारा 138, धारा 482, सीपीसी, सीआरपीसी, आईपीसी, बीएनएस, बीएनएसएस, बीएसए, "
            "दीवानी प्रक्रिया संहिता, दंड प्रक्रिया संहिता, भारतीय संविधान, उच्च न्यायालय, "
            "सर्वोच्च न्यायालय, जिला न्यायालय, जमानत, अंतरिम राहत, आदेश, निर्णय।"
        )
    elif "mr" in lang:
        return (
            "न्यायालयीन कामकाज प्रतिलेख: नामदार न्यायालय, माननीय न्यायालय, अर्जदार, प्रतिवादी, "
            "याचिकाकर्ता, विद्वान वकील, प्रतिज्ञापत्र, युक्तिवाद, पुरावा, कामकाज, कलम 144, "
            "कलम 420, कलम 302, कलम 138, कलम 482, सीपीसी, सीआरपीसी, आयपीसी, बीएनएस, बीएनएसएस, "
            "बीएसए, दिवाणी प्रक्रिया संहिता, फौजदारी प्रक्रिया संहिता, भारतीय संविधान, "
            "उच्च न्यायालय, सर्वोच्च न्यायालय, जिल्हा न्यायालय, जामीन, अंतरिम दिलासा, आदेश, निकाल."
        )
    else:
        # Default English / Multilingual prompt
        key_terms = [
            "Applicant", "Respondent", "Petitioner", "Counsel", "Learned Counsel",
            "Hon'ble Court", "Affidavit", "Submissions", "Exhibit", "Proceedings",
            "Section 144", "Section 420", "Section 302", "Section 138", "Section 482",
            "CPC", "CrPC", "IPC", "BNS", "BNSS", "BSA",
            "Civil Procedure Code", "Criminal Procedure Code", "Constitution of India",
            "High Court", "Supreme Court", "District Court", "Magistrate", "Order 39",
        ]
        return "Courtroom proceedings transcript: " + ", ".join(key_terms) + "."


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
    Applies safe, conservative legal terminology normalization to transcript output.
    Does NOT blindly replace uncertain words. Standardizes statutory citations
    and legal acronyms in English, Hindi, and Marathi.
    
    Examples:
        - "Section one forty four" -> "Section 144"
        - "कलम १४४" / "कलम 144" -> "कलम 144"
        - "धारा १४४" / "धारा 144" -> "धारा 144"
        - "C P C" or "c.p.c." -> "CPC"
        - "honourable court" -> "Hon'ble Court"
        - "माननीय कोर्ट" -> "माननीय न्यायालय"
    """
    if not enabled or not text:
        return text

    normalized = text
    lang = (language_code or "").lower()

    # 1. Devanagari numerals normalization in statutory citations
    # e.g. "धारा १४४" -> "धारा 144", "कलम १४४" -> "कलम 144"
    normalized = re.sub(r"(धारा|कलम|सेक्शन)\s*([०-९]+)", _replace_dev_digits, normalized)

    # 2. Marathi & Hindi Statutory Sections
    if "mr" in lang:
        mr_patterns: List[Tuple[re.Pattern, str]] = [
            (re.compile(r"कलम\s*(?:एकशे\s*चव्वेचाळीस|एक\s*शे\s*चव्वेचाळीस)", re.IGNORECASE), "कलम 144"),
            (re.compile(r"कलम\s*(?:चारशे\s*वीस|चार\s*शे\s*वीस)", re.IGNORECASE), "कलम 420"),
            (re.compile(r"कलम\s*(?:तीनशे\s*दोन|तीन\s*शे\s*दोन)", re.IGNORECASE), "कलम 302"),
            (re.compile(r"कलम\s*(?:एकशे\s*अडतीस|एक\s*शे\s*अडतीस)", re.IGNORECASE), "कलम 138"),
            (re.compile(r"कलम\s*(?:चारशे\s*ब्याऐंशी|चार\s*शे\s*ब्याऐंशी)", re.IGNORECASE), "कलम 482"),
            (re.compile(r"(?:नामदार\s+कोर्ट|माननीय\s+कोर्ट)", re.IGNORECASE), "नामदार न्यायालय"),
            (re.compile(r"विद्वान\s+अधिवक्ता", re.IGNORECASE), "विद्वान वकील"),
        ]
        for pattern, replacement in mr_patterns:
            normalized = pattern.sub(replacement, normalized)

    elif "hi" in lang:
        hi_patterns: List[Tuple[re.Pattern, str]] = [
            (re.compile(r"धारा\s*(?:एक\s*सौ\s*चवालीस|एक\s*सौ\s*चौवालीस)", re.IGNORECASE), "धारा 144"),
            (re.compile(r"धारा\s*(?:चार\s*सौ\s*बीस)", re.IGNORECASE), "धारा 420"),
            (re.compile(r"धारा\s*(?:तीन\s*सौ\s*दो)", re.IGNORECASE), "धारा 302"),
            (re.compile(r"धारा\s*(?:एक\s*सौ\s*अड़तीस|एक\s*सौ\s*अडतीस)", re.IGNORECASE), "धारा 138"),
            (re.compile(r"धारा\s*(?:चार\s*सौ\s*बयासी)", re.IGNORECASE), "धारा 482"),
            (re.compile(r"(?:माननीय\s+कोर्ट|नामदार\s+कोर्ट)", re.IGNORECASE), "माननीय न्यायालय"),
        ]
        for pattern, replacement in hi_patterns:
            normalized = pattern.sub(replacement, normalized)

    # 3. Vernacular Legal Acronyms
    acronym_vernacular: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"(?:\b|^|\s)(?:सी\.?\s*पी\.?\s*सी\.?|सी\s+पी\s+सी|सीपीसी)(?=\b|\s|[.,;:?!]|$)", re.IGNORECASE), " सीपीसी"),
        (re.compile(r"(?:\b|^|\s)(?:सी\.?\s*आर\.?\s*पी\.?\s*सी\.?|सी\s*आर\s*पी\s*सी|सीआरपीसी)(?=\b|\s|[.,;:?!]|$)", re.IGNORECASE), " सीआरपीसी"),
        (re.compile(r"(?:\b|^|\s)(?:आई\.?\s*पी\.?\s*सी\.?|आय\.?\s*पी\.?\s*सी\.?|आईपीसी|आयपीसी)(?=\b|\s|[.,;:?!]|$)", re.IGNORECASE), " आईपीसी"),
        (re.compile(r"(?:\b|^|\s)(?:बी\.?\s*एन\.?\s*एस\.?|बी\s*एन\s*एस|बीएनएस)(?=\b|\s|[.,;:?!]|$)", re.IGNORECASE), " बीएनएस"),
        (re.compile(r"(?:\b|^|\s)(?:बी\.?\s*एन\.?\s*एस\.?\s*एस\.?|बीएनएसएस)(?=\b|\s|[.,;:?!]|$)", re.IGNORECASE), " बीएनएसएस"),
        (re.compile(r"(?:\b|^|\s)(?:बी\.?\s*एस\.?\s*ए\.?|बीएसए)(?=\b|\s|[.,;:?!]|$)", re.IGNORECASE), " बीएसए"),
    ]
    for pattern, replacement in acronym_vernacular:
        normalized = pattern.sub(replacement, normalized)

    # 4. English Statutory Sections - Common spoken forms
    section_patterns: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"\b(?:section|sec\.?)\s+one\s+forty[- ]?four\b", re.IGNORECASE), "Section 144"),
        (re.compile(r"\b(?:section|sec\.?)\s+four\s+twenty\b", re.IGNORECASE), "Section 420"),
        (re.compile(r"\b(?:section|sec\.?)\s+(?:three\s+zero\s+two|three\s+hundred\s+(?:and\s+)?two)\b", re.IGNORECASE), "Section 302"),
        (re.compile(r"\b(?:section|sec\.?)\s+one\s+thirty[- ]?eight\b", re.IGNORECASE), "Section 138"),
        (re.compile(r"\b(?:section|sec\.?)\s+four\s+eighty[- ]?two\b", re.IGNORECASE), "Section 482"),
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

    # 5. English Legal Acronyms
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

    # 6. Court honorifics in English
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

    return normalized.strip()
