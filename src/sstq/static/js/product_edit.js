const productImage = document.getElementById("product-image");
const imageWrapper = document.querySelector(".product-image-wrapper");
const editBarcodeInput = document.getElementById("edit-barcode");
const editImageInput = document.getElementById("edit-image");
const editImageFile = document.getElementById("edit-image-file");
const chooseImageFileButton = document.getElementById("choose-image-file");
const editImageStatus = document.getElementById("edit-image-status");
const editCapturedImage = document.getElementById("edit-captured-image");
const editorForm = document.querySelector(".editor-form");

const EDITOR_CONFIG = {
  timeline: {
    fields: [
      { name: "stage_type", label: "Stage Type", placeholder: "Raw Material Sourcing" },
      { name: "country", label: "Country", placeholder: "Brazil" },
      { name: "region", label: "Region", placeholder: "Amazon" },
      { name: "start_date", label: "Start Date", placeholder: "2024-01-01" },
      { name: "end_date", label: "End Date", placeholder: "2024-01-08" },
      { name: "description", label: "Description", placeholder: "Cocoa bean sourcing", multiline: true },
    ],
    textareaId: "timeline_rows",
    listId: "timeline-list",
    scriptId: "timeline-items",
    title: (row, index) => row.stage_type || `Timeline Row ${index + 1}`,
  },
  breakdown: {
    fields: [
      { name: "name", label: "Name", placeholder: "Cocoa" },
      { name: "country", label: "Country", placeholder: "Brazil" },
      { name: "percentage", label: "Percentage", placeholder: "65" },
      { name: "notes", label: "Notes", placeholder: "Rainforest farm region", multiline: true },
    ],
    textareaId: "breakdown_rows",
    listId: "breakdown-list",
    scriptId: "breakdown-items",
    title: (row, index) => row.name || `Breakdown Row ${index + 1}`,
  },
  claim: {
    fields: [
      { name: "claim_type", label: "Claim Type", placeholder: "Sustainability" },
      { name: "claim_text", label: "Claim Text", placeholder: "Uses certified farms", multiline: true },
      { name: "confidence_label", label: "Confidence Label", placeholder: "verified" },
      { name: "rationale", label: "Rationale", placeholder: "Checked against latest certificates", multiline: true },
    ],
    textareaId: "claim_rows",
    listId: "claim-list",
    scriptId: "claim-items",
    title: (row, index) => row.claim_type || `Claim Row ${index + 1}`,
  },
  evidence: {
    fields: [
      { name: "claim_index", label: "Claim Index", placeholder: "1" },
      { name: "evidence_type", label: "Evidence Type", placeholder: "Certificate" },
      { name: "issuer", label: "Issuer", placeholder: "Rainforest Alliance" },
      { name: "date", label: "Date", placeholder: "2024-02-15" },
      { name: "summary", label: "Summary", placeholder: "Annual certificate renewed", multiline: true },
      { name: "file_reference", label: "File Reference", type: "file_reference" },
    ],
    textareaId: "evidence_rows",
    listId: "evidence-list",
    scriptId: "evidence-items",
    title: (row, index) => row.evidence_type || `Evidence Row ${index + 1}`,
  },
};

function createImageFallback(message) {
  if (!imageWrapper || document.getElementById("product-image-fallback")) return;
  const fallback = document.createElement("div");
  fallback.id = "product-image-fallback";
  fallback.className = "product-image-fallback";
  fallback.textContent = message;
  imageWrapper.appendChild(fallback);
}

if (productImage) {
  productImage.addEventListener("error", () => {
    productImage.remove();
    createImageFallback("Image URL is unavailable");
  });
}

async function uploadImageBlob(blob) {
  const barcode = editBarcodeInput?.value?.trim() || "";
  const formData = new FormData();
  formData.append("image", blob, "product-image.jpg");
  formData.append("barcode", barcode);

  const response = await fetch("/upload_product_image_temp", {
    method: "POST",
    body: formData,
  });
  return response.json();
}

