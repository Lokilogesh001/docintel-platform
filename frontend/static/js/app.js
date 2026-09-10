// DocIntel AI - Modern Enterprise SaaS Frontend Application
document.addEventListener("DOMContentLoaded", () => {
  // Upload Elements
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
  const pipelineProgress = document.getElementById("pipeline-progress");

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

  // Dashboard & Search Elements
  const docTableBody = document.getElementById("doc-table-body");
  const btnRefresh = document.getElementById("btn-refresh-docs");
  const searchInput = document.getElementById("search-docs");
  const globalSearchInput = document.getElementById("global-search-input");
  const btnViewFormats = document.getElementById("btn-view-formats");

  // Result Viewer / Inspector Elements
  const inspectionCard = document.getElementById("inspection-card");
  const resultViewer = document.getElementById("result-viewer");
  const emptyViewer = document.getElementById("empty-viewer");
  const resDocName = document.getElementById("res-doc-name");
  const resDocType = document.getElementById("res-doc-type");
  const resDocStatus = document.getElementById("res-doc-status");
  const resExtractionEngine = document.getElementById("res-extraction-engine");
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
  let allDocs = [];

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
        if (healthText) healthText.textContent = "API Ready";
        if (llmText) {
          llmText.textContent = data.llm_configured ? "GPT-4o-mini" : "NLP Fallback";
        }
      } else {
        if (healthText) healthText.textContent = "API Degraded";
      }
    } catch (e) {
      if (healthText) healthText.textContent = "API Offline";
    }
  }

  // -------------------------------------------------------------
  // 2. CATEGORY CARD SELECTION
  // -------------------------------------------------------------
  const catOptions = document.querySelectorAll(".cat-option");
  catOptions.forEach(opt => {
    opt.addEventListener("click", () => {
      const radio = opt.querySelector('input[type="radio"]');
      if (radio) radio.checked = true;
    });
  });

  // -------------------------------------------------------------
  // 3. FILE SELECTION & DRAG-AND-DROP
  // -------------------------------------------------------------
  if (dropzone) {
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
  }

  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFileSelected(e.target.files[0]);
      }
    });
  }

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
    if (fileNameDisplay) {
      fileNameDisplay.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    }
    if (dropzone) dropzone.style.display = "none";
    if (filePreview) filePreview.style.display = "flex";
    if (btnProcess) {
      btnProcess.disabled = false;
      btnText.textContent = "Extract & Validate Document";
    }
    clearAlert();
  }

  if (btnRemoveFile) {
    btnRemoveFile.addEventListener("click", (e) => {
      e.stopPropagation();
      selectedFile = null;
      if (fileInput) fileInput.value = "";
      if (filePreview) filePreview.style.display = "none";
      if (dropzone) dropzone.style.display = "flex";
      if (btnProcess) {
        btnProcess.disabled = true;
        btnText.textContent = "Choose File";
      }
    });
  }

  if (btnViewFormats) {
    btnViewFormats.addEventListener("click", () => {
      alert("Supported Document Formats:\n• PDF (Native text or scanned raster)\n• JPG / JPEG (Scanned invoices & statements)\n• PNG (High-resolution documents)\n\nConstraints: Maximum 3 pages, up to 15MB per file.");
    });
  }

  // -------------------------------------------------------------
  // 4. DOCUMENT PROCESS SUBMISSION
  // -------------------------------------------------------------
  if (uploadForm) {
    uploadForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!selectedFile) {
        fileInput.click();
        return;
      }

      const docTypeRadio = document.querySelector('input[name="doc_type"]:checked');
      const docType = docTypeRadio ? docTypeRadio.value : "invoice";

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

        // Smooth scroll to inspection card
        if (inspectionCard) {
          inspectionCard.style.display = "block";
          inspectionCard.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      } catch (err) {
        showAlert("NETWORK_ERROR", `Failed to communicate with API: ${err.message}`);
        setProcessingState(false);
      }
    });
  }

  function setProcessingState(isProcessing) {
    if (isProcessing) {
      if (btnProcess) btnProcess.disabled = true;
      if (spinner) spinner.style.display = "inline-block";
      if (btnText) btnText.textContent = "Processing Pipeline Active...";
      if (pipelineProgress) pipelineProgress.style.display = "block";
    } else {
      if (btnProcess) btnProcess.disabled = !selectedFile;
      if (spinner) spinner.style.display = "none";
      if (btnText) btnText.textContent = selectedFile ? "Extract & Validate Document" : "Choose File";
      if (pipelineProgress) pipelineProgress.style.display = "none";
    }
  }

  function showAlert(code, message) {
    if (alertContainer) {
      alertContainer.innerHTML = `
        <div class="alert-box alert-danger" id="error-alert">
          <span>⚠️ <strong>[${escapeHtml(code)}]</strong> ${escapeHtml(message)}</span>
        </div>
      `;
    }
  }

  function clearAlert() {
    if (alertContainer) alertContainer.innerHTML = "";
  }

  // -------------------------------------------------------------
  // 5. DASHBOARD DOCUMENT LIST & METRICS
  // -------------------------------------------------------------
  async function loadDocuments() {
    try {
      const res = await fetch("/api/v1/documents?limit=100");
      if (res.ok) {
        allDocs = await res.json();
        renderDocumentTable(allDocs);
        updateStats(allDocs);
      }
    } catch (e) {
      console.error("Failed to load documents:", e);
    }
  }

  function updateStats(docs) {
    const total = docs.length;
    const pass = docs.filter(d => d.processing_status === "PASS").length;
    const fail = docs.filter(d => d.processing_status === "FAIL").length;
    const na = docs.filter(d => d.processing_status === "NOT_APPLICABLE").length;
    const rejected = docs.filter(d => d.processing_status === "REJECTED").length;

    if (statTotal) statTotal.textContent = total;
    if (statPass) statPass.textContent = pass;
    if (statFail) statFail.textContent = fail;
    if (statNa) statNa.textContent = na;
    if (statRejected) statRejected.textContent = rejected;
  }

  // Synchronized Search Handlers
  function handleSearch(query) {
    const q = (query || "").toLowerCase().trim();
    const filtered = q ? allDocs.filter(d =>
      d.document_name.toLowerCase().includes(q) ||
      d.document_type.toLowerCase().includes(q) ||
      d.processing_status.toLowerCase().includes(q)
    ) : allDocs;
    renderDocumentTable(filtered);
  }

  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      if (globalSearchInput) globalSearchInput.value = e.target.value;
      handleSearch(e.target.value);
    });
  }

  if (globalSearchInput) {
    globalSearchInput.addEventListener("input", (e) => {
      if (searchInput) searchInput.value = e.target.value;
      handleSearch(e.target.value);
    });
  }

  // Ctrl + K shortcut
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      if (globalSearchInput) globalSearchInput.focus();
    }
  });

  if (btnRefresh) {
    btnRefresh.addEventListener("click", () => {
      loadDocuments();
      checkHealth();
    });
  }

  function renderDocumentTable(docs) {
    if (!docTableBody) return;

    if (!docs || docs.length === 0) {
      docTableBody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; padding: 2.5rem; color: var(--text-muted);">
            No processed documents yet. Upload a document above to get started.
          </td>
        </tr>
      `;
      return;
    }

    docTableBody.innerHTML = docs.map((d, index) => {
      const statusClass = `status-${d.processing_status.toLowerCase()}`;
      const confStr = d.overall_confidence ? `${Math.round(d.overall_confidence * 100)}%` : "N/A";
      
      let dateStr = "";
      if (d.processed_at) {
        const dt = new Date(d.processed_at);
        const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        const m = months[dt.getMonth()];
        const day = dt.getDate();
        const y = dt.getFullYear();
        const hrs = String(dt.getHours()).padStart(2, "0");
        const mins = String(dt.getMinutes()).padStart(2, "0");
        dateStr = `${m} ${day}, ${y} ${hrs}:${mins}`;
      }

      // File badge
      const ext = d.document_name.split(".").pop().toLowerCase();
      let badgeClass = "badge-pdf";
      let badgeLabel = "PDF";
      if (ext === "jpg" || ext === "jpeg") {
        badgeClass = "badge-jpg";
        badgeLabel = "JPG";
      } else if (ext === "png") {
        badgeClass = "badge-png";
        badgeLabel = "PNG";
      }

      return `
        <tr data-doc-name="${escapeHtml(d.document_name)}">
          <td style="color: var(--text-muted); font-size: 0.8rem; font-weight: 500;">${index + 1}</td>
          <td>
            <div class="doc-name-cell">
              <span class="doc-file-badge ${badgeClass}">${badgeLabel}</span>
              <span>${escapeHtml(d.document_name)}</span>
            </div>
          </td>
          <td><span class="cat-pill">${escapeHtml(d.document_type.replace(/_/g, " "))}</span></td>
          <td><span class="status-pill ${statusClass}">${escapeHtml(d.processing_status)}</span></td>
          <td style="font-weight: 600; color: var(--text-main);">${confStr}</td>
          <td style="color: var(--text-muted); font-size: 0.8rem;">${dateStr}</td>
          <td style="text-align: right;">
            <div class="action-buttons-group" style="justify-content: flex-end;">
              <button type="button" class="tbl-action-btn btn-view-doc" title="View / Inspect Document">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
              </button>
              <button type="button" class="tbl-action-btn btn-download-doc" title="Download Raw JSON">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
              </button>
              <button type="button" class="tbl-action-btn btn-more-doc" title="Options">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="1"></circle><circle cx="19" cy="12" r="1"></circle><circle cx="5" cy="12" r="1"></circle></svg>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join("");

    // Attach row events
    docTableBody.querySelectorAll("tr").forEach((row) => {
      const docName = row.getAttribute("data-doc-name");
      if (!docName) return;

      // Click row
      row.addEventListener("click", (e) => {
        if (e.target.closest(".btn-download-doc")) return;
        highlightAndInspect(row, docName);
      });

      // Click View
      const btnView = row.querySelector(".btn-view-doc");
      if (btnView) {
        btnView.addEventListener("click", (e) => {
          e.stopPropagation();
          highlightAndInspect(row, docName);
        });
      }

      // Click Download
      const btnDl = row.querySelector(".btn-download-doc");
      if (btnDl) {
        btnDl.addEventListener("click", async (e) => {
          e.stopPropagation();
          await downloadDocJson(docName);
        });
      }
    });
  }

  function highlightAndInspect(row, name) {
    docTableBody.querySelectorAll("tr").forEach(r => r.classList.remove("selected-row"));
    row.classList.add("selected-row");
    fetchAndInspectDocument(name);
  }

  async function fetchAndInspectDocument(name) {
    try {
      const res = await fetch(`/api/v1/documents/${encodeURIComponent(name)}`);
      if (res.ok) {
        const data = await res.json();
        renderDocumentResult(data);
        if (inspectionCard) {
          inspectionCard.style.display = "block";
          inspectionCard.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }
    } catch (e) {
      console.error("Error inspecting document:", e);
    }
  }

  async function downloadDocJson(name) {
    try {
      const res = await fetch(`/api/v1/documents/${encodeURIComponent(name)}`);
      if (res.ok) {
        const data = await res.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${name}_extracted.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (e) {
      console.error("Failed to download JSON:", e);
    }
  }

  // -------------------------------------------------------------
  // 6. RESULT VIEWER RENDERING
  // -------------------------------------------------------------
  function renderDocumentResult(data) {
    currentResultData = data;
    if (emptyViewer) emptyViewer.style.display = "none";
    if (resultViewer) resultViewer.style.display = "block";

    // Header Info
    if (resDocName) resDocName.textContent = data.document_name;
    if (resDocType) resDocType.textContent = data.document_type.replace(/_/g, " ").toUpperCase();

    const status = data.processing_status;
    if (resDocStatus) {
      resDocStatus.innerHTML = `<span class="status-pill status-${status.toLowerCase()}">${status}</span>`;
    }

    // Metadata
    if (metaConfidence) {
      metaConfidence.textContent = data.overall_confidence ? `${Math.round(data.overall_confidence * 100)}%` : "N/A";
    }
    if (metaPages) {
      metaPages.textContent = `${data.file_validation.page_count} page(s)`;
    }
    if (metaTime) {
      metaTime.textContent = `${data.processing_metadata.processing_time_ms} ms`;
    }
    if (metaOcr) {
      metaOcr.textContent = data.processing_metadata.ocr_used ? "OCR Fallback" : "Native Text";
    }

    if (resExtractionEngine) {
      const llmEngine = data.processing_metadata.llm_engine;
      resExtractionEngine.textContent = llmEngine ? `🤖 ${llmEngine}` : "⚙️ NLP Fallback";
    }

    // Render Tab 1: Financial Validations
    renderValidationTab(data.validation);

    // Render Tab 2: Extracted Fields
    renderFieldsTab(data.extracted_data);

    // Render Tab 3: Tables & Line Items
    renderTablesTab(data.document_type, data.extracted_data);

    // Render Tab 4: Raw JSON
    if (rawJsonPre) rawJsonPre.textContent = JSON.stringify(data, null, 2);
  }

  function renderValidationTab(validation) {
    if (!tabValidation) return;
    const checks = validation.checks || [];
    if (checks.length === 0) {
      tabValidation.innerHTML = `<p style="color: var(--text-muted); padding: 1rem 0;">No financial validations performed.</p>`;
      return;
    }

    tabValidation.innerHTML = checks.map((c) => {
      const statusClass = `status-${c.status.toLowerCase()}`;
      const calcStr = c.calculated_value !== null && c.calculated_value !== undefined ? Number(c.calculated_value).toLocaleString() : "null";
      const repStr = c.reported_value !== null && c.reported_value !== undefined ? Number(c.reported_value).toLocaleString() : "null";
      const varStr = c.variance !== null && c.variance !== undefined ? Number(c.variance).toLocaleString() : "null";

      return `
        <div class="val-card-item">
          <div class="val-header">
            <span class="val-title">${escapeHtml(c.name.replace(/_/g, " "))}</span>
            <span class="status-pill ${statusClass}">${escapeHtml(c.status)}</span>
          </div>
          <div class="val-formula-code">${escapeHtml(c.formula)}</div>
          <div class="val-numbers-row">
            <span>Calculated: <strong style="color: var(--text-main);">${calcStr}</strong></span>
            <span>Reported: <strong style="color: var(--text-main);">${repStr}</strong></span>
            <span>Variance: <strong style="color: var(--text-main);">${varStr}</strong></span>
          </div>
          ${c.message ? `<div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.35rem;">${escapeHtml(c.message)}</div>` : ""}
        </div>
      `;
    }).join("");
  }

  function renderFieldsTab(extracted) {
    if (!tabFields) return;
    const skipKeys = ["line_items", "asset_line_items", "liability_line_items", "equity_line_items", "income_line_items", "expense_line_items", "operating_activities", "investing_activities", "financing_activities", "field_evidence", "additional_fields"];
    const evidenceMap = extracted.field_evidence || {};

    const items = [];
    for (const [key, value] of Object.entries(extracted)) {
      if (skipKeys.includes(key)) continue;

      const isNull = value === null || value === undefined;
      const valDisplay = isNull ? "null" : String(value);
      const valClass = isNull ? "field-cell-val null-val" : "field-cell-val";

      const evidence = evidenceMap[key];
      let evidenceHtml = "";
      if (evidence && evidence.evidence && evidence.evidence.source_text) {
        evidenceHtml = `
          <div class="evidence-chip" title="Source on Page ${evidence.evidence.page_number}">
            📄 Pg ${evidence.evidence.page_number}: "${escapeHtml(evidence.evidence.source_text)}"
          </div>
        `;
      }

      items.push(`
        <div class="field-cell">
          <div class="field-cell-label">${escapeHtml(key.replace(/_/g, " "))}</div>
          <div class="${valClass}">${escapeHtml(valDisplay)}</div>
          ${evidenceHtml}
        </div>
      `);
    }

    tabFields.innerHTML = `<div class="fields-2col-grid">${items.join("")}</div>`;
  }

  function renderTablesTab(docType, extracted) {
    if (!tabTables) return;
    let items = [];

    if (docType === "invoice") {
      items = extracted.line_items || [];
    } else if (docType === "balance_sheet") {
      items = [
        ...(extracted.asset_line_items || []).map(x => ({ ...x, section: "Asset" })),
        ...(extracted.liability_line_items || []).map(x => ({ ...x, section: "Liability" })),
        ...(extracted.equity_line_items || []).map(x => ({ ...x, section: "Equity" }))
      ];
    } else if (docType === "profit_and_loss") {
      items = [
        ...(extracted.income_line_items || []).map(x => ({ ...x, section: "Income" })),
        ...(extracted.expense_line_items || []).map(x => ({ ...x, section: "Expense" }))
      ];
    } else if (docType === "cash_flow_statement") {
      items = [
        ...(extracted.operating_activities || []).map(x => ({ ...x, section: "Operating" })),
        ...(extracted.investing_activities || []).map(x => ({ ...x, section: "Investing" })),
        ...(extracted.financing_activities || []).map(x => ({ ...x, section: "Financing" }))
      ];
    }

    if (!items || items.length === 0) {
      tabTables.innerHTML = `<p style="color: var(--text-muted); padding: 1rem 0;">No structured table or line items detected for this document.</p>`;
      return;
    }

    if (docType === "invoice") {
      tabTables.innerHTML = `
        <div class="table-responsive">
          <table class="modern-table">
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
                  <td><strong>${escapeHtml(it.description || "N/A")}</strong></td>
                  <td>${it.quantity !== null && it.quantity !== undefined ? it.quantity : "N/A"}</td>
                  <td>${it.unit_price !== null && it.unit_price !== undefined ? it.unit_price.toFixed(2) : "N/A"}</td>
                  <td><strong style="color: var(--primary);">${it.amount !== null && it.amount !== undefined ? it.amount.toFixed(2) : "N/A"}</strong></td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    } else {
      tabTables.innerHTML = `
        <div class="table-responsive">
          <table class="modern-table">
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
                  <td><span class="status-pill status-pass" style="font-size: 0.68rem;">${escapeHtml(it.section || "Item")}</span></td>
                  <td><strong>${escapeHtml(it.name || "N/A")}</strong></td>
                  <td><strong style="color: var(--primary);">${it.amount !== null && it.amount !== undefined ? Number(it.amount).toLocaleString() : "N/A"}</strong></td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    }
  }

  // -------------------------------------------------------------
  // 7. TAB SWITCHING
  // -------------------------------------------------------------
  document.querySelectorAll(".tab-nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-nav-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach((c) => c.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add("active");
    });
  });

  // Copy Raw JSON
  if (btnCopyJson) {
    btnCopyJson.addEventListener("click", () => {
      if (currentResultData) {
        navigator.clipboard.writeText(JSON.stringify(currentResultData, null, 2)).then(() => {
          btnCopyJson.textContent = "Copied!";
          setTimeout(() => (btnCopyJson.textContent = "Copy JSON"), 2000);
        });
      }
    });
  }

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
