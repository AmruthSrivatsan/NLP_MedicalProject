const uploadForm = document.getElementById("uploadForm");
const fileInput = document.getElementById("fileInput");
const output = document.getElementById("output");
const rawText = document.getElementById("rawText");
const reportImage = document.getElementById("reportImage");
const evalOutput = document.getElementById("evalOutput");
const progressSection = document.getElementById("progressSection");
const progressFill = document.getElementById("progressFill");
const hitlForm = document.getElementById("hitlForm");
const saveBtn = document.getElementById("saveBtn");

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

// Render editable form with read-only confidence
function renderEditableForm(data) {
  let html = "<h3>Patient Info</h3>";
  for (const [k, v] of Object.entries(data.patient)) {
    html += `<label>${k}: <input type="text" id="pat_${k}" value="${v}"></label><br/>`;
  }

  html += "<h3>Tests</h3><table><tr><th>Name</th><th>Value</th><th>Unit</th><th>Confidence</th></tr>";
  data.tests.forEach((t, i) => {
    const conf = (t.confidence !== undefined) ? t.confidence.toFixed(2) : "N/A";
    html += `<tr>
      <td><input type="text" id="test_${i}_name" value="${t.name}"></td>
      <td><input type="text" id="test_${i}_value" value="${t.value}"></td>
      <td><input type="text" id="test_${i}_unit" value="${t.unit}"></td>
      <td><input type="text" value="${conf}" readonly></td>
    </tr>`;
  });
  html += "</table>";
  hitlForm.innerHTML = html;
  saveBtn.disabled = false;
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

    currentFile = data.file.replace(/\.[^/.]+$/, "");
    rawText.textContent = data.raw_text || "⚠️ OCR text not available";
    output.textContent = "✅ Extracted:\n" + JSON.stringify(data.extracted, null, 2);

    if (data.image) {
      reportImage.src = `${API_URL}${data.image}`;
    }

    renderEditableForm(data.extracted);

  } catch (err) {
    stopProgress(interval);
    output.textContent = "❌ Network error: " + err;
  }
});

// Save Corrections
saveBtn.addEventListener("click", async () => {
  if (!currentFile) return;
  const corrected = { patient: {}, tests: [] };

  // Collect patient fields
  document.querySelectorAll("[id^='pat_']").forEach(inp => {
    corrected.patient[inp.id.replace("pat_", "")] = inp.value;
  });

  // Collect test fields (ignore confidence as it's read-only)
  let i = 0;
  while (document.getElementById(`test_${i}_name`)) {
    corrected.tests.push({
      name: document.getElementById(`test_${i}_name`).value,
      value: document.getElementById(`test_${i}_value`).value,
      unit: document.getElementById(`test_${i}_unit`).value
    });
    i++;
  }

  const res = await fetch(`${API_URL}/correct`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename: currentFile + ".json", corrected })
  });

  const result = await res.json();
  if (res.ok) {
    alert("✅ Correction saved: " + result.path);
  } else {
    alert("❌ Error: " + result.detail);
  }
});
