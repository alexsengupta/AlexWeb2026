const statusEl = document.getElementById("status");
const runButton = document.getElementById("runButton");
const downloadButton = document.getElementById("downloadButton");
const fitSummaryEl = document.getElementById("fitSummary");
const yearsInput = document.getElementById("yearsInput");
const fileInput = document.getElementById("fileInput");
const tableHead = document.querySelector("#dataTable thead");
const tableBody = document.querySelector("#dataTable tbody");
const viewRawButton = document.getElementById("viewRawButton");
const equationsSection = document.getElementById("equationsSection");
const equationsContent = document.getElementById("equationsContent");
const equationsToggle = document.getElementById("equationsToggle");
const plotsSection = document.getElementById("plotsSection");
const downloadSection = document.getElementById("downloadSection");
const helpButton = document.getElementById("helpButton");
const helpModal = document.getElementById("helpModal");
const closeHelpButton = document.getElementById("closeHelpButton");
const modalBackdrop = document.querySelector("#helpModal .modal-backdrop");

const H_MEAN = 3;
const H_LOGVAR = 2;
const P_ANNUAL = 365.2425;
const DAYS_PER_YEAR = 365;

let pyodideReadyPromise = null;
let pyodideInstance = null;
let sampleCsvText = null;
let selectedFileText = null;
let downloadUrl = null;
let currentMetadata = null;

function setGeneratedSectionsVisible(visible) {
  if (equationsSection) {
    equationsSection.hidden = !visible;
    if (!visible) {
      equationsSection.classList.remove("collapsed");
      if (equationsToggle) {
        equationsToggle.setAttribute("aria-expanded", "false");
      }
    }
  }
  if (plotsSection) {
    plotsSection.hidden = !visible;
    if (!visible) {
      if (typeof Plotly !== "undefined") {
        Plotly.purge("plot-first3");
        Plotly.purge("plot-variance");
        Plotly.purge("plot-acf");
      }
    }
  }
  if (downloadSection) {
    downloadSection.hidden = !visible;
  }
}

setGeneratedSectionsVisible(false);

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

async function initPyodide() {
  setStatus("Initialising Pyodide…");
  pyodideInstance = await loadPyodide({
    indexURL: "https://cdn.jsdelivr.net/pyodide/v0.24.1/full/",
  });
  setStatus("Loading Python packages…");
  await pyodideInstance.loadPackage(["numpy", "pandas", "statsmodels"]);

  const pythonSource = await fetch("synthetic_sst.py").then((resp) => {
    if (!resp.ok) {
      throw new Error(`Unable to load synthetic_sst.py (${resp.status})`);
    }
    return resp.text();
  });
  pyodideInstance.FS.writeFile("synthetic_sst.py", pythonSource, { encoding: "utf8" });
  await pyodideInstance.runPythonAsync("import importlib\nimport synthetic_sst\nimportlib.reload(synthetic_sst)\n");
  setStatus("Pyodide ready. Sample dataset loading…");
  try {
    sampleCsvText = await fetch("../sst_daily_1D_simple.csv").then((resp) =>
      resp.ok ? resp.text() : Promise.reject(resp.status)
    );
    setStatus("Sample dataset loaded. Ready to generate synthetic SST.");
    renderDataPreview(sampleCsvText);
    setRawDataButtonState(sampleCsvText);
  } catch (err) {
    console.warn("Sample dataset unavailable:", err);
    setStatus("Pyodide ready. Upload a CSV to get started.");
  }
}

function readUploadedFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error || new Error("File read failed"));
    reader.readAsText(file);
  });
}

async function ensurePyodide() {
  if (!pyodideReadyPromise) {
    pyodideReadyPromise = initPyodide().catch((err) => {
      setStatus(`Pyodide failed to initialise: ${err.message}`, true);
      throw err;
    });
  }
  return pyodideReadyPromise;
}

async function nextFrame() {
  return new Promise((resolve) => requestAnimationFrame(resolve));
}

async function handleRun() {
  await ensurePyodide();

  const years = Number.parseInt(yearsInput.value, 10);
  if (!Number.isFinite(years) || years < 1) {
    setStatus("Years must be a positive integer.", true);
    return;
  }

  let csvText = selectedFileText || sampleCsvText;
  if (!csvText) {
    setStatus("No CSV data available. Please upload a file.", true);
    return;
  }

  setStatus("Generating synthetic SST…");
  runButton.disabled = true;
  downloadButton.disabled = true;

  try {
    const seedValue = generateSeed();
    const globals = pyodideInstance.globals;
    globals.set("csv_text", csvText);
    globals.set("years_syn", years);
    globals.set("seed_value", seedValue);
    const resultJsonStr = await pyodideInstance.runPythonAsync(`
from synthetic_sst import generate_synthetic_sst_json
generate_synthetic_sst_json(csv_text, years_syn=years_syn, seed=seed_value)
`);
    const result = JSON.parse(resultJsonStr);
    setGeneratedSectionsVisible(true);
    await nextFrame();
    renderDiagnostics(result.diagnostics);
    presentMetadata(result.metadata);
    prepareDownload(result.synthetic_csv, result.metadata);
    updateEquations(result.metadata);
    setStatus("Synthetic SST generated.");
  } catch (err) {
    console.error(err);
    setStatus(`Failed to generate synthetic SST: ${err.message}`, true);
  } finally {
    runButton.disabled = false;
  }
}

