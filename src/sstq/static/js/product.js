const productImage = document.getElementById("product-image");
const imageWrapper = document.querySelector(".product-image-wrapper");
const description = document.getElementById("description");
const toggleButton = document.getElementById("toggle-description");
const editBarcodeInput = document.getElementById("edit-barcode");
const editImageInput = document.getElementById("edit-image");
const editImageFile = document.getElementById("edit-image-file");
const uploadImageFileButton = document.getElementById("upload-image-file");
const editImageStatus = document.getElementById("edit-image-status");
const editCapturedImage = document.getElementById("edit-captured-image");
const editPhotoVideo = document.getElementById("edit-photo-preview");
const startEditPhotoCameraButton = document.getElementById("start-edit-photo-camera");
const captureEditPhotoButton = document.getElementById("capture-edit-photo");
const stopEditPhotoCameraButton = document.getElementById("stop-edit-photo-camera");

let editPhotoStream = null;

function createImageFallback(message) {
  if (!imageWrapper) return;
  if (document.getElementById("product-image-fallback")) return;

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

if (description && toggleButton) {
  const rawText = description.textContent?.trim() || "";
  const isLongText = rawText.length > 190;

  if (!isLongText) {
    description.classList.remove("collapsed");
    toggleButton.classList.add("hidden");
  } else {
    toggleButton.addEventListener("click", () => {
      const isCollapsed = description.classList.toggle("collapsed");
      toggleButton.textContent = isCollapsed ? "Show more" : "Show less";
    });
  }
}

function stopEditPhotoCamera(updateStatus = true) {
  if (editPhotoStream instanceof MediaStream) {
    editPhotoStream.getTracks().forEach((track) => track.stop());
  }
  editPhotoStream = null;

  if (editPhotoVideo) {
    editPhotoVideo.srcObject = null;
  }

  if (updateStatus && editImageStatus) {
    editImageStatus.textContent = "Camera closed.";
  }
}

async function uploadImageBlob(blob) {
  const barcode = editBarcodeInput?.value?.trim() || "";
  const formData = new FormData();
  formData.append("image", blob, "product-image.jpg");
  formData.append("barcode", barcode);

  const response = await fetch("/upload_product_image", {
    method: "POST",
    body: formData,
  });
  return response.json();
}

function applyUploadedImageUrl(imageUrl) {
  if (editImageInput) {
    editImageInput.value = imageUrl;
  }
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
    if (editImageStatus) {
      editImageStatus.textContent = "Please choose an image file first.";
    }
    return;
  }

  if (editImageStatus) {
    editImageStatus.textContent = "Uploading image...";
  }

  try {
    const data = await uploadImageBlob(file);
    if (!data.success) {
      if (editImageStatus) {
        editImageStatus.textContent = data.message || "Image upload failed.";
      }
      return;
    }

    applyUploadedImageUrl(data.image_url);
    if (editImageStatus) {
      editImageStatus.textContent = "Image uploaded successfully.";
    }
  } catch (error) {
    if (editImageStatus) {
      editImageStatus.textContent = "Image upload failed.";
    }
  }
}

async function startEditPhotoCamera() {
  if (!editPhotoVideo || !editImageStatus) {
    return;
  }

  stopEditPhotoCamera(false);

  if (!navigator.mediaDevices?.getUserMedia) {
    editImageStatus.textContent = "Camera not available here. Use HTTPS (tunnel) or localhost.";
    return;
  }

  try {
    editPhotoStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" } },
      audio: false,
    });
    editPhotoVideo.srcObject = editPhotoStream;
    editImageStatus.textContent = "Camera ready.";
  } catch (error) {
    editImageStatus.textContent = `Could not open camera: ${error?.name || error}`;
  }
}

function captureEditPhoto() {
  if (!editPhotoVideo || !editImageStatus) {
    return;
  }
  if (!(editPhotoStream instanceof MediaStream)) {
    editImageStatus.textContent = "Open camera first.";
    return;
  }

  const width = editPhotoVideo.videoWidth;
  const height = editPhotoVideo.videoHeight;
  if (!width || !height) {
    editImageStatus.textContent = "Camera not ready yet. Try again.";
    return;
  }

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) {
    editImageStatus.textContent = "Capture failed.";
    return;
  }

  context.drawImage(editPhotoVideo, 0, 0, width, height);
  editImageStatus.textContent = "Uploading captured photo...";

  canvas.toBlob(async (blob) => {
    if (!blob) {
      editImageStatus.textContent = "Capture failed.";
      return;
    }

    try {
      const data = await uploadImageBlob(blob);
      if (!data.success) {
        editImageStatus.textContent = data.message || "Photo upload failed.";
        return;
      }

      applyUploadedImageUrl(data.image_url);
      editImageStatus.textContent = "Photo uploaded successfully.";
    } catch (error) {
      editImageStatus.textContent = "Photo upload failed.";
    }
  }, "image/jpeg", 0.9);
}

uploadImageFileButton?.addEventListener("click", uploadSelectedFile);
startEditPhotoCameraButton?.addEventListener("click", startEditPhotoCamera);
captureEditPhotoButton?.addEventListener("click", captureEditPhoto);
stopEditPhotoCameraButton?.addEventListener("click", () => stopEditPhotoCamera(true));
window.addEventListener("beforeunload", () => stopEditPhotoCamera(false));
