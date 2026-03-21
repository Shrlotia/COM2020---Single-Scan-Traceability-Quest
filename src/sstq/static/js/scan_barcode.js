import { BrowserMultiFormatReader } from "@zxing/browser";

const startButton = document.getElementById("start-scan");
const video = document.getElementById("preview");
const statusText = document.getElementById("status");
const scanConfig = document.getElementById("scan-config");

const reader = new BrowserMultiFormatReader();

let controls = null;

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

function returnBarcode(barcode) {
    const returnUrl = scanConfig?.dataset.returnUrl;
    if (!returnUrl) {
        return;
    }

    const separator = returnUrl.includes("?") ? "&" : "?";
    window.location.href = `${returnUrl}${separator}barcode=${encodeURIComponent(barcode)}`;
}

function needsUserGesture() {
    return window.matchMedia("(pointer: coarse)").matches || navigator.maxTouchPoints > 0;
}

async function startScanning() {
    if (!video || !statusText) {
        return;
    }

    if (startButton) {
        startButton.hidden = true;
    }

    if (controls) {
        stopScanning(false);
    }

    if (!navigator.mediaDevices?.getUserMedia) {
        statusText.textContent = "Camera not available here. Use HTTPS (tunnel) or localhost.";
        return;
    }

    statusText.textContent = "Starting camera...";

    const onDecode = (result) => {
        if (!result) {
            return;
        }

        const barcode = normalizeBarcode(result.getText());
        statusText.textContent = "Detected. Returning barcode...";

        stopScanning(false);
        window.setTimeout(() => returnBarcode(barcode), 250);
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
        } catch (fallbackError) {
            stopScanning(false);
            if (startButton) {
                startButton.hidden = false;
            }
            statusText.textContent = `Could not start camera: ${fallbackError?.name || fallbackError}`;
        }
    }
}

window.addEventListener("load", () => {
    if (needsUserGesture()) {
        statusText.textContent = "Tap to start the camera.";
        return;
    }

    if (startButton) {
        startButton.hidden = true;
    }
    startScanning();
});
startButton?.addEventListener("click", () => startScanning());
window.addEventListener("beforeunload", () => stopScanning(false));
