const startButton = document.getElementById("start-picture-camera");
const captureButton = document.getElementById("capture-picture");
const cancelButton = document.getElementById("cancel-picture");
const video = document.getElementById("picture-preview");
const statusText = document.getElementById("picture-status");
const config = document.getElementById("picture-config");

let stream = null;

function stopCamera(updateStatus = true) {
  if (stream instanceof MediaStream) {
    stream.getTracks().forEach((track) => track.stop());
  }
  stream = null;

  if (video) {
    video.srcObject = null;
  }

  if (updateStatus && statusText) {
    statusText.textContent = "Camera stopped.";
  }
}

function returnToEditor(tempImageUrl = "") {
  const returnUrl = config?.dataset.returnUrl;
  if (!returnUrl) return;

  const separator = returnUrl.includes("?") ? "&" : "?";
  const nextUrl = tempImageUrl
    ? `${returnUrl}${separator}temp_image=${encodeURIComponent(tempImageUrl)}`
    : returnUrl;
  window.location.href = nextUrl;
}

async function uploadTempImage(blob) {
  const barcode = config?.dataset.barcode || "";
  const formData = new FormData();
  formData.append("image", blob, "product-photo.jpg");
  formData.append("barcode", barcode);

  const response = await fetch("/upload_product_image_temp", {
    method: "POST",
    body: formData,
  });
  return response.json();
}

async function startCamera() {
  if (!navigator.mediaDevices?.getUserMedia || !video || !statusText) {
    return;
  }

  stopCamera(false);
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" } },
      audio: false,
    });
    video.srcObject = stream;
    statusText.textContent = "Camera ready.";
    if (startButton) startButton.hidden = true;
  } catch (error) {
    statusText.textContent = `Could not open camera: ${error?.name || error}`;
  }
}

function capturePicture() {
  if (!(stream instanceof MediaStream) || !video || !statusText) {
    statusText.textContent = "Open the camera first.";
    return;
  }

  const width = video.videoWidth;
  const height = video.videoHeight;
  if (!width || !height) {
    statusText.textContent = "Camera is not ready yet.";
    return;
  }

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) {
    statusText.textContent = "Capture failed.";
    return;
  }

  context.drawImage(video, 0, 0, width, height);
  statusText.textContent = "Uploading picture...";

  canvas.toBlob(async (blob) => {
    if (!blob) {
      statusText.textContent = "Capture failed.";
      return;
    }

    try {
      const data = await uploadTempImage(blob);
      if (!data.success) {
        statusText.textContent = data.message || "Upload failed.";
        return;
      }
      stopCamera(false);
      returnToEditor(data.image_url);
    } catch (error) {
      statusText.textContent = "Upload failed.";
    }
  }, "image/jpeg", 0.9);
}

startButton?.addEventListener("click", startCamera);
captureButton?.addEventListener("click", capturePicture);
cancelButton?.addEventListener("click", () => returnToEditor(""));
window.addEventListener("beforeunload", () => stopCamera(false));
