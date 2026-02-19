import {
  BrowserMultiFormatReader,
  NotFoundException,
} from "https://cdn.jsdelivr.net/npm/@zxing/library@0.21.2/+esm";

const startButton = document.getElementById("start-scan");
const stopButton = document.getElementById("stop-scan");
const video = document.getElementById("preview");
const statusText = document.getElementById("status");
const detectedText = document.getElementById("detected");
const barcodeInput = document.getElementById("barcode");
const barcodeForm = document.getElementById("barcode-form");

const reader = new BrowserMultiFormatReader();

let controls = null;

function normalizeBarcode(text) {
  const digits = String(text || "").replace(/\D/g, "");

  // If ZXing returns UPC-A (12 digits), normalize it to EAN-13 by adding a leading 0.
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

async function startScanning() {
  if (!video || !statusText) {
    return;
  }

  // If already running, reset first.
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
      statusText.textContent = "Detected. Submitting barcode...";

      stopScanning(false);
      if (barcodeInput) {
        barcodeInput.value = barcode;
      }
      if (barcodeForm) {
        if (typeof barcodeForm.requestSubmit === "function") {
          barcodeForm.requestSubmit();
        } else {
          barcodeForm.submit();
        }
      }
      return;
    }

    // NotFoundException just means "no barcode in this frame".
    if (error && !(error instanceof NotFoundException)) {
      // Keep it quiet; just keep scanning.
    }
  };

  try {
    // Prefer the back camera if available, but keep constraints minimal.
    controls = await reader.decodeFromConstraints(
      { audio: false, video: { facingMode: { ideal: "environment" } } },
      video,
      onDecode,
    );
    statusText.textContent = "Scanning...";
  } catch (error) {
    try {
      // Fallback: let the browser pick any camera.
      controls = await reader.decodeFromVideoDevice(undefined, video, onDecode);
      statusText.textContent = "Scanning...";
    } catch (error2) {
      stopScanning(false);
      statusText.textContent = `Could not start camera: ${error2?.name || error2}`;
    }
  }
}

startButton?.addEventListener("click", startScanning);
stopButton?.addEventListener("click", () => stopScanning(true));
window.addEventListener("beforeunload", () => stopScanning(false));
