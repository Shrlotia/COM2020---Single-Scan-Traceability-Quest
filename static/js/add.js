import { BrowserMultiFormatReader, NotFoundException } from "https://cdn.jsdelivr.net/npm/@zxing/library@0.21.2/+esm";

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
        statusText.textContent = "Camera not available here. Use HTTPS (tunnel) or localhost.";
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
                    barcodeForm.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
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

barcodeForm?.addEventListener("submit", handleBarcodeSubmit);

productDetailsForm?.addEventListener("submit", (event) => {
    event.preventDefault();

    const productData = {
        barcode: barcodeInput?.value.trim() || "",
        name: document.getElementById("name")?.value.trim() || "",
        category: document.getElementById("category")?.value.trim() || "",
        brand: document.getElementById("brand")?.value.trim() || "",
        Description: document.getElementById("Description")?.value.trim() || "",
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
window.addEventListener("beforeunload", () => stopScanning(false));