function applyUploadedImageUrl(imageUrl) {
  if (editImageInput) editImageInput.value = imageUrl;
  if (editCapturedImage) {
    editCapturedImage.src = imageUrl;
    editCapturedImage.hidden = false;
  }
  if (productImage) {
    productImage.src = imageUrl;
  }
}

async function uploadSelectedFile() {
  const file = editImageFile?.files?.[0];
  if (!file) {
    if (editImageStatus) editImageStatus.textContent = "Please choose an image file first.";
    return;
  }

  if (editImageStatus) editImageStatus.textContent = "Uploading image to cache...";

  try {
    const data = await uploadImageBlob(file);
    if (!data.success) {
      if (editImageStatus) editImageStatus.textContent = data.message || "Image upload failed.";
      return;
    }
    applyUploadedImageUrl(data.image_url);
    if (editImageStatus) editImageStatus.textContent = "Cached image ready. Save changes to publish it.";
  } catch {
    if (editImageStatus) editImageStatus.textContent = "Image upload failed.";
  }
}

editImageFile?.addEventListener("change", () => {
  if (editImageFile.files?.length) {
    uploadSelectedFile();
  }
});

chooseImageFileButton?.addEventListener("click", () => {
  editImageFile?.click();
});

function parseItems(scriptId, fieldNames) {
  const element = document.getElementById(scriptId);
  if (!element) return [];

  try {
    const rows = JSON.parse(element.textContent || "[]");
    return rows.map((row) => {
      const mapped = {};
      fieldNames.forEach((field, index) => {
        mapped[field] = row[index] || "";
      });
      return mapped;
    });
  } catch {
    return [];
  }
}

function buildRowText(config, row) {
  return config.fields.map((field) => String(row[field.name] || "").replaceAll("|", "/").replaceAll("\n", " ").trim()).join("|");
}

function fileNameFromReference(fileReference) {
  const value = String(fileReference || "").trim();
  if (!value) return "";
  try {
    const pathname = new URL(value, window.location.origin).pathname;
    return pathname.split("/").pop() || value;
  } catch {
    return value.split("/").pop() || value;
  }
}

async function uploadEvidenceFile(file) {
  const barcode = editBarcodeInput?.value?.trim() || "";
  const formData = new FormData();
  formData.append("file", file, file.name || "evidence.pdf");
  formData.append("barcode", barcode);

  const response = await fetch("/upload_evidence_file_temp", {
    method: "POST",
    body: formData,
  });
  return response.json();
}

function createField(field, value, onChange) {
  const wrapper = document.createElement("label");
  wrapper.className = "record-field";

  const label = document.createElement("span");
  label.textContent = field.label;
  wrapper.appendChild(label);

  if (field.type === "file_reference") {
    const fileName = document.createElement("div");
    fileName.className = "file-reference-name";
    fileName.textContent = fileNameFromReference(value) || "No file selected.";
    wrapper.appendChild(fileName);

    const helperText = document.createElement("p");
    helperText.className = "field-help-text";
    helperText.textContent = "PDF uploads go to cache first and are published on save.";
    wrapper.appendChild(helperText);

    const actionButton = document.createElement("button");
    actionButton.type = "button";
    actionButton.className = "file-action-box";
    actionButton.textContent = value ? "Replace File" : "Choose File";
    wrapper.appendChild(actionButton);

    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = ".pdf,application/pdf";
    fileInput.className = "image-file-input";
    wrapper.appendChild(fileInput);

    const uploadStatus = document.createElement("p");
    uploadStatus.className = "field-help-text";
    wrapper.appendChild(uploadStatus);

    actionButton.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", async () => {
      const file = fileInput.files?.[0];
      if (!file) return;

      uploadStatus.textContent = "Uploading PDF to cache...";
      try {
        const data = await uploadEvidenceFile(file);
        if (!data.success) {
          uploadStatus.textContent = data.message || "PDF upload failed.";
          return;
        }
        onChange(field.name, data.file_url);
        fileName.textContent = fileNameFromReference(data.file_url) || file.name;
        actionButton.textContent = "Replace File";
        uploadStatus.textContent = "Cached PDF ready. Save changes to publish it.";
      } catch {
        uploadStatus.textContent = "PDF upload failed.";
      }
    });

    return wrapper;
  }

  const input = field.multiline ? document.createElement("textarea") : document.createElement("input");
  input.value = value || "";
  input.placeholder = field.placeholder || "";
  input.rows = field.multiline ? 3 : undefined;
  input.addEventListener("input", (event) => onChange(field.name, event.target.value));
  wrapper.appendChild(input);
  return wrapper;
}

