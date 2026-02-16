document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("productSearch");
  const grid = document.getElementById("productGrid");

  if (!input || !grid) return;

  const items = grid.querySelectorAll(".product-block");

  const normalize = (str) =>
    (str || "").toString().trim().toLowerCase();

  input.addEventListener("input", () => {
    const query = normalize(input.value);

    items.forEach((item) => {
      const barcode = normalize(item.dataset.barcode);
      const name = normalize(item.dataset.name);

      const match =
        query === "" ||
        barcode.includes(query) ||
        name.includes(query);

      item.style.display = match ? "" : "none";
    });
  });
});