import re
from typing import Dict, Any, List
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from src.schemas import Report, Patient, TestResult
import warnings
import logging
import transformers

# -----------------------------
# Silence warnings/logging
# -----------------------------
warnings.filterwarnings("ignore")
transformers.logging.set_verbosity_error()
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)

# -----------------------------
# HuggingFace Model Setup
# -----------------------------
MODEL_NAME = "emilyalsentzer/Bio_ClinicalBERT"

ner_pipeline = None
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, local_files_only=False)
    model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME, local_files_only=False)
    ner_pipeline = pipeline("ner", model=model, tokenizer=tokenizer, grouped_entities=True)
except Exception:
    ner_pipeline = None

# -----------------------------
# Helpers
# -----------------------------
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
        if wl in BLACKLIST:
            continue
        if counts[wl] > 5:
            continue
        cleaned.append(w)
    return " ".join(cleaned)

def _confidence_from_tokens(tokens: List[Dict[str, Any]], words: List[str]) -> float:
    """Compute confidence by averaging OCR confidence of matched words"""
    if not tokens or not words:
        return 0.5
    confs = []
    for w in words:
        for t in tokens:
            if t["text"].lower() == w.lower():
                confs.append(t.get("confidence", 0.5))
                break
    return round(sum(confs) / len(confs), 3) if confs else 0.6

# -----------------------------
# Patient Info Extraction
# -----------------------------
def parse_patient_info(text: str, tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
    patient = {}
    confs = {}

    try:
        m = re.search(r"(?:Patient\s*Name|Name)\s*[:\-]?\s*([A-Za-z .]+)", text, re.I)
        if m:
            val = m.group(1).strip()
            patient["name"] = val
            confs["name"] = _confidence_from_tokens(tokens, val.split())
    except:
        pass

    m = re.search(r"Age\s*[:\-]?\s*(\d{1,3})", text, re.I)
    if m:
        patient["age"] = m.group(1)
        confs["age"] = _confidence_from_tokens(tokens, [m.group(1)])

    m = re.search(r"Sex\s*[:\-]?\s*(Male|Female|M|F)", text, re.I)
    if m:
        val = m.group(1)[0].upper()
        patient["sex"] = val
        confs["sex"] = _confidence_from_tokens(tokens, [val])

    m = re.search(r"(Date|DOB)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})", text, re.I)
    if m:
        val = m.group(2)
        if m.group(1).lower() == "dob":
            patient["dob"] = val
            confs["dob"] = _confidence_from_tokens(tokens, [val])
        else:
            patient["date"] = val
            confs["date"] = _confidence_from_tokens(tokens, [val])

    # Ensure defaults
    for key in ["name", "age", "sex", "date", "dob", "visit_id", "id"]:
        patient.setdefault(key, "UNKNOWN")

    return patient, confs

# -----------------------------
# Test Extraction (Regex + Model)
# -----------------------------
def parse_tests(text: str, tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tests = []

    # Regex baseline
    pattern = re.compile(r"([A-Za-z0-9 ()/\-]+)\s+([-+]?\d+(?:\.\d+)?)\s*([A-Za-z/%().-]+)", re.I)
    for m in pattern.finditer(text):
        label, value, unit = m.group(1).strip(), m.group(2), m.group(3)
        if len(label) < 3:
            continue
        if any(x in label.lower() for x in ["reference", "range", "method", "ordered", "report"]):
            continue
        unit = unit.replace("dI", "dl").replace("ldl", "dl").replace("mgldl", "mg/dl")

        words = label.split() + [value] + ([unit] if unit else [])
        conf = _confidence_from_tokens(tokens, words)

        tests.append({
            "name": label,
            "value": value,
            "unit": unit,
            "matched_tokens": words,
            "confidence": conf
        })

    # HuggingFace NER enhancement
    if ner_pipeline:
        try:
            entities = ner_pipeline(text)
            for ent in entities:
                word = ent.get("word", "").strip()
                if not word:
                    continue
                score = float(ent.get("score", 0.8))
                if re.fullmatch(r"[-+]?\d+(\.\d+)?", word):
                    tests.append({
                        "name": "UNKNOWN",
                        "value": word,
                        "unit": "",
                        "matched_tokens": [word],
                        "confidence": score
                    })
                else:
                    tests.append({
                        "name": word,
                        "value": "",
                        "unit": "",
                        "matched_tokens": [word],
                        "confidence": score
                    })
        except Exception:
            pass

    return tests

# -----------------------------
# Main Extraction Function
# -----------------------------
def extract_with_text(text: str, tokens: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    tokens = tokens or []
    cleaned = clean_text_for_parsing(text)

    patient, patient_confs = parse_patient_info(cleaned, tokens)
    tests = parse_tests(cleaned, tokens)

    report = Report(
        patient=Patient(**patient),
        tests=[TestResult(**{k: v for k, v in t.items() if k in ["name", "value", "unit", "matched_tokens"]}) for t in tests]
    )

    output = report.dict()
    # Add confidence to tests
    for i, t in enumerate(tests):
        output["tests"][i]["confidence"] = t.get("confidence", 0.6)
    # Add confidence to patient fields
    output["patient_confidence"] = patient_confs

    return output
