document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("productSearch");
  const grid = document.getElementById("productGrid");
  const categoryFilter = document.getElementById("categoryFilter");
  const sortProducts = document.getElementById("sortProducts");

  if (!input || !grid || !categoryFilter || !sortProducts) return;

  const items = Array.from(grid.querySelectorAll(".product-block"));
  const images = grid.querySelectorAll(".product-thumb");

  const normalize = (str) =>
    (str || "").toString().trim().toLowerCase();

  const matchesCategory = (item, selectedCategory) => {
    if (!selectedCategory) return true;

    const categories = item.dataset.category
      .split(",")
      .map((category) => normalize(category));

    return categories.includes(normalize(selectedCategory));
  };

  const compareValues = (left, right, direction = "asc") => {
    const result = left.localeCompare(right, undefined, { numeric: true, sensitivity: "base" });
    return direction === "desc" ? -result : result;
  };

  const applyFiltersAndSort = () => {
    const query = normalize(input.value);
    const selectedCategory = categoryFilter.value;
    const [sortKey, direction] = sortProducts.value.split("-");

    items.forEach((item) => {
      const barcode = normalize(item.dataset.barcode);
      const name = normalize(item.dataset.name);
      const category = normalize(item.dataset.category);

      const matchSearch =
        query === "" ||
        barcode.includes(query) ||
        name.includes(query) ||
        category.includes(query);

      const matchCategory = matchesCategory(item, selectedCategory);
      item.style.display = matchSearch && matchCategory ? "" : "none";
    });

    items
      .slice()
      .sort((leftItem, rightItem) => {
        const leftValue = normalize(leftItem.dataset[sortKey]);
        const rightValue = normalize(rightItem.dataset[sortKey]);
        return compareValues(leftValue, rightValue, direction);
      })
      .forEach((item) => {
        grid.appendChild(item);
      });
  };

  images.forEach((image) => {
    image.addEventListener("error", () => {
      image.hidden = true;
      const fallback = image.parentElement?.querySelector(".product-thumb-fallback");
      if (fallback) fallback.hidden = false;
    });
  });

  input.addEventListener("input", applyFiltersAndSort);
  categoryFilter.addEventListener("change", applyFiltersAndSort);
  sortProducts.addEventListener("change", applyFiltersAndSort);

  applyFiltersAndSort();
});