function renderDiagnostics(diagnostics) {
  renderTimeseries(diagnostics.timeseries);
  renderVariance(diagnostics.variance);
  renderAcf(diagnostics.acf);
}

function renderTimeseries(series) {
  if (!series || !series.dates) {
    Plotly.purge("plot-first3");
    return;
  }
  const totalPoints = series.dates.length;
  const initialEndIndex = Math.min(totalPoints - 1, 3 * DAYS_PER_YEAR);
  const layout = {
    margin: { t: 20, r: 10, l: 50, b: 50 },
    yaxis: { title: "SSTA (°C)" },
    xaxis: {
      title: "Date",
      rangeslider: { visible: true },
      range: totalPoints > 0 ? [series.dates[0], series.dates[initialEndIndex]] : undefined,
    },
    dragmode: "pan",
    legend: { orientation: "h" },
    hovermode: "x unified",
  };
  const traces = [
    {
      x: series.dates,
      y: series.observed,
      type: "scatter",
      mode: "lines",
      name: "Observed",
      line: { color: "#1f77b4", width: 2 },
    },
    {
      x: series.dates,
      y: series.synthetic,
      type: "scatter",
      mode: "lines",
      name: "Synthetic",
      line: { color: "#ff7f0e", width: 2 },
    },
  ];
  Plotly.newPlot("plot-first3", traces, layout, {
    responsive: true,
    displaylogo: false,
    displayModeBar: true,
    modeBarButtonsToRemove: ["select2d", "lasso2d"],
    scrollZoom: true,
  });
}

function renderVariance(variance) {
  if (!variance) {
    Plotly.purge("plot-variance");
    return;
  }
  const traces = [
    {
      x: variance.doy,
      y: variance.observed,
      mode: "lines",
      name: "Observed",
      line: { color: "#1f77b4", width: 2 },
    },
    {
      x: variance.doy,
      y: variance.synthetic,
      mode: "lines",
      name: "Synthetic",
      line: { color: "#ff7f0e", width: 2 },
    },
  ];
  const layout = {
    margin: { t: 20, r: 10, l: 50, b: 45 },
    xaxis: { title: "Day of year" },
    yaxis: { title: "Variance (°C²)" },
    legend: { orientation: "h" },
  };
  Plotly.newPlot("plot-variance", traces, layout, { responsive: true, displayModeBar: false, displaylogo: false });
}

function renderAcf(acf) {
  if (!acf) {
    Plotly.purge("plot-acf");
    return;
  }
  const traces = [
    {
      x: acf.lags,
      y: acf.observed,
      type: "scatter",
      mode: "lines+markers",
      name: "Observed",
    },
    {
      x: acf.lags,
      y: acf.synthetic,
      type: "scatter",
      mode: "lines+markers",
      name: "Synthetic",
      line: { dash: "dash" },
    },
  ];
  const layout = {
    margin: { t: 20, r: 10, l: 50, b: 45 },
    xaxis: { title: "Lag (days)" },
    yaxis: { title: "ACF", range: [-1, 1] },
    legend: { orientation: "h" },
  };
  Plotly.newPlot("plot-acf", traces, layout, { responsive: true, displayModeBar: false, displaylogo: false });
}

function presentMetadata(metadata) {
  if (!metadata) {
    fitSummaryEl.textContent = "";
    currentMetadata = null;
    return;
  }
  const { phi, theta, rho, fraction, years_syn: years, seed } = metadata;
  currentMetadata = metadata;
  fitSummaryEl.textContent = `ARMA fit: phi=${phi}, theta=${theta}; slow memory rho=${rho}, fraction=${fraction}. Generated ${years} years (seed ${seed}).`;
}

