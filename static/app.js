const uploadForm = document.getElementById("uploadForm");
const fileInput = document.getElementById("fileInput");
const output = document.getElementById("output");
const rawText = document.getElementById("rawText");
const reportImage = document.getElementById("reportImage");
const evalOutput = document.getElementById("evalOutput");
const progressSection = document.getElementById("progressSection");
const progressFill = document.getElementById("progressFill");

let currentFile = null;
const API_URL = "http://127.0.0.1:8000";

// Progress bar
function startProgress() {
  progressSection.style.display = "block";
  progressFill.style.width = "0%";

  let width = 0;
  const interval = setInterval(() => {
    if (width < 90) {
      width += Math.random() * 10;
      if (width > 90) width = 90;
      progressFill.style.width = width + "%";
    }
  }, 400);
  return interval;
}

function stopProgress(interval) {
  clearInterval(interval);
  progressFill.style.width = "100%";
  setTimeout(() => {
    progressSection.style.display = "none";
  }, 800);
}

// Upload
uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = fileInput.files[0];
  if (!file) return;

  const fd = new FormData();
  fd.append("file", file);

  const interval = startProgress();

  try {
    const res = await fetch(`${API_URL}/upload`, { method: "POST", body: fd });
    const data = await res.json();

    stopProgress(interval);

    if (!res.ok || !data.extracted) {
      output.textContent = "❌ Error: " + (data.detail || "Upload failed.");
      return;
    }

    currentFile = data.file;
    rawText.textContent = data.raw_text || "⚠️ OCR text not available";
    output.textContent = "✅ Extracted:\n" + JSON.stringify(data.extracted, null, 2);

    if (data.image) {
      reportImage.src = `${API_URL}${data.image}`;
    }
  } catch (err) {
    stopProgress(interval);
    output.textContent = "❌ Network error: " + err;
  }
});

// Evaluation
document.getElementById("evaluateBtn").addEventListener("click", async () => {
  const interval = startProgress();
  evalOutput.innerHTML = "Running evaluation...";

  try {
    const res = await fetch(`${API_URL}/evaluate`);
    const data = await res.json();

    stopProgress(interval);
    renderEvaluation(data);
  } catch (err) {
    stopProgress(interval);
    evalOutput.innerHTML = "❌ Error: " + err;
  }
});

function renderEvaluation(data) {
  evalOutput.innerHTML = "";
  for (const [file, result] of Object.entries(data)) {
    if (result.status === "missing") {
      evalOutput.innerHTML += `<p>⚠️ Missing results for ${file}</p>`;
      continue;
    }

    let html = `<h3>${file}</h3>`;
    html += `<p>Patient Accuracy: ${result.patient_accuracy}% | Test Accuracy: ${result.test_accuracy}%</p>`;

    // Patient results
    html += `<table class="eval-table"><tr><th>Patient Field</th><th>Match</th></tr>`;
    for (const [field, match] of Object.entries(result.patient_results)) {
      html += `<tr><td>${field}</td><td class="${match ? "pass" : "fail"}">${match ? "✅" : "❌"}</td></tr>`;
    }
    html += `</table>`;

    // Test results
    html += `<table class="eval-table"><tr><th>Test</th><th>Value</th><th>Unit</th></tr>`;
    for (const t of result.test_results) {
      html += `<tr>
        <td>${t.name}</td>
        <td class="${t.value_match ? "pass" : "fail"}">${t.value_match ? "✅" : "❌"}</td>
        <td class="${t.unit_match ? "pass" : "fail"}">${t.unit_match ? "✅" : "❌"}</td>
      </tr>`;
    }
    html += `</table><br/>`;

    evalOutput.innerHTML += html;
  }
}
