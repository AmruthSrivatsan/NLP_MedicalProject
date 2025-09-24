import os, json, re
from doctr.io import DocumentFile
from doctr.models import ocr_predictor

model = ocr_predictor(pretrained=True)

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
    if not word:
        return ""
    if re.fullmatch(r"[#▯Xx\-]+", word):
        return "[REDACTED]"
    return word

def ocr_image(image_path: str):
    doc = DocumentFile.from_images(image_path)
    result = model(doc).export()

    tokens, lines = [], []
    for page in result["pages"]:
        for block in page.get("blocks", []):
            for line in block.get("lines", []):
                line_text = []
                for word in line.get("words", []):
                    txt = clean_word(word.get("value", "").strip())
                    if not txt:
                        continue
                    x0,y0,x1,y1 = _flatten_geometry(word.get("geometry"))
                    tokens.append({
                        "text": txt,
                        "bbox": (x0, y0, x1, y1),
                        "confidence": float(word.get("confidence", 0.0)),
                    })
                    line_text.append(txt)
                if line_text:
                    lines.append(" ".join(line_text))

    full_text = "\n".join(lines)

    # Save debug artifacts
    os.makedirs("data/samples/tokens", exist_ok=True)
    with open(os.path.join("data/samples/tokens", f"tokens_{os.path.basename(image_path)}.json"), "w") as f:
        json.dump(tokens, f, indent=2)
    with open(os.path.join(DEBUG_DIR, f"text_{os.path.basename(image_path)}.txt"), "w") as f:
        f.write(full_text)

    return tokens, full_text
