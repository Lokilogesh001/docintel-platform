// Intelligent Document Intelligence Platform - Frontend Application
document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const filePreview = document.getElementById("file-preview");
  const fileNameDisplay = document.getElementById("file-name-display");
  const btnRemoveFile = document.getElementById("btn-remove-file");
  const uploadForm = document.getElementById("upload-form");
  const btnProcess = document.getElementById("btn-process");
  const spinner = document.getElementById("spinner");
  const btnText = document.getElementById("btn-text");
  const alertContainer = document.getElementById("alert-container");

  // Health Elements
  const healthBadge = document.getElementById("health-badge");
  const healthText = document.getElementById("health-text");
  const llmBadge = document.getElementById("llm-badge");
  const llmText = document.getElementById("llm-text");

  // Stats bar elements
  const statTotal = document.getElementById("stat-total");
  const statPass = document.getElementById("stat-pass");
  const statFail = document.getElementById("stat-fail");
  const statNa = document.getElementById("stat-na");
  const statRejected = document.getElementById("stat-rejected");

  // Dashboard Elements
  const docTableBody = document.getElementById("doc-table-body");
  const btnRefresh = document.getElementById("btn-refresh-docs");
  const searchInput = document.getElementById("search-docs");

  // Result Viewer Elements
  const resultViewer = document.getElementById("result-viewer");
  const emptyViewer = document.getElementById("empty-viewer");
  const resDocName = document.getElementById("res-doc-name");
  const resDocType = document.getElementById("res-doc-type");
  const resDocStatus = document.getElementById("res-doc-status");
  const metaConfidence = document.getElementById("meta-confidence");
  const metaPages = document.getElementById("meta-pages");
  const metaTime = document.getElementById("meta-time");
  const metaOcr = document.getElementById("meta-ocr");

  // Tab Containers
  const tabValidation = document.getElementById("tab-validation");
  const tabFields = document.getElementById("tab-fields");
  const tabTables = document.getElementById("tab-tables");
  const tabRawJson = document.getElementById("tab-raw-json");
  const rawJsonPre = document.getElementById("raw-json-pre");
  const btnCopyJson = document.getElementById("btn-copy-json");

  let selectedFile = null;
  let currentResultData = null;

  // Initialize
  checkHealth();
  loadDocuments();

  // -------------------------------------------------------------
  // 1. SYSTEM HEALTH
  // -------------------------------------------------------------
  async function checkHealth() {
    try {
      const res = await fetch("/api/v1/health");
      if (res.ok) {
        const data = await res.json();
        healthText.textContent = `API Ready (${data.environment})`;
        // Show LLM badge if configured
        if (data.llm_configured) {
          llmBadge.style.display = "flex";
          llmText.textContent = "GPT-4o-mini Active";
        } else {
          llmBadge.style.display = "flex";
          llmText.textContent = "NLP Fallback Mode";
          llmBadge.style.background = "rgba(100,116,139,0.12)";
          llmBadge.style.borderColor = "rgba(100,116,139,0.3)";
          llmBadge.style.color = "#94a3b8";
          document.querySelector(".llm-dot").style.background = "#64748b";
          document.querySelector(".llm-dot").style.boxShadow = "none";
          document.querySelector(".llm-dot").style.animation = "none";
        }
      } else {
        healthText.textContent = "API Degraded";
        healthBadge.style.color = "var(--status-fail-text)";
      }
    } catch (e) {
      healthText.textContent = "API Offline";
      healthBadge.style.color = "var(--status-fail-text)";
    }
  }

  // -------------------------------------------------------------
  // 2. FILE SELECTION & DRAG-AND-DROP
  // -------------------------------------------------------------
  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  function handleFileSelected(file) {
    const validExtensions = [".pdf", ".jpg", ".jpeg", ".png"];
    const ext = "." + file.name.split(".").pop().toLowerCase();

    if (!validExtensions.includes(ext)) {
      showAlert("UNSUPPORTED_FILE_TYPE", `File type '${ext}' is not supported. Only PDF, JPG, and PNG are allowed.`);
      return;
    }

    if (file.size > 15 * 1024 * 1024) {
      showAlert("FILE_TOO_LARGE", "File size exceeds 15MB limit.");
      return;
    }

    selectedFile = file;
    fileNameDisplay.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    dropzone.style.display = "none";
    filePreview.style.display = "flex";
    btnProcess.disabled = false;
    clearAlert();
  }

  btnRemoveFile.addEventListener("click", (e) => {
    e.stopPropagation();
    selectedFile = null;
    fileInput.value = "";
    filePreview.style.display = "none";
    dropzone.style.display = "block";
    btnProcess.disabled = true;
  });

  // -------------------------------------------------------------
  // 3. DOCUMENT PROCESS SUBMISSION
  // -------------------------------------------------------------
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    const docType = document.querySelector('input[name="doc_type"]:checked').value;

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("document_type", docType);

    setProcessingState(true);
    clearAlert();

    try {
      const response = await fetch("/api/v1/documents/process", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        const err = data.error || { code: "SERVER_ERROR", message: "Failed to process document." };
        showAlert(err.code, err.message);
        setProcessingState(false);
        return;
      }

      // Success
      renderDocumentResult(data);
      loadDocuments();
      setProcessingState(false);
    } catch (err) {
      showAlert("NETWORK_ERROR", `Failed to communicate with API: ${err.message}`);
      setProcessingState(false);
    }
  });

  function setProcessingState(isProcessing) {
    if (isProcessing) {
      btnProcess.disabled = true;
      spinner.style.display = "inline-block";
      btnText.textContent = "Processing Pipeline Active...";
    } else {
      btnProcess.disabled = !selectedFile;
      spinner.style.display = "none";
      btnText.textContent = "Extract & Validate Document";
    }
  }

  function showAlert(code, message) {
    alertContainer.innerHTML = `
      <div class="alert alert-danger" id="error-alert">
        <span>⚠️ <strong>[${escapeHtml(code)}]</strong> ${escapeHtml(message)}</span>
      </div>
    `;
  }

  function clearAlert() {
    alertContainer.innerHTML = "";
  }

  // -------------------------------------------------------------
  // 4. DASHBOARD DOCUMENT LIST
  // -------------------------------------------------------------
  let allDocs = [];

  async function loadDocuments() {
    try {
      const res = await fetch("/api/v1/documents?limit=100");
      if (res.ok) {
        allDocs = await res.json();
        renderDocumentTable(allDocs);
        updateStatsBar(allDocs);
      }
    } catch (e) {
      console.error("Failed to load documents:", e);
    }
  }

  function updateStatsBar(docs) {
    const total = docs.length;
    const pass = docs.filter(d => d.processing_status === "PASS").length;
    const fail = docs.filter(d => d.processing_status === "FAIL").length;
    const na = docs.filter(d => d.processing_status === "NOT_APPLICABLE").length;
    const rejected = docs.filter(d => d.processing_status === "REJECTED").length;
    statTotal.textContent = total;
    statPass.textContent = pass;
    statFail.textContent = fail;
    statNa.textContent = na;
    statRejected.textContent = rejected;
  }

  // Search filter
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      const q = searchInput.value.toLowerCase().trim();
      const filtered = q ? allDocs.filter(d =>
        d.document_name.toLowerCase().includes(q) ||
        d.document_type.toLowerCase().includes(q) ||
        d.processing_status.toLowerCase().includes(q)
      ) : allDocs;
      renderDocumentTable(filtered);
    });
  }

  btnRefresh.addEventListener("click", () => {
    loadDocuments();
    checkHealth();
  });

  function renderDocumentTable(docs) {
    if (!docs || docs.length === 0) {
      docTableBody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-muted);">
            No processed documents yet. Upload a document above to get started.
          </td>
        </tr>
      `;
      return;
    }

    docTableBody.innerHTML = docs.map((d) => {
      const statusClass = `status-${d.processing_status.toLowerCase()}`;
      const confStr = d.overall_confidence ? `${Math.round(d.overall_confidence * 100)}%` : "N/A";
      const timeStr = d.processed_at ? new Date(d.processed_at).toLocaleTimeString() : "";

      return `
        <tr data-doc-name="${escapeHtml(d.document_name)}">
          <td><strong style="color: var(--text-primary);">${escapeHtml(d.document_name)}</strong></td>
          <td><span style="font-size: 0.78rem; text-transform: uppercase;">${escapeHtml(d.document_type.replace(/_/g, " "))}</span></td>
          <td><span class="status-pill ${statusClass}">${escapeHtml(d.processing_status)}</span></td>
          <td>${confStr}</td>
          <td>${d.page_count} pg</td>
          <td>${timeStr}</td>
        </tr>
      `;
    }).join("");

    // Add click listeners to rows with selected-row highlight
    docTableBody.querySelectorAll("tr").forEach((row) => {
      row.style.cursor = "pointer";
      row.addEventListener("click", () => {
        // Deselect previous
        docTableBody.querySelectorAll("tr").forEach(r => r.classList.remove("selected-row"));
        row.classList.add("selected-row");
        const name = row.getAttribute("data-doc-name");
        if (name) fetchAndInspectDocument(name);
      });
    });
  }

  async function fetchAndInspectDocument(name) {
    try {
      const res = await fetch(`/api/v1/documents/${encodeURIComponent(name)}`);
      if (res.ok) {
        const data = await res.json();
        renderDocumentResult(data);
        window.scrollTo({ top: resultViewer.offsetTop - 80, behavior: "smooth" });
      }
    } catch (e) {
      console.error("Error inspecting document:", e);
    }
  }

  // -------------------------------------------------------------
  // 5. RESULT VIEWER RENDERING
  // -------------------------------------------------------------
  function renderDocumentResult(data) {
    currentResultData = data;
    emptyViewer.style.display = "none";
    resultViewer.style.display = "block";

    // Header Info
    resDocName.textContent = data.document_name;
    resDocType.textContent = data.document_type.replace(/_/g, " ").toUpperCase();

    const status = data.processing_status;
    resDocStatus.className = `status-pill status-${status.toLowerCase()}`;
    resDocStatus.textContent = status;

    // Metadata
    metaConfidence.textContent = data.overall_confidence ? `${Math.round(data.overall_confidence * 100)}%` : "N/A";
    metaPages.textContent = `${data.file_validation.page_count} page(s)`;
    metaTime.textContent = `${data.processing_metadata.processing_time_ms} ms`;
    metaOcr.textContent = data.processing_metadata.ocr_used ? "OCR Fallback" : "Native Text";

    // Show extraction engine label
    const engineEl = document.getElementById("res-extraction-engine");
    if (engineEl) {
      const llmEngine = data.processing_metadata.llm_engine;
      if (llmEngine) {
        engineEl.textContent = `🤖 ${llmEngine}`;
        engineEl.style.color = "#a5b4fc";
      } else {
        engineEl.textContent = "⚙️ NLP Fallback";
        engineEl.style.color = "var(--text-muted)";
      }
    }

    // Render Tab 1: Financial Validations
    renderValidationTab(data.validation);

    // Render Tab 2: Extracted Fields
    renderFieldsTab(data.extracted_data);

    // Render Tab 3: Tables & Line Items
    renderTablesTab(data.document_type, data.extracted_data);

    // Render Tab 4: Raw JSON
    rawJsonPre.textContent = JSON.stringify(data, null, 2);
  }

  function renderValidationTab(validation) {
    const checks = validation.checks || [];
    if (checks.length === 0) {
      tabValidation.innerHTML = `<p style="color: var(--text-muted);">No financial validations performed.</p>`;
      return;
    }

    tabValidation.innerHTML = checks.map((c) => {
      const statusClass = `status-${c.status.toLowerCase()}`;
      const calcStr = c.calculated_value !== null && c.calculated_value !== undefined ? c.calculated_value.toLocaleString() : "null";
      const repStr = c.reported_value !== null && c.reported_value !== undefined ? c.reported_value.toLocaleString() : "null";
      const varStr = c.variance !== null && c.variance !== undefined ? c.variance.toLocaleString() : "null";

      return `
        <div class="val-card">
          <div class="val-card-header">
            <span class="val-name">${escapeHtml(c.name.replace(/_/g, " "))}</span>
            <span class="status-pill ${statusClass}">${escapeHtml(c.status)}</span>
          </div>
          <div class="val-formula">${escapeHtml(c.formula)}</div>
          <div class="val-details">
            <span>Calculated: <strong>${calcStr}</strong></span>
            <span>Reported: <strong>${repStr}</strong></span>
            <span>Variance: <strong>${varStr}</strong></span>
          </div>
          ${c.message ? `<div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.35rem;">${escapeHtml(c.message)}</div>` : ""}
        </div>
      `;
    }).join("");
  }

  function renderFieldsTab(extracted) {
    const skipKeys = ["line_items", "asset_line_items", "liability_line_items", "equity_line_items", "income_line_items", "expense_line_items", "operating_activities", "investing_activities", "financing_activities", "field_evidence", "additional_fields"];
    const evidenceMap = extracted.field_evidence || {};

    const items = [];
    for (const [key, value] of Object.entries(extracted)) {
      if (skipKeys.includes(key)) continue;

      const isNull = value === null || value === undefined;
      const valDisplay = isNull ? "[Not Present / null]" : String(value);
      const valClass = isNull ? "field-value null-value" : "field-value";

      const evidence = evidenceMap[key];
      let evidenceHtml = "";
      if (evidence && evidence.evidence && evidence.evidence.source_text) {
        evidenceHtml = `
          <span class="evidence-tag" title="Source: Page ${evidence.evidence.page_number}">
            📄 Pg ${evidence.evidence.page_number}: "${escapeHtml(evidence.evidence.source_text)}"
          </span>
        `;
      }

      items.push(`
        <div class="field-item">
          <div class="field-label">${escapeHtml(key.replace(/_/g, " "))}</div>
          <div class="${valClass}">${escapeHtml(valDisplay)}</div>
          ${evidenceHtml}
        </div>
      `);
    }

    tabFields.innerHTML = `<div class="field-grid">${items.join("")}</div>`;
  }

  function renderTablesTab(docType, extracted) {
    let items = [];
    let title = "Line Items / Tables";

    if (docType === "invoice") {
      items = extracted.line_items || [];
      title = "Invoice Line Items";
    } else if (docType === "balance_sheet") {
      items = [
        ...(extracted.asset_line_items || []).map(x => ({ ...x, section: "Asset" })),
        ...(extracted.liability_line_items || []).map(x => ({ ...x, section: "Liability" })),
        ...(extracted.equity_line_items || []).map(x => ({ ...x, section: "Equity" }))
      ];
      title = "Balance Sheet Line Items";
    } else if (docType === "profit_and_loss") {
      items = [
        ...(extracted.income_line_items || []).map(x => ({ ...x, section: "Income" })),
        ...(extracted.expense_line_items || []).map(x => ({ ...x, section: "Expense" }))
      ];
      title = "P&L Breakdown Items";
    } else if (docType === "cash_flow_statement") {
      items = [
        ...(extracted.operating_activities || []).map(x => ({ ...x, section: "Operating" })),
        ...(extracted.investing_activities || []).map(x => ({ ...x, section: "Investing" })),
        ...(extracted.financing_activities || []).map(x => ({ ...x, section: "Financing" }))
      ];
      title = "Cash Flow Activities";
    }

    if (!items || items.length === 0) {
      tabTables.innerHTML = `<p style="color: var(--text-muted);">No structured table or line items detected for this document.</p>`;
      return;
    }

    if (docType === "invoice") {
      tabTables.innerHTML = `
        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th>Description</th>
                <th>Qty</th>
                <th>Unit Price</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
              ${items.map(it => `
                <tr>
                  <td>${escapeHtml(it.description || "N/A")}</td>
                  <td>${it.quantity !== null && it.quantity !== undefined ? it.quantity : "N/A"}</td>
                  <td>${it.unit_price !== null && it.unit_price !== undefined ? it.unit_price.toFixed(2) : "N/A"}</td>
                  <td><strong>${it.amount !== null && it.amount !== undefined ? it.amount.toFixed(2) : "N/A"}</strong></td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    } else {
      tabTables.innerHTML = `
        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th>Section</th>
                <th>Item Name</th>
                <th>Reported Amount</th>
              </tr>
            </thead>
            <tbody>
              ${items.map(it => `
                <tr>
                  <td><span class="status-pill status-pass" style="font-size: 0.7rem;">${escapeHtml(it.section || "Item")}</span></td>
                  <td>${escapeHtml(it.name || "N/A")}</td>
                  <td><strong>${it.amount !== null && it.amount !== undefined ? it.amount.toLocaleString() : "N/A"}</strong></td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    }
  }

  // -------------------------------------------------------------
  // 6. TAB SWITCHING
  // -------------------------------------------------------------
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      document.getElementById(targetId).classList.add("active");
    });
  });

  // Copy Raw JSON
  btnCopyJson.addEventListener("click", () => {
    if (currentResultData) {
      navigator.clipboard.writeText(JSON.stringify(currentResultData, null, 2)).then(() => {
        btnCopyJson.textContent = "Copied!";
        setTimeout(() => (btnCopyJson.textContent = "Copy JSON"), 2000);
      });
    }
  });

  // Helper
  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
