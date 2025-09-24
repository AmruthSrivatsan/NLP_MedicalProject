import os, joblib
from src.model_training import prepare_features, MODEL_PATH

def run_model_inference(tokens, rule_json):
    """Combine rule-based + ML model predictions."""
    patient = rule_json["patient"]
    tests = rule_json["tests"]

    if os.path.exists(MODEL_PATH):
        clf = joblib.load(MODEL_PATH)
        meta = {"width": 1000, "height": 1000}  # fallback
        X, _ = prepare_features(tokens, meta, {"patient": patient, "tests": tests})
        if X:
            y_pred = clf.predict(X)
            if "B-NAME" in y_pred:
                patient["name"] = " ".join([t["text"] for t, lab in zip(tokens, y_pred) if lab=="B-NAME"])
            if "B-AGE" in y_pred:
                ages = [t["text"] for t, lab in zip(tokens, y_pred) if lab=="B-AGE"]
                if ages: patient["age"] = int(ages[0])
    return {"patient": patient, "tests": tests}
