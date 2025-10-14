const uploadForm = document.getElementById("uploadForm");
const fileInput = document.getElementById("fileInput");
const output = document.getElementById("output");
const rawText = document.getElementById("rawText");
const reportImageContainer = document.getElementById("reportImageContainer");
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
function createPatientRow(key = "", value = "") {
  const row = document.createElement("tr");
  row.classList.add("patient-row");

  const fieldCell = document.createElement("td");
  const fieldInput = document.createElement("input");
  fieldInput.type = "text";
  fieldInput.className = "patient-key";
  fieldInput.value = key;
  fieldCell.appendChild(fieldInput);

  const valueCell = document.createElement("td");
  const valueInput = document.createElement("input");
  valueInput.type = "text";
  valueInput.className = "patient-value";
  valueInput.value = value;
  valueCell.appendChild(valueInput);

  const actionCell = document.createElement("td");
  const deleteBtn = document.createElement("button");
  deleteBtn.type = "button";
  deleteBtn.className = "delete-patient-row";
  deleteBtn.textContent = "Delete";
  actionCell.appendChild(deleteBtn);

  row.appendChild(fieldCell);
  row.appendChild(valueCell);
  row.appendChild(actionCell);

  return row;
}

function setupPatientRowHandlers() {
  const tableBody = document.getElementById("patientTableBody");
  const addBtn = document.getElementById("addPatientRow");
  const table = document.getElementById("patientTable");

  if (!tableBody || !addBtn || !table) return;

  addBtn.onclick = () => {
    tableBody.appendChild(createPatientRow());
  };

  table.onclick = (event) => {
    const target = event.target;
    if (target && target.classList.contains("delete-patient-row")) {
      const row = target.closest("tr");
      if (row) {
        row.remove();
      }
    }
  };
}

function renderEditableForm(data) {
  let html = `
    <h3>Patient Info</h3>
    <table id="patientTable">
      <thead>
        <tr><th>Field</th><th>Value</th><th></th></tr>
      </thead>
      <tbody id="patientTableBody"></tbody>
    </table>
    <button type="button" id="addPatientRow">+ Add Row</button>
    <h3>Tests</h3>
    <table>
      <tr><th>Name</th><th>Value</th><th>Unit</th><th>Confidence</th></tr>`;
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

  const patientBody = document.getElementById("patientTableBody");
  const patientEntries = data.patient ? Object.entries(data.patient) : [];
  patientEntries.forEach(([k, v]) => {
    patientBody.appendChild(createPatientRow(k, v));
  });

  setupPatientRowHandlers();
  saveBtn.disabled = false;
}

// Upload
uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const files = Array.from(fileInput.files || []);
  if (!files.length) return;

  const fd = new FormData();
  files.forEach(file => fd.append("files", file));

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

    if (Array.isArray(data.images) && data.images.length) {
      reportImageContainer.innerHTML = "";
      data.images.forEach((img, index) => {
        const figure = document.createElement("figure");
        const image = document.createElement("img");
        image.src = `${API_URL}${img.image}`;
        image.alt = `Annotated page ${index + 1}`;
        const caption = document.createElement("figcaption");
        const label = img.filename ? `Page ${index + 1}: ${img.filename}` : `Page ${index + 1}`;
        caption.textContent = label;
        figure.appendChild(image);
        figure.appendChild(caption);
        reportImageContainer.appendChild(figure);
      });
    } else {
      reportImageContainer.innerHTML = "<p>No annotated image available.</p>";
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
  const patientRows = document.querySelectorAll("#patientTableBody tr");
  patientRows.forEach(row => {
    const key = row.querySelector(".patient-key")?.value.trim();
    const value = row.querySelector(".patient-value")?.value ?? "";
    if (key) {
      corrected.patient[key] = value;
    }
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
