Lab Report Digitization and Structured Data Extraction
CS429 – Natural Language Processing
Amruth Srivatsan 2023A7PS0026P

## 1. Project Title

Lab Report Digitization and Structured Data Extraction

---

## 2. Aim

To develop a system that can automatically extract and digitize patient details and test results from laboratory reports into a structured format (JSON).

---

## 3. Objectives

* Accept lab reports as PDF, JPG, or PNG.
* Perform OCR to extract text and bounding boxes.
* Apply rule-based and machine learning methods to extract patient details and test results.
* Provide a Human-in-the-Loop (HITL) interface for corrections.
* Continuously improve extraction through supervised learning on corrected reports.
* Expose a REST API and provide a simple frontend UI for demonstration.

## 4. Implementation Details

### Module 1: File Input & Preprocessing

* **File:** `src/preprocessing.py`
* **Tools:** OpenCV, pdf2image
* Functions: `preprocess_input`, `deskew`, `preprocess_image`
* Converts PDFs to images, deskews, denoises, applies OTSU thresholding.

### Module 2: OCR & Tokenization

* **File:** `src/ocr.py`
* **Tools:** Doctr OCR with GPU/CPU fallback
* Extracts tokens with bounding boxes and confidence.
* Saves token JSONs (`data/samples/tokens/`) and raw text debug files.

### Module 3: Rule-Based Extraction

* **File:** `src/extract_rules.py`
* Regex rules for patient fields: Name, Age, Sex, Date, DOB.
* Regex and heuristics for test results (Test Name, Value, Unit).
* HuggingFace BioClinicalBERT integrated for semantic fallback.

### Module 4: Human-in-the-Loop (HITL) UI

* **Files:** `static/index.html`, `static/app.js`, `static/style.css`
* Editable patient/test form with confidence values (read-only).
* Corrections saved in `data/corrections/` via API `/correct`.

### Module 5: Supervised Learning Model

* **Files:** `src/model_training.py`, `retrain.py`
* Logistic Regression model for token classification (Name, Age, Test, Value, Unit).
* `retrain.py` converts corrections into training samples and trains model (`data/model.joblib`).

### Module 6: Inference (Hybrid Rules + ML)

* **File:** `src/inference.py`
* Combines rule-based parsing with ML model predictions.
* Falls back to rules if ML model not available.

### Module 7: API & Demo

* **File:** `app.py`
* REST API endpoints:

  * `/upload`: Upload file, run OCR, extract structured data, annotate, return JSON.
  * `/correct`: Save corrected report.
  * `/evaluate`: Run evaluation.
* Serves frontend from `/static/index.html`.

### Module 8: Storage & Continuous Learning

* **File:** `src/storage.py`
* Saves confirmed reports in `data/final_reports/` and corrections in `data/corrections/`.
* Supports periodic retraining with `retrain.py`.

### Module 9: Evaluation

* **File:** `evaluate.py`
* Compares system outputs with expected JSONs (`data/samples/*_expected.json`).
* Calculates patient accuracy and test accuracy for both regex and hybrid extraction.

### Module 10: Documentation

* **File:** `README.md`
* Setup instructions:

  ```bash
  pip install -r requirements.txt
  python -m uvicorn app:app --reload
  ```
* Demo available at: [http://127.0.0.1:8000](http://127.0.0.1:8000)


## 5. Features Implemented

* PDF to image preprocessing
* OCR with GPU support (Doctr)
* Rule-based extraction
* Human-in-the-loop correction UI
* Supervised machine learning with Logistic Regression
* Hybrid inference (rules + ML)
* JSON structured output
* Annotated report visualization
* Confidence scoring for test results
* Evaluation pipeline
## 6. Sample Output

Extracted JSONs are stored in `data/final_reports/`.
Debug annotated images are stored in `data/debug/`.

Example:

```json
{
  "patient": {
    "name": "John Doe",
    "age": 42,
    "sex": "M",
    "dob": "UNKNOWN",
    "visit_id": "UNKNOWN",
    "date": "08/09/2018"
  },
  "tests": [
    {"name": "Hemoglobin", "value": "13.5", "unit": "g/dL", "confidence": 0.92},
    {"name": "WBC", "value": "7600", "unit": "/µL", "confidence": 0.90}
  ]
}

## 7. Evaluation Summary

* Regex extractor accuracy (average): ~70–80%
* Hybrid extractor accuracy (average): ~85–90%
* Main errors caused by noisy scans and unit variations.

## 9. Conclusion

The system digitizes lab reports into structured JSON format using rule-based extraction, machine learning enhancement, and a correction interface. It achieves good accuracy on sample reports and can continuously improve through retraining.