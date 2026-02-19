import {
  BrowserMultiFormatReader,
  NotFoundException,
} from "https://cdn.jsdelivr.net/npm/@zxing/library@0.21.2/+esm";

const barcodeForm = document.getElementById("barcode-form");
const barcodeInput = document.getElementById("barcode");
const detailsForm = document.getElementById("details-form");
const productDetailsForm = document.getElementById("productDetailsForm");
const errorText = document.getElementById("error");

const startButton = document.getElementById("start-scan");
const stopButton = document.getElementById("stop-scan");
const video = document.getElementById("preview");
const statusText = document.getElementById("status");
const detectedText = document.getElementById("detected");
const imageUrlInput = document.getElementById("image_url");

const photoStartButton = document.getElementById("start-photo-camera");
const photoCaptureButton = document.getElementById("capture-photo");
const photoStopButton = document.getElementById("stop-photo-camera");
const photoVideo = document.getElementById("photo-preview");
const imageStatus = document.getElementById("image-status");
const capturedImage = document.getElementById("captured-image");

const reader = new BrowserMultiFormatReader();
let controls = null;
let photoStream = null;

function normalizeBarcode(text) {
  const digits = String(text || "").replace(/\D/g, "");
  if (digits.length === 12) {
    return `0${digits}`;
  }
  return digits || String(text || "");
}

function releaseCamera() {
  const stream = video?.srcObject;
  if (stream instanceof MediaStream) {
    stream.getTracks().forEach((track) => track.stop());
  }
  if (video) {
    video.srcObject = null;
  }
}

function stopScanning(updateStatus = true) {
  try {
    controls?.stop?.();
  } catch (error) {
    // Ignore.
  }
  controls = null;

  try {
    reader.reset();
  } catch (error) {
    // Ignore.
  }

  releaseCamera();

  if (updateStatus && statusText) {
    statusText.textContent = "Scanner stopped.";
  }
}

function stopPhotoCamera(updateStatus = true) {
  if (photoStream instanceof MediaStream) {
    photoStream.getTracks().forEach((track) => track.stop());
  }
  photoStream = null;

  if (photoVideo) {
    photoVideo.srcObject = null;
  }

  if (updateStatus && imageStatus) {
    imageStatus.textContent = "Photo camera closed.";
  }
}

async function validateBarcode(barcode) {
  const res = await fetch("/validate_barcode", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ barcode }),
  });
  return res.json();
}

async function handleBarcodeSubmit(event) {
  event.preventDefault();

  const barcode = barcodeInput?.value.trim() || "";
  const barcodeValid = await validateBarcode(barcode);

  if (!barcodeValid.valid) {
    if (errorText) {
      errorText.innerText = barcodeValid.message;
      errorText.hidden = false;
    }
    return;
  }

  if (errorText) {
    errorText.hidden = true;
  }
  if (barcodeForm) {
    barcodeForm.hidden = true;
  }
  if (detailsForm) {
    detailsForm.hidden = false;
  }
}

async function startScanning() {
  if (!video || !statusText) {
    return;
  }

  if (controls) {
    stopScanning(false);
  }

  if (!navigator.mediaDevices?.getUserMedia) {
    statusText.textContent =
      "Camera not available here. Use HTTPS (tunnel) or localhost.";
    return;
  }

  if (detectedText) {
    detectedText.textContent = "";
  }
  statusText.textContent = "Starting camera...";

  const onDecode = (result, error) => {
    if (result) {
      const barcode = normalizeBarcode(result.getText());
      if (detectedText) {
        detectedText.textContent = `Detected: ${barcode}`;
      }
      statusText.textContent = "Detected. Filling barcode...";

      stopScanning(false);
      if (barcodeInput) {
        barcodeInput.value = barcode;
      }
      if (barcodeForm) {
        if (typeof barcodeForm.requestSubmit === "function") {
          barcodeForm.requestSubmit();
        } else {
          barcodeForm.dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true }),
          );
        }
      }
      return;
    }

    if (error && !(error instanceof NotFoundException)) {
      // Keep scanning.
    }
  };

  try {
    controls = await reader.decodeFromConstraints(
      { audio: false, video: { facingMode: { ideal: "environment" } } },
      video,
      onDecode,
    );
    statusText.textContent = "Scanning...";
  } catch (error) {
    try {
      controls = await reader.decodeFromVideoDevice(undefined, video, onDecode);
      statusText.textContent = "Scanning...";
    } catch (error2) {
      stopScanning(false);
      statusText.textContent = `Could not start camera: ${error2?.name || error2}`;
    }
  }
}

async function startPhotoCamera() {
  if (!photoVideo || !imageStatus) {
    return;
  }

  stopPhotoCamera(false);

  if (!navigator.mediaDevices?.getUserMedia) {
    imageStatus.textContent =
      "Camera not available here. Use HTTPS (tunnel) or localhost.";
    return;
  }

  try {
    photoStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" } },
      audio: false,
    });
    photoVideo.srcObject = photoStream;
    imageStatus.textContent = "Photo camera ready.";
  } catch (error) {
    imageStatus.textContent = `Could not open photo camera: ${error?.name || error}`;
  }
}

async function uploadCapturedPhoto(blob) {
  const barcode = barcodeInput?.value.trim() || "";
  const formData = new FormData();
  formData.append("image", blob, "product-photo.jpg");
  formData.append("barcode", barcode);

  const response = await fetch("/upload_product_image", {
    method: "POST",
    body: formData,
  });

  return response.json();
}

async function capturePhoto() {
  if (!photoVideo || !imageStatus) {
    return;
  }

  if (!(photoStream instanceof MediaStream)) {
    imageStatus.textContent = "Open the photo camera first.";
    return;
  }

  const width = photoVideo.videoWidth;
  const height = photoVideo.videoHeight;

  if (!width || !height) {
    imageStatus.textContent = "Camera is not ready yet. Try again.";
    return;
  }

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) {
    imageStatus.textContent = "Could not capture photo.";
    return;
  }

  context.drawImage(photoVideo, 0, 0, width, height);

  imageStatus.textContent = "Uploading photo...";
  canvas.toBlob(
    async (blob) => {
      if (!blob) {
        imageStatus.textContent = "Could not create image file.";
        return;
      }

      try {
        const data = await uploadCapturedPhoto(blob);
        if (!data.success) {
          imageStatus.textContent = data.message || "Photo upload failed.";
          return;
        }

        if (imageUrlInput) {
          imageUrlInput.value = data.image_url;
        }
        if (capturedImage) {
          capturedImage.src = data.image_url;
          capturedImage.hidden = false;
        }
        imageStatus.textContent = "Photo uploaded successfully.";
      } catch (error) {
        imageStatus.textContent = "Photo upload failed.";
      }
    },
    "image/jpeg",
    0.9,
  );
}

barcodeForm?.addEventListener("submit", handleBarcodeSubmit);

productDetailsForm?.addEventListener("submit", (event) => {
  event.preventDefault();

  const productData = {
    barcode: barcodeInput?.value.trim() || "",
    name: document.getElementById("name")?.value.trim() || "",
    category: document.getElementById("category")?.value.trim() || "",
    brand: document.getElementById("brand")?.value.trim() || "",
    description: document.getElementById("Description")?.value.trim() || "",
    image: imageUrlInput?.value.trim() || "",
  };

  fetch("/add_product", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ productData }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        window.location.href = `/product/${data.barcode}`;
      } else {
        console.error("Error:", data.message);
      }
    });
});

startButton?.addEventListener("click", startScanning);
stopButton?.addEventListener("click", () => stopScanning(true));
photoStartButton?.addEventListener("click", startPhotoCamera);
photoCaptureButton?.addEventListener("click", capturePhoto);
photoStopButton?.addEventListener("click", () => stopPhotoCamera(true));
window.addEventListener("beforeunload", () => {
  stopScanning(false);
  stopPhotoCamera(false);
});
