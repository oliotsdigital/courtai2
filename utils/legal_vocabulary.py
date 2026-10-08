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
    "Principal Sessions Judge",
    "Sessions Judge",
    "Trial Court",
    "Fast Track Court",
    "Judicial Magistrate First Class",
    "JMFC",
    "Chief Judicial Magistrate",
    "CJM",
    "High Court",
    "Supreme Court",
    "Coram",
    
    # Parties, Accused & Witnesses (Court Transcript Conventions)
    "Applicant",
    "Respondent",
    "Petitioner",
    "Appellant",
    "Appellants",
    "Plaintiff",
    "Defendant",
    "Accused",
    "Accused No. 1",
    "Accused Nos.",
    "Appellant No. 1",
    "Complainant",
    "Witness",
    "Prosecution Witness",
    "Defence Witness",
    "Court Witness",
    "PW-1", "PW-2", "PW-3", "PW-4", "PW-5", "PW-6", "PW-7", "PW-8", "PW-9", "PW-10",
    "DW-1", "DW-2", "CW-1", "CW-2",
    "Injured Witness",
    "Ocular Witness",
    "Hostile Witness",
    "Declared Hostile",
    "Interested Witness",
    "Independent Witness",
    "Panchas",
    "Panch Witness",
    "Panch Panchanama",
    "Counsel",
    "Advocate",
    "Learned Counsel",
    "Learned Senior Counsel",
    "Public Prosecutor",
    "Amicus Curiae",
    "S/o.", "D/o.", "W/o.", "alias",
    
    # Exhibits, Material Objects & Forensic Evidence
    "Exhibit",
    "Ex.P1", "Ex.P2", "Ex.P3", "Ex.P4", "Ex.P5", "Ex.P6", "Ex.P7", "Ex.P8", "Ex.P9", "Ex.P10",
    "Ex.P11", "Ex.P12", "Ex.P13", "Ex.P14", "Ex.P15", "Ex.P16", "Ex.P17", "Ex.P18", "Ex.P19", "Ex.P20", "Ex.P21",
    "Ex.D1", "Ex.D2",
    "Material Object",
    "MO-1", "MO-2", "MO-3", "MO-4", "MO-5", "MO-6", "MO-7", "MO-8", "MO-9", "MO-10",
    "MO-11", "MO-12", "MO-13", "MO-14", "MO-15", "MO-16", "MO-17",
    "Inquest Mahazar",
    "Seizure Mahazar",
    "Scene of Offence",
    "Panchanama",
    "FSL Report",
    "Forensic Science Laboratory",
    "Post-Mortem Report",
    "P.M. Report",
    "Ante-Mortem Injuries",
    "Post-Mortem Examination",
    "Wound Certificate",
    "Injury Certificate",
    "Injury Report",
    "MLC Register",
    
    # Examination & Trial Procedure
    "Examination-in-Chief",
    "Cross-Examination",
    "Re-Examination",
    "First Information Report",
    "FIR",
    "F.I.R.",
    "Crime No.",
    "Criminal Appeal No.",
    "Sessions Case No.",
    "Charge-Sheet",
    "Committal Order",
    "Order of Acquittal",
    "Order of Conviction",
    "Impugned Judgment",
    "Assailed",
    "Appreciation of Evidence",
    "Re-Appreciation of Evidence",
    "Chain of Circumstances",
    "Presumption of Innocence",
    "Two-Views Theory",
    "Leave granted.",
    
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
    "Evidence",
    "Deposition",
    
    # Orders & Sentencing
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
    "Rigorous Imprisonment",
    "RI",
    "Simple Imprisonment",
    "SI",
    "Life Imprisonment",
    "Period Already Undergone",
    "In Default of Payment",
    
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
    "Section 307",
    "Section 326",
    "Section 341",
    "Section 504",
    "Section 506B",
    "Section 147",
    "Section 148",
    "Section 149",
    "Section 34",
    "Section 138",
    "Section 482",
    "Section 439",
    "Section 235",
    "Section 313",
    "Section 161",
    "Section 164",
    "Article 226",
    "Article 32",
    "Article 21",
    "Order 39 Rule 1",
    "Order 39 Rule 2",
    
    # Latin Maxims & Legal Phrases
    "Mens Rea",
    "Actus Reus",
    "Ante Mortem",
    "Inter Se",
    "Per Contra",
    "Prima Facie",
    "Suo Motu",
    "Res Judicata",
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
    Constructs a concise Indian English legal prompt for the OpenAI Audio API.
    CRITICAL STENOGRAPHY INSTRUCTION:
    - Transcribe verbatim as spoken in Indian English courtroom standard.
    - Accurately capture Indian legal citations, sections, witness notations, and exhibits.
    - Never translate.
    """
    return (
        "Official judicial stenographer verbatim record of Judge's oral statement, court dictation, and judgment in Indian English: "
        "Hon'ble Court, Judge, Rajesh Bindal, J., S.C. Sharma, J., Principal Sessions Judge, JMFC, CJM, "
        "PW-1 to PW-10, DW-1, CW-1, A1 to A8, Accused No. 1, S/o., D/o., W/o., alias, "
        "Ex.P1 to Ex.P21, Ex.D1, MO-1 to MO-17, Inquest Mahazar, Seizure Mahazar, Panchanama, "
        "FSL report, post-mortem report, wound certificate, ante-mortem injuries, cross-examination, Examination-in-Chief, "
        "Section 302 read with Section 34, Sections 147, 148, 149, 302, 307, 326, 341, 504, 506B IPC, "
        "Section 235 CrPC, RI 1 month, RI 6 months, RI 5 years, fine of ₹ 1,500/-, period already undergone, "
        "mens rea, actus reus, per contra, inter se, prima facie, FIR, Crime No., Criminal Appeal No., Sessions Case No. "
        "Transcribe verbatim as spoken without translation. Output strictly in Indian English."
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
    Formats witness designations (PW-1), exhibits (Ex.P1), material objects (MO-1),
    parentage (S/o.), statutes (Section 302 read with Section 34), sentences (RI 5 years),
    and Latin maxims verbatim as shown in High Court and Supreme Court transcripts.
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

    # 5. Witness & Accused Formatting (Court Transcript Standards from english_data_1.txt & english_data_2.txt)
    witness_patterns: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"\b(?:P\.?\s*W\.?|Prosecution\s+Witness)\s*[- ]?(\d+)\b", re.IGNORECASE), r"PW-\1"),
        (re.compile(r"\b(?:D\.?\s*W\.?|Defence\s+Witness)\s*[- ]?(\d+)\b", re.IGNORECASE), r"DW-\1"),
        (re.compile(r"\b(?:C\.?\s*W\.?|Court\s+Witness)\s*[- ]?(\d+)\b", re.IGNORECASE), r"CW-\1"),
        (re.compile(r"\bA\s*[-]?\s*(\d+)\s+to\s+A\s*[-]?\s*(\d+)\b", re.IGNORECASE), r"A\1 to A\2"),
        (re.compile(r"\b(?:accused|accused\s+no\.?)\s*(\d+)\b", re.IGNORECASE), r"Accused No. \1"),
        (re.compile(r"\b(?:appellant|appellant\s+no\.?)\s*(\d+)\b", re.IGNORECASE), r"Appellant No. \1"),
        (re.compile(r"\b(?:son\s+of|s\s*/\s*o\.?)\s+", re.IGNORECASE), "S/o. "),
        (re.compile(r"\b(?:daughter\s+of|d\s*/\s*o\.?)\s+", re.IGNORECASE), "D/o. "),
        (re.compile(r"\b(?:wife\s+of|w\s*/\s*o\.?)\s+", re.IGNORECASE), "W/o. "),
        (re.compile(r"\b(?:a\.?\s*k\.?\s*a\.?|also\s+known\s+as)\b", re.IGNORECASE), "alias"),
    ]
    for pattern, replacement in witness_patterns:
        normalized = pattern.sub(replacement, normalized)

    # 6. Exhibits & Material Objects (e.g. Ex.P1 to Ex.P21, Ex.D1, MO-1 to MO-17)
    exhibit_patterns: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"\b(?:Ex(?:hibit|\.)?\s*P\s*[- ]?(\d+))\b", re.IGNORECASE), r"Ex.P\1"),
        (re.compile(r"\b(?:Ex(?:hibit|\.)?\s*D\s*[- ]?(\d+))\b", re.IGNORECASE), r"Ex.D\1"),
        (re.compile(r"\b(?:M\.?O\.?|Material\s+Object)\s*[- ]?(\d+)\b", re.IGNORECASE), r"MO-\1"),
        (re.compile(r"\b(?:M\.?O\.?s|Material\s+Objects)\s*(\d+)\s*(?:to|-)\s*(\d+)\b", re.IGNORECASE), r"MOs \1 to \2"),
    ]
    for pattern, replacement in exhibit_patterns:
        normalized = pattern.sub(replacement, normalized)

    # 7. Forensics, Medical Evidence & Procedural Stages
    forensic_patterns: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"\bpost\s*mortem\b", re.IGNORECASE), "post-mortem"),
        (re.compile(r"\bante\s*mortem\b", re.IGNORECASE), "ante-mortem"),
        (re.compile(r"\bcross\s*examination\b", re.IGNORECASE), "cross-examination"),
        (re.compile(r"\bexamination\s+in\s+chief\b", re.IGNORECASE), "Examination-in-Chief"),
        (re.compile(r"\bre\s*examination\b", re.IGNORECASE), "re-examination"),
        (re.compile(r"\bcharge\s*sheet\b", re.IGNORECASE), "charge-sheet"),
        (re.compile(r"\bwound\s+certificate\b", re.IGNORECASE), "wound certificate"),
        (re.compile(r"\binquest\s+mahazar\b", re.IGNORECASE), "inquest mahazar"),
        (re.compile(r"\bseizure\s+mahazar\b", re.IGNORECASE), "seizure mahazar"),
        (re.compile(r"\bF\.?S\.?L\.?\b", re.IGNORECASE), "FSL"),
        (re.compile(r"\bJ\.?M\.?F\.?C\.?\b", re.IGNORECASE), "JMFC"),
        (re.compile(r"\bC\.?J\.?M\.?\b", re.IGNORECASE), "CJM"),
        (re.compile(r"\b(?:P\.?M\.?|PM)\s*report\b", re.IGNORECASE), "post-mortem report"),
        (re.compile(r"\bM\.?L\.?C\.?\b", re.IGNORECASE), "MLC"),
    ]
    for pattern, replacement in forensic_patterns:
        normalized = pattern.sub(replacement, normalized)

    # 8. English Statutory Sections & Provisions
    section_patterns: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"\b(?:section|sec\.?)\s+one\s+forty[- ]?four\b", re.IGNORECASE), "Section 144"),
        (re.compile(r"\b(?:section|sec\.?)\s+four\s+twenty\b", re.IGNORECASE), "Section 420"),
        (re.compile(r"\b(?:section|sec\.?)\s+(?:three\s+zero\s+two|three\s+hundred\s+(?:and\s+)?two)\b", re.IGNORECASE), "Section 302"),
        (re.compile(r"\b(?:section|sec\.?)\s+one\s+thirty[- ]?eight\b", re.IGNORECASE), "Section 138"),
        (re.compile(r"\b(?:section|sec\.?)\s+four\s+eighty[- ]?two\b", re.IGNORECASE), "Section 482"),
        (re.compile(r"\b(?:section|sec\.?)\s+four\s+thirty[- ]?nine\b", re.IGNORECASE), "Section 439"),
        (re.compile(r"\bread\s+with\s+sec(?:tion)?\.?\s*(\d+[A-Z]?)\b", re.IGNORECASE), r"read with Section \1"),
        (re.compile(r"\bu\s*/\s*s\s*(\d+[A-Z]?)\b", re.IGNORECASE), r"U/s \1"),
        (re.compile(r"\bunder\s+sec(?:tion)?\.?\s+(\d+[A-Z]?)\b", re.IGNORECASE), r"under Section \1"),
        (re.compile(r"\bunder\s+sec(?:tions)?\.?\s+(\d+[A-Z]?(?:[,\s]+(?:\d+[A-Z]?|and))+)\b", re.IGNORECASE), r"under Sections \1"),
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

    # 9. Case Numbers & Headings (e.g. Criminal Appeal No. 1363/2005, Crime No. 78/97)
    case_patterns: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"\b(?:crl\.?\s*a(?:ppl|ppeal)?\.?|criminal\s+appeal)\s*(?:no\.?)?\s*(\d+)\s*/\s*(\d+)\b", re.IGNORECASE), r"Criminal Appeal No. \1/\2"),
        (re.compile(r"\bsessions\s+case\s*(?:no\.?)?\s*(\d+)\s*/\s*(\d+)\b", re.IGNORECASE), r"Sessions Case No. \1/\2"),
        (re.compile(r"\bcrime\s*(?:no\.?)?\s*(\d+)\s*/\s*(\d+)\b", re.IGNORECASE), r"Crime No. \1/\2"),
        (re.compile(r"\bleave\s+granted(?:\.|\b)", re.IGNORECASE), "Leave granted."),
    ]
    for pattern, replacement in case_patterns:
        normalized = pattern.sub(replacement, normalized)

    # 10. Sentencing, Imprisonment & Fines (e.g. RI 5 years, fine of ₹ 1,500/-)
    sentencing_patterns: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"\b(?:R\.?\s*I\.?|rigorous\s+imprisonment)\s*(\d+)\s*(month|months|year|years|day|days)\b", re.IGNORECASE), r"RI \1 \2"),
        (re.compile(r"\b(?:S\.?\s*I\.?|simple\s+imprisonment)\s*(\d+)\s*(month|months|year|years|day|days)\b", re.IGNORECASE), r"SI \1 \2"),
        (re.compile(r"\bfine\s+of\s+(?:Rs\.?|INR|'|`)\s*(\d+(?:,\d+)*(?:\/-)?)\b", re.IGNORECASE), r"fine of ₹ \1"),
        (re.compile(r"\bto\s+further\s+undergo\s+R\.?\s*I\.?\b", re.IGNORECASE), "to further undergo RI"),
        (re.compile(r"\bperiod\s+already\s+undergone\b", re.IGNORECASE), "period already undergone"),
    ]
    for pattern, replacement in sentencing_patterns:
        normalized = pattern.sub(replacement, normalized)

    # 11. Latin Maxims & Doctrines
    latin_patterns: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"\bmens\s+rea\b", re.IGNORECASE), "mens rea"),
        (re.compile(r"\bactus\s+reus\b", re.IGNORECASE), "actus reus"),
        (re.compile(r"\bper\s+contra\b", re.IGNORECASE), "Per contra"),
        (re.compile(r"\binter\s+se\b", re.IGNORECASE), "inter se"),
        (re.compile(r"\bprima\s+facie\b", re.IGNORECASE), "prima facie"),
        (re.compile(r"\bsuo\s+motu\b", re.IGNORECASE), "suo motu"),
        (re.compile(r"\bres\s+judicata\b", re.IGNORECASE), "res judicata"),
    ]
    for pattern, replacement in latin_patterns:
        normalized = pattern.sub(replacement, normalized)

    # 12. English Legal Acronyms
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

    # 13. English Court Honorifics
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

    # 13b. Standardize spoken 'comma' command into ','
    normalized = re.sub(
        r"(?<![A-Za-z0-9\u0900-\u097F])(?:comma|koma|alpa\s+viram|alpaviram|swalpa\s+viram|swalpaviram|कॉमा|स्वल्पविराम|अल्पविराम)(?![A-Za-z0-9\u0900-\u097F])",
        ",",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(r",\s*,+", ",", normalized)

    # 14. Clean up spaces around punctuation
    normalized = re.sub(r"\s+([.,;:?!])", r"\1", normalized)
    normalized = re.sub(r"([.,;:?!])([A-Za-z0-9\u0900-\u097F])", r"\1 \2", normalized)

    # 15. Re-tighten legal abbreviations & citations after punctuation formatting
    normalized = re.sub(r"\bEx\.\s*([PD]\d+)\b", r"Ex.\1", normalized)
    normalized = re.sub(r"\bS\s*/\s*o\.\s*", "S/o. ", normalized)
    normalized = re.sub(r"\bD\s*/\s*o\.\s*", "D/o. ", normalized)
    normalized = re.sub(r"\bW\s*/\s*o\.\s*", "W/o. ", normalized)
    normalized = re.sub(r"\b([A-Z])\.\s+([A-Z])\.\s+([A-Z])\.", r"\1.\2.\3.", normalized)
    normalized = re.sub(r"\b([A-Z])\.\s+([A-Z])\.", r"\1.\2.", normalized)
    normalized = re.sub(r"\.{2,}", ".", normalized)
    normalized = re.sub(r",\s*J\s*\.", ", J.", normalized)
    normalized = re.sub(r"₹\s*(\d)", r"₹ \1", normalized)

    # If the output consists purely of whitespace/breaks, preserve intentional break symbol
    if re.fullmatch(r"[\r\n\t ]*", normalized):
        if "\n\n" in normalized:
            return "\n\n"
        elif "\n" in normalized:
            return "\n"
        elif " " in normalized:
            return " "
        return ""

    # Strip horizontal spaces/tabs, preserving leading and trailing newlines
    return normalized.strip(" \t")


