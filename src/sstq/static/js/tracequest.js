document.addEventListener("DOMContentLoaded", () => {
  const categorySelect = document.getElementById("mission_category");
  const difficultySelect = document.getElementById("difficulty");
  const categoryCards = document.querySelectorAll("[data-category-card]");
  const difficultyCards = document.querySelectorAll("[data-difficulty-card]");

  const updateSelectedState = (nodes, attribute, selectedValue) => {
    nodes.forEach((node) => {
      node.classList.toggle("selected", node.dataset[attribute] === selectedValue);
    });
  };

  categorySelect?.addEventListener("change", () => {
    updateSelectedState(categoryCards, "categoryCard", categorySelect.value);
  });

  categoryCards.forEach((card) => {
    card.addEventListener("click", () => {
      if (!categorySelect) return;
      categorySelect.value = card.dataset.categoryCard || "";
      updateSelectedState(categoryCards, "categoryCard", categorySelect.value);
    });
  });

  difficultyCards.forEach((card) => {
    card.addEventListener("click", () => {
      if (!difficultySelect) return;
      difficultySelect.value = card.dataset.difficultyCard || "";
      updateSelectedState(difficultyCards, "difficultyCard", difficultySelect.value);
    });
  });
});
