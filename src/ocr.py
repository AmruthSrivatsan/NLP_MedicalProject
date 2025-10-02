import os, sys, types, json, re, torch

# 🚫 Block Doctr’s unused HTML/WeasyPrint imports
fake_html = types.ModuleType("doctr.io.html")
fake_html.read_html = lambda *a, **k: None  # stub to satisfy doctr import
sys.modules["weasyprint"] = types.ModuleType("weasyprint")
sys.modules["doctr.io.html"] = fake_html

from doctr.io import DocumentFile
from doctr.models import ocr_predictor

# Pick GPU if available, else CPU
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🔹 Using OCR device: {device}")

# Initialize model safely
try:
    model = ocr_predictor(pretrained=True).to(device)
except Exception:
    device = "cpu"
    model = ocr_predictor(pretrained=True).to("cpu")

DEBUG_DIR = "data/debug"
os.makedirs(DEBUG_DIR, exist_ok=True)


def _flatten_geometry(geom):
    try:
        if isinstance(geom, (list, tuple)) and len(geom) == 2:
            (x0, y0), (x1, y1) = geom
            return float(x0), float(y0), float(x1), float(y1)
        if isinstance(geom, (list, tuple)) and len(geom) == 4:
            return tuple(map(float, geom))
    except Exception:
        pass
    return (0.0, 0.0, 1.0, 1.0)


def clean_word(word: str) -> str:
    """Clean OCR artifacts & normalize units."""
    if not word:
        return ""
    if re.fullmatch(r"[#▯Xx\-]+", word):
        return "[REDACTED]"
    # Normalize common OCR mistakes
    word = word.replace("dI", "dl").replace("mgldl", "mg/dl").replace("Mgldl", "mg/dl")
    word = word.replace("ldl", "dl")  # when 'l' is duplicated by OCR
    return word


def _median(values):
    if not values:
        return 0.02  # reasonable default in normalized coords
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return (s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0)


def ocr_image(image_path: str):
    """Run OCR and return tokens + full text in strict L→R, T→B order with adaptive line grouping."""
    try:
        doc = DocumentFile.from_images(image_path)
        result = model(doc).export()
    except Exception as e:
        raise RuntimeError(f"OCR processing failed: {e}")

    # Collect ALL words across the page (ignore Doctr's block/line structure)
    words_all = []  # (y_center, x0, txt, bbox, conf, height)
    for page in result.get("pages", []):
        for block in page.get("blocks", []):
            for line in block.get("lines", []):
                for word in line.get("words", []):
                    txt = clean_word(word.get("value", "").strip())
                    if not txt:
                        continue
                    x0, y0, x1, y1 = _flatten_geometry(word.get("geometry"))
                    h = max(1e-6, (y1 - y0))
                    y_center = (y0 + y1) / 2.0
                    words_all.append((y_center, x0, txt, (x0, y0, x1, y1), float(word.get("confidence", 0.0)), h))

    # Sort globally: top-to-bottom, then left-to-right
    words_all.sort(key=lambda w: (w[0], w[1]))

    # Adaptive line threshold based on median word height
    heights = [w[5] for w in words_all]
    h_med = _median(heights)
    # Threshold: ~60% of median text height, but not less than 0.008
    line_thresh = max(0.6 * h_med, 0.008)

    # Group into lines using adaptive threshold on y_center
    grouped_lines = []  # list[list[word_tuple]]
    current_line = []
    current_y = None

    for w in words_all:
        y_center = w[0]
        if current_y is None or abs(y_center - current_y) <= line_thresh:
            current_line.append(w)
            # Update running average for stability
            if current_y is None:
                current_y = y_center
            else:
                current_y = (current_y * (len(current_line) - 1) + y_center) / len(current_line)
        else:
            grouped_lines.append(current_line)
            current_line = [w]
            current_y = y_center

    if current_line:
        grouped_lines.append(current_line)

    # Within each line, sort by x0 and build tokens/text
    tokens = []
    lines = []
    for line_words in grouped_lines:
        line_words.sort(key=lambda w: w[1])  # by x0
        line_text_parts = []
        for (_, x0, txt, bbox, conf, _) in line_words:
            tokens.append({"text": txt, "bbox": bbox, "confidence": conf})
            line_text_parts.append(txt)
        lines.append(" ".join(line_text_parts))

    full_text = "\n".join(lines)

    # Save debug artifacts
    os.makedirs("data/samples/tokens", exist_ok=True)
    with open(os.path.join("data/samples/tokens", f"tokens_{os.path.basename(image_path)}.json"), "w") as f:
        json.dump(tokens, f, indent=2)
    with open(os.path.join(DEBUG_DIR, f"text_{os.path.basename(image_path)}.txt"), "w") as f:
        f.write(full_text)

    return tokens, full_text