function prepareDownload(csvText, metadata) {
  if (downloadUrl) {
    URL.revokeObjectURL(downloadUrl);
    downloadUrl = null;
  }
  if (!csvText) {
    downloadButton.disabled = true;
    return;
  }
  const blob = new Blob([csvText], { type: "text/csv" });
  downloadUrl = URL.createObjectURL(blob);
  const years = metadata?.years_syn ?? "synthetic";
  downloadButton.disabled = false;
  downloadButton.onclick = () => {
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = `synthetic_sst_${years}yr.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
}

fileInput.addEventListener("change", async (event) => {
  selectedFileText = null;
  const file = event.target.files?.[0];
  if (!file) {
    setStatus("File input cleared. Using sample dataset if available.");
    renderDataPreview(sampleCsvText);
    setRawDataButtonState(sampleCsvText);
    return;
  }
  try {
    selectedFileText = await readUploadedFile(file);
    setStatus(`Loaded ${file.name}. Ready to generate synthetic SST.`);
    renderDataPreview(selectedFileText);
    setRawDataButtonState(selectedFileText);
  } catch (err) {
    console.error(err);
    setStatus(`Failed to read file: ${err.message}`, true);
  }
});

runButton.addEventListener("click", handleRun);

ensurePyodide();

if (equationsToggle) {
  equationsToggle.addEventListener("click", () => {
    const collapsed = equationsSection.classList.toggle("collapsed");
    equationsToggle.setAttribute("aria-expanded", String(!collapsed));
  });
}

helpButton.addEventListener("click", () => {
  helpModal.hidden = false;
});

closeHelpButton.addEventListener("click", () => {
  helpModal.hidden = true;
});

modalBackdrop.addEventListener("click", () => {
  helpModal.hidden = true;
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !helpModal.hidden) {
    helpModal.hidden = true;
  }
});

function renderDataPreview(csvText) {
  if (!csvText) {
    tableHead.innerHTML = "";
    tableBody.innerHTML = `<tr><td colspan="1">No data available</td></tr>`;
    return;
  }
  const rows = parseCsv(csvText, 200);
  if (!rows.length) {
    tableHead.innerHTML = "";
    tableBody.innerHTML = `<tr><td colspan="1">No rows parsed</td></tr>`;
    return;
  }
  const headers = rows[0];
  tableHead.innerHTML = `<tr>${headers.map((h) => `<th>${escapeHtml(h)}</th>`).join("")}</tr>`;
  const maxRows = Math.min(rows.length - 1, 50);
  const bodyHtml = [];
  for (let i = 1; i <= maxRows; i += 1) {
    const row = rows[i] ?? [];
    const cells = headers.map((_, idx) => `<td>${escapeHtml(row[idx] ?? "")}</td>`).join("");
    bodyHtml.push(`<tr>${cells}</tr>`);
  }
  const colSpan = Math.max(headers.length, 1);
  tableBody.innerHTML = bodyHtml.join("") || `<tr><td colspan="${colSpan}">No data rows</td></tr>`;
}

function parseCsv(text, maxRows = 200) {
  const lines = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
  const rows = [];
  for (const line of lines) {
    if (line.trim() === "") continue;
    rows.push(line.split(","));
    if (rows.length >= maxRows) break;
  }
  return rows;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function setRawDataButtonState(csvText) {
  if (csvText) {
    viewRawButton.disabled = false;
    viewRawButton.onclick = () => showRawTimeseries(csvText);
  } else {
    viewRawButton.disabled = true;
    viewRawButton.onclick = null;
  }
}

function showRawTimeseries(csvText) {
  const rows = parseCsv(csvText, Number.POSITIVE_INFINITY);
  if (rows.length <= 1) {
    alert("No data rows to display.");
    return;
  }
  const headers = rows[0];
  const timeIndex = headers.findIndex((h) => h.trim().toLowerCase() === "time");
  const sstIndex = headers.findIndex((h) => h.trim().toLowerCase() === "sst");
  if (timeIndex === -1 || sstIndex === -1) {
    alert("CSV must contain 'time' and 'sst' columns.");
    return;
  }
  const dataRows = rows.slice(1);
  const xValues = [];
  const yValues = [];
  for (const row of dataRows) {
    const t = row[timeIndex];
    const val = parseFloat(row[sstIndex]);
    if (t && Number.isFinite(val)) {
      xValues.push(t);
      yValues.push(val);
    }
  }
  if (!xValues.length) {
    alert("No valid time/SST pairs to plot.");
    return;
  }
  const plotHtml = `
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <div id="raw-plot" style="width: 100%; height: 100%;"></div>
    <script>
      const trace = { x: ${JSON.stringify(xValues)}, y: ${JSON.stringify(yValues)}, mode: "lines", name: "SST" };
      const layout = { margin: { t: 40, r: 40, b: 60, l: 60 }, xaxis: { title: "Date" }, yaxis: { title: "SST (°C)" } };
      Plotly.newPlot("raw-plot", [trace], layout, { displaylogo: false });
    </script>
  `;
  const rawWindow = window.open("", "_blank", "width=1000,height=600");
  if (!rawWindow) {
    alert("Pop-up blocked. Allow pop-ups for this site to view the plot.");
    return;
  }
  rawWindow.document.write(`<!DOCTYPE html><html><head><title>Raw SST Timeseries</title></head><body>${plotHtml}</body></html>`);
  rawWindow.document.close();
}

function updateEquations(metadata) {
  if (!metadata) {
    equationsSection.hidden = true;
    equationsContent.innerHTML = "";
    equationsSection.classList.remove("collapsed");
    if (equationsToggle) {
      equationsToggle.setAttribute("aria-expanded", "false");
    }
    return;
  }
  const { phi, theta, rho, fraction, years_syn: years, seed } = metadata;
  const wasHidden = equationsSection.hidden;
  equationsSection.hidden = false;
  if (wasHidden) {
    equationsSection.classList.remove("collapsed");
    if (equationsToggle) {
      equationsToggle.setAttribute("aria-expanded", "true");
    }
  } else if (equationsToggle) {
    const collapsed = equationsSection.classList.contains("collapsed");
    equationsToggle.setAttribute("aria-expanded", String(!collapsed));
  }
  equationsContent.innerHTML = `
    <p>The synthetic series is generated by combining a harmonic seasonal mean, a seasonal variance envelope, and a mixed ARMA/AR process calibrated to the observed record.</p>
    <div class="math-block">\\[
      m(t) = \\beta_0 + \\sum_{k=1}^{${H_MEAN}} \\left[ \\beta_{c,k} \\cos\\left(\\tfrac{2\\pi k t}{${P_ANNUAL}}\\right) + \\beta_{s,k} \\sin\\left(\\tfrac{2\\pi k t}{${P_ANNUAL}}\\right) \\right]
    \\]</div>
    <p>The observed anomalies remove the seasonal mean and linear trend:</p>
    <div class="math-block">\\[
      x_t = T_t - m(t) - (a_0 + a_1 (t - \\bar{t}))
    \\]</div>
    <p>A seasonal variance profile rescales anomalies</p>
    <div class="math-block">\\[
      \\log \\sigma^2(d) = \\gamma_0 + \\sum_{k=1}^{${H_LOGVAR}} \\left[ \\gamma_{c,k} \\cos\\left(\\tfrac{2\\pi k d}{${P_ANNUAL}}\\right) + \\gamma_{s,k} \\sin\\left(\\tfrac{2\\pi k d}{${P_ANNUAL}}\\right) \\right], \\qquad z_t = \\frac{x_t}{\\sigma(d_t)}
    \\]</div>
    <p>The fast component follows an ARMA(1,1) fitted to \\(z_t\\)</p>
    <div class="math-block">\\[
      y_t^{\\mathrm{fast}} = ${phi}\\, y_{t-1}^{\\mathrm{fast}} + e_t + ${theta}\\, e_{t-1}, \\qquad e_t \\sim \\mathcal{N}(0, \\sigma_e^2)
    \\]</div>
    <p>The slow component is an AR(1)</p>
    <div class="math-block">\\[
      y_t^{\\mathrm{slow}} = ${rho}\\, y_{t-1}^{\\mathrm{slow}} + \\eta_t, \\qquad \\eta_t \\sim \\mathcal{N}(0, 1)
    \\]</div>
    <p>Mixing the two components with weight \\(f = ${fraction}\\) gives</p>
    <div class="math-block">\\[
      y_t = \\sqrt{1-${fraction}}\\, y_t^{\\mathrm{fast}} + \\sqrt{${fraction}}\\, y_t^{\\mathrm{slow}}
    \\]</div>
    <p>Synthetic anomalies and SST rebuild the seasonal structure</p>
    <div class="math-block">\\[
      x_t^{\\mathrm{syn}} = \\sigma(d_t)\\, y_t, \\qquad T_t^{\\mathrm{syn}} = m(t) + x_t^{\\mathrm{syn}}
    \\]</div>
    <p><strong>Simulation settings:</strong> years = ${years}, seed = ${seed}.</p>
  `;
  if (window.MathJax?.typesetPromise) {
    window.MathJax.typesetPromise([equationsContent]).catch((err) => console.error("MathJax render error", err));
  }
}

function generateSeed() {
  if (window.crypto?.getRandomValues) {
    const array = new Uint32Array(1);
    window.crypto.getRandomValues(array);
    // Keep seed within 32-bit signed range for numpy
    return array[0] % 2147483647 || 123456789;
  }
  // Fallback to Math.random
  return Math.floor(Math.random() * 2147483646) + 1;
}
