const productImage = document.getElementById("product-image");
const imageWrapper = document.querySelector(".product-image-wrapper");
const description = document.getElementById("description");
const toggleButton = document.getElementById("toggle-description");

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
