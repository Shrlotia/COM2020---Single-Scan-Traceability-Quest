const barcodeForm = document.getElementById("barcode-form");
const barcodeInput = document.getElementById("barcode");
const detailsForm = document.getElementById("details-form");
const productDetailsForm = document.getElementById("productDetailsForm");
const errorText = document.getElementById("error");
const imageUrlInput = document.getElementById("image_url");

const photoStartButton = document.getElementById("start-photo-camera");
const photoCaptureButton = document.getElementById("capture-photo");
const photoStopButton = document.getElementById("stop-photo-camera");
const photoVideo = document.getElementById("photo-preview");
const imageStatus = document.getElementById("image-status");
const capturedImage = document.getElementById("captured-image");

let photoStream = null;

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

async function startPhotoCamera() {
    if (!photoVideo || !imageStatus) {
        return;
    }

    stopPhotoCamera(false);

    if (!navigator.mediaDevices?.getUserMedia) {
        imageStatus.textContent = "Camera not available here. Use HTTPS (tunnel) or localhost.";
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
    canvas.toBlob(async (blob) => {
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
    }, "image/jpeg", 0.9);
}

barcodeForm?.addEventListener("submit", handleBarcodeSubmit);

if (barcodeInput?.value.trim() && barcodeForm) {
    window.addEventListener("load", () => {
        barcodeForm.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });
}

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

photoStartButton?.addEventListener("click", startPhotoCamera);
photoCaptureButton?.addEventListener("click", capturePhoto);
photoStopButton?.addEventListener("click", () => stopPhotoCamera(true));
window.addEventListener("beforeunload", () => {
    stopPhotoCamera(false);
});