function renderEditor(type) {
  const config = EDITOR_CONFIG[type];
  const list = document.getElementById(config.listId);
  const textarea = document.getElementById(config.textareaId);
  if (!list || !textarea) return;

  const fieldNames = config.fields.map((field) => field.name);
  const rows = parseItems(config.scriptId, fieldNames);
  const state = rows.length ? rows : [Object.fromEntries(fieldNames.map((name) => [name, ""]))];
  let expandedIndex = null;

  const syncTextarea = () => {
    textarea.value = state
      .filter((row) => config.fields.some((field) => String(row[field.name] || "").trim() !== ""))
      .map((row) => buildRowText(config, row))
      .join("\n");
  };

  const renderRows = () => {
    list.innerHTML = "";
    state.forEach((row, index) => {
      const card = document.createElement("article");
      card.className = "record-card";
      card.id = `${type}-row-${index}`;
      if (expandedIndex === index) {
        card.classList.add("is-expanded");
      }

      const header = document.createElement("div");
      header.className = "record-card-header";

      const summary = document.createElement("p");
      summary.className = "record-card-summary";
      summary.textContent = config.title(row, index);
      header.appendChild(summary);

      const headerActions = document.createElement("div");
      headerActions.className = "record-card-actions";

      const editButton = document.createElement("button");
      editButton.type = "button";
      editButton.className = "edit-row-button";
      editButton.textContent = expandedIndex === index ? "Close" : "Edit";
      editButton.addEventListener("click", () => {
        expandedIndex = expandedIndex === index ? null : index;
        renderRows();
        document.getElementById(`${type}-row-${index}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
      headerActions.appendChild(editButton);

      const removeButton = document.createElement("button");
      removeButton.type = "button";
      removeButton.className = "remove-row-button";
      removeButton.textContent = "Remove";
      removeButton.addEventListener("click", () => {
        if (state.length === 1) {
          state[0] = Object.fromEntries(fieldNames.map((name) => [name, ""]));
        } else {
          state.splice(index, 1);
        }
        if (expandedIndex === index) expandedIndex = null;
        if (expandedIndex !== null && expandedIndex > index) expandedIndex -= 1;
        renderRows();
      });
      headerActions.appendChild(removeButton);
      header.appendChild(headerActions);
      card.appendChild(header);

      const body = document.createElement("div");
      body.className = "record-card-body";

      config.fields.forEach((field) => {
        body.appendChild(
          createField(field, row[field.name], (name, value) => {
            row[name] = value;
            syncTextarea();
            summary.textContent = config.title(row, index);
          }),
        );
      });

      card.appendChild(body);

      list.appendChild(card);
    });

    syncTextarea();
  };

  document.querySelector(`[data-add-row="${type}"]`)?.addEventListener("click", () => {
    state.push(Object.fromEntries(fieldNames.map((name) => [name, ""])));
    expandedIndex = state.length - 1;
    renderRows();
  });

  renderRows();
}

Object.keys(EDITOR_CONFIG).forEach(renderEditor);

editorForm?.addEventListener("submit", () => {
  Object.keys(EDITOR_CONFIG).forEach((type) => {
    const textarea = document.getElementById(EDITOR_CONFIG[type].textareaId);
    if (textarea) {
      textarea.value = textarea.value.trim();
    }
  });
});
