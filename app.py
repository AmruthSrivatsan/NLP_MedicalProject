import os, shutil, cv2, json
from typing import List
from fastapi import FastAPI, UploadFile, HTTPException, Body, File
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.ocr import ocr_image
from src.extract_rules import extract_with_text
from src.storage import save_confirmed, save_correction, load_correction
from evaluate import evaluate_all

app = FastAPI(title="Lab Report Digitization API")

# Serve frontend and data folders
app.mount("/static", StaticFiles(directory="static", html=True), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

UPLOAD_DIR = "data/samples"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def annotate_image(image_path, tokens, parsed):
    """Highlight only exact matched tokens from parsing."""
    img = cv2.imread(image_path)
    if img is None:
        raise RuntimeError(f"Failed to load image: {image_path}")

    h, w = img.shape[:2]
    highlight_tokens = []

    # Patient fields
    if parsed.get("patient"):
        for v in parsed["patient"].values():
            if v and v != "UNKNOWN":
                highlight_tokens.append(str(v))

    # Test tokens
    for t in parsed.get("tests", []):
        if "matched_tokens" in t:
            highlight_tokens.extend(t["matched_tokens"])

    # Draw rectangles
    for t in tokens:
        if any(ht.lower() == t["text"].lower() for ht in highlight_tokens):
            x0, y0, x1, y1 = t["bbox"]
            x0, y0, x1, y1 = int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)
            cv2.rectangle(img, (x0, y0), (x1, y1), (0, 255, 0), 2)

    out_path = f"data/debug/annotated_{os.path.basename(image_path)}"
    os.makedirs("data/debug", exist_ok=True)
    cv2.imwrite(out_path, img)
    return out_path

@app.post("/upload")
async def upload(files: List[UploadFile] = File(...)):
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")

        saved_pages = []
        combined_texts = []

        for upload_file in files:
            file_path = os.path.join(UPLOAD_DIR, upload_file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)

            try:
                tokens, full_text = ocr_image(file_path)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"OCR failed for {upload_file.filename}: {str(e)}")

            saved_pages.append({
                "filename": upload_file.filename,
                "path": file_path,
                "tokens": tokens,
            })
            combined_texts.append(full_text)

        combined_text = "\n\n".join(text for text in combined_texts if text)

        # Extract structured data on combined text
        parsed = extract_with_text(combined_text)

        # Determine document identifier
        base_name = os.path.splitext(files[0].filename)[0]
        if len(files) > 1:
            base_name = f"{base_name}_bundle"
        bundle_filename = f"{base_name}.json"

        # If a correction exists for this bundle, prefer that payload
        corrected = load_correction(bundle_filename)
        if corrected:
            parsed = corrected

        # Annotate each page
        annotated_images = []
        for page in saved_pages:
            try:
                annotated_path = annotate_image(page["path"], page["tokens"], parsed)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Annotation failed for {page['filename']}: {str(e)}")

            annotated_images.append({
                "filename": page["filename"],
                "image": f"/data/debug/{os.path.basename(annotated_path)}"
            })

        # Save structured JSON for the bundle
        save_confirmed(bundle_filename, parsed)

        return {
            "status": "ok",
            "file": bundle_filename,
            "files": [page["filename"] for page in saved_pages],
            "raw_text": combined_text,
            "extracted": parsed,
            "images": annotated_images
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/evaluate")
async def evaluate():
    try:
        return evaluate_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@app.post("/correct")
async def correct(filename: str = Body(...), corrected: dict = Body(...)):
    """
    Save corrected JSON from frontend HITL form
    """
    try:
        path = save_correction(filename, corrected)
        return {"status": "ok", "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Correction failed: {str(e)}")
