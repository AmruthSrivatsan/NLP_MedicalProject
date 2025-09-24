import os, json
from glob import glob

EXPECTED_DIR = "data/samples"
RESULTS_DIR = "data/final_reports"

def safe_load(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def compare_dicts(expected, actual):
    results = {}
    for key, exp_val in expected.items():
        act_val = actual.get(key, "MISSING")
        results[key] = (exp_val == act_val)
    return results

def compare_tests(expected_tests, actual_tests):
    results = []
    total = len(expected_tests)

    for exp in expected_tests:
        found = False
        for act in actual_tests:
            if exp["name"].lower() == act["name"].lower():
                same_val = str(exp.get("value")) == str(act.get("value"))
                same_unit = str(exp.get("unit")) == str(act.get("unit"))
                results.append({
                    "name": exp["name"],
                    "value_match": same_val,
                    "unit_match": same_unit
                })
                found = True
                break
        if not found:
            results.append({
                "name": exp["name"],
                "value_match": False,
                "unit_match": False
            })

    score = sum(1 for r in results if r["value_match"] and r["unit_match"]) / max(1,total)
    return results, score

def evaluate_all():
    summary = {}
    expected_files = glob(os.path.join(EXPECTED_DIR, "*_expected.json"))

    for exp_file in expected_files:
        base = os.path.basename(exp_file).replace("_expected.json","")
        act_file = os.path.join(RESULTS_DIR, f"{base}.json")

        expected = safe_load(exp_file)
        actual = safe_load(act_file)

        if not expected or not actual:
            summary[base] = {"status":"missing"}
            continue

        # Patient info
        patient_results = compare_dicts(expected.get("patient", {}), actual.get("patient", {}))
        patient_score = sum(patient_results.values())/max(1,len(patient_results))

        # Tests
        test_results, test_score = compare_tests(expected.get("tests", []), actual.get("tests", []))

        summary[base] = {
            "patient_accuracy": round(patient_score*100,2),
            "test_accuracy": round(test_score*100,2),
            "patient_results": patient_results,
            "test_results": test_results
        }

    return summary
