import os, json, joblib
from sklearn.linear_model import LogisticRegression

TRAIN_DIR = "data/training_data"
MODEL_PATH = "data/model.joblib"

def prepare_features(tokens, meta, corrected):
    """Very simple token-level features with labels."""
    X, y = [], []
    for t in tokens:
        text = t["text"]
        feats = [
            len(text),
            text.isdigit(),
            text.isupper(),
            t["bbox"][0] / meta["width"],
            t["bbox"][1] / meta["height"],
        ]
        label = "O"
        if corrected.get("patient", {}).get("name") and text in corrected["patient"]["name"].split():
            label = "B-NAME"
        elif corrected.get("patient", {}).get("age") and text == str(corrected["patient"]["age"]):
            label = "B-AGE"
        for row in corrected.get("tests", []):
            if text in row["name"].split():
                label = "B-TEST"
            elif text == str(row["value"]):
                label = "B-VALUE"
            elif text == row["unit"]:
                label = "B-UNIT"
        X.append(feats)
        y.append(label)
    return X, y

def train_model():
    X, y = [], []
    for fname in os.listdir(TRAIN_DIR):
        if not fname.endswith(".json"): continue
        with open(os.path.join(TRAIN_DIR, fname), "r", encoding="utf-8") as f:
            sample = json.load(f)
        tokens = sample.get("tokens", [])
        meta = sample.get("meta", {"width": 1000, "height": 1000})
        corrected = sample.get("corrected", {})
        Xi, yi = prepare_features(tokens, meta, corrected)
        X.extend(Xi); y.extend(yi)

    if not X:
        print("No training data found")
        return None

    clf = LogisticRegression(max_iter=200)
    clf.fit(X, y)
    os.makedirs("data", exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    print(f"✅ Model saved at {MODEL_PATH}")
    return clf
