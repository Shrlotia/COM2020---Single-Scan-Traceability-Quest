document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("productSearch");
  const resetFilters = document.getElementById("resetFilters");
  const filtersForm = document.getElementById("productFiltersForm");
  const grid = document.getElementById("productGrid");
  const categoryFilter = document.getElementById("categoryFilter");
  const sortProducts = document.getElementById("sortProducts");
  const compareForm = document.getElementById("compareForm");
  const compareDock = document.getElementById("compareDock");
  const compareCancel = document.getElementById("compareCancel");
  const compareConfirm = document.getElementById("compareConfirm");
  const compareIds = document.getElementById("compareIds");
  const compareSelectionText = document.getElementById("compareSelectionText");

  if (
    !input ||
    !resetFilters ||
    !filtersForm ||
    !grid ||
    !categoryFilter ||
    !sortProducts ||
    !compareForm ||
    !compareDock ||
    !compareCancel ||
    !compareConfirm ||
    !compareIds ||
    !compareSelectionText
  ) return;

  const items = Array.from(grid.querySelectorAll(".product-block"));
  const images = grid.querySelectorAll(".product-thumb");
  const checkboxes = Array.from(grid.querySelectorAll(".compare-checkbox"));
  const compareLabels = Array.from(grid.querySelectorAll(".compare-select"));
  const detailLinks = Array.from(grid.querySelectorAll(".product-main-link"));
  let compareMode = false;

  const selectedCheckboxes = () =>
    checkboxes.filter((checkbox) => checkbox.checked);

  const syncCompareState = () => {
    const selected = selectedCheckboxes();
    const selectedIds = selected.map((checkbox) => checkbox.value);
    const remaining = Math.max(0, 2 - selected.length);

    if (compareMode && selected.length === 0) {
      setCompareMode(false);
      return;
    }

    compareIds.value = selectedIds.join(",");
    compareConfirm.disabled = selected.length !== 2;
    compareSelectionText.textContent =
      selected.length === 2 ? "2 products selected" : `Select ${remaining} more product${remaining === 1 ? "" : "s"}`;

    checkboxes.forEach((checkbox) => {
      checkbox.disabled = !compareMode || (!checkbox.checked && selected.length >= 2);
    });
  };

  const setCompareMode = (enabled) => {
    compareMode = enabled;
    compareDock.hidden = !enabled;

    if (!enabled) {
      checkboxes.forEach((checkbox) => {
        checkbox.checked = false;
      });
      compareIds.value = "";
    }

    syncCompareState();
  };

  images.forEach((image) => {
    image.addEventListener("error", () => {
      image.hidden = true;
      const fallback = image.parentElement?.querySelector(".product-thumb-fallback");
      if (fallback) fallback.hidden = false;
    });
  });

  checkboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", syncCompareState);
  });

  compareLabels.forEach((label, index) => {
    label.addEventListener("click", (event) => {
      if (compareMode) return;

      event.preventDefault();
      event.stopPropagation();
      const checkbox = checkboxes[index];
      if (checkbox && !checkbox.checked) {
        checkbox.checked = true;
      }
      setCompareMode(true);
    });
  });

  detailLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      if (compareMode) {
        event.preventDefault();
      }
    });
  });

  compareCancel.addEventListener("click", () => {
    setCompareMode(false);
  });

  compareForm.addEventListener("submit", (event) => {
    if (selectedCheckboxes().length !== 2) {
      event.preventDefault();
    }
  });

  resetFilters.addEventListener("click", () => {
    window.location.href = filtersForm.action;
  });

  categoryFilter.addEventListener("change", () => {
    filtersForm.requestSubmit();
  });

  sortProducts.addEventListener("change", () => {
    filtersForm.requestSubmit();
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      filtersForm.requestSubmit();
    }
  });

  setCompareMode(false);
});
