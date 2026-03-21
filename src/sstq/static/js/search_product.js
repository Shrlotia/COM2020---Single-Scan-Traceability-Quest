const barcodeInput = document.getElementById("barcode");
const barcodeForm = document.getElementById("barcode-form");

if (barcodeInput?.value.trim() && barcodeForm) {
    window.addEventListener("load", () => {
        if (typeof barcodeForm.requestSubmit === "function") {
            barcodeForm.requestSubmit();
        } else {
            barcodeForm.submit();
        }
    });
}
