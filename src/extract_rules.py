import re
from typing import Dict, Any, List

BLACKLIST = {"confidential", "sample", "copy", "report", "hospital"}

def clean_text_for_parsing(text: str) -> str:
    words = text.split()
    counts = {}
    for w in words:
        wl = w.lower()
        counts[wl] = counts.get(wl, 0) + 1
    cleaned = []
    for w in words:
        wl = w.lower()
        if wl in BLACKLIST: continue
        if counts[wl] > 5: continue
        cleaned.append(w)
    return " ".join(cleaned)

def parse_patient_info(text: str) -> Dict[str, Any]:
    patient = {}
    try:
        m = re.search(r"(?:Patient\s*Name|Name)\s*[:\-]?\s*([A-Za-z .]+)", text, re.I)
        if m: patient["name"] = m.group(1).strip()
    except: pass

    m = re.search(r"Age\s*[:\-]?\s*(\d{1,3})", text, re.I)
    if m: patient["age"] = m.group(1)

    m = re.search(r"Sex\s*[:\-]?\s*(Male|Female|M|F)", text, re.I)
    if m: patient["sex"] = m.group(1)[0].upper()

    m = re.search(r"(Date|DOB)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})", text, re.I)
    if m:
        if m.group(1).lower() == "dob":
            patient["dob"] = m.group(2)
        else:
            patient["date"] = m.group(2)

    for key in ["name","age","sex","date","dob"]:
        patient.setdefault(key, "UNKNOWN")
    return patient

def parse_tests(text: str) -> List[Dict[str, Any]]:
    tests = []
    pattern = re.compile(r"([A-Za-z0-9 ()/\-]+)\s+([-+]?\d+(?:\.\d+)?)\s*([A-Za-z/%().-]+)", re.I)
    for m in pattern.finditer(text):
        label, value, unit = m.group(1).strip(), m.group(2), m.group(3)
        if len(label) < 3: continue
        if any(x in label.lower() for x in ["reference","range","method","ordered","report"]): continue
        tests.append({
            "name": label,
            "value": value,
            "unit": unit,
            # NEW: record exact matched tokens
            "matched_tokens": [label, value] + ([unit] if unit else [])
        })
    return tests

def extract_with_text(text: str) -> Dict[str, Any]:
    cleaned = clean_text_for_parsing(text)
    patient = parse_patient_info(cleaned)
    tests = parse_tests(cleaned)
    return {"patient": patient, "tests": tests}
