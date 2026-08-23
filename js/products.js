(function () {
  const grid = document.getElementById("products-grid");
  if (!grid) return;

  const searchInput = document.getElementById("products-search-input");
  const chips = Array.from(document.querySelectorAll(".products-filter-chip"));
  const cards = Array.from(grid.querySelectorAll("[data-product-item]"));
  const countEl = document.getElementById("products-count");
  const emptyEl = document.getElementById("products-empty");
  const clearBtn = document.getElementById("products-clear");

  let activeCategory = "";

  function applyFilters() {
    const q = searchInput.value.trim().toLowerCase();
    let visible = 0;
    cards.forEach(function (card) {
      const matchesCategory = !activeCategory || card.dataset.category === activeCategory;
      const matchesQuery = !q ||
        card.dataset.name.includes(q) ||
        card.dataset.category.toLowerCase().includes(q) ||
        card.dataset.parent.includes(q);
      const show = matchesCategory && matchesQuery;
      card.hidden = !show;
      if (show) visible++;
    });
    countEl.textContent = visible === cards.length
      ? cards.length + " products"
      : "Showing " + visible + " of " + cards.length + " products";
    emptyEl.hidden = visible !== 0;
    grid.hidden = visible === 0;
  }

  searchInput.addEventListener("input", applyFilters);

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      activeCategory = chip.dataset.categoryFilter || "";
      chips.forEach(function (c) { c.classList.toggle("active", c === chip); });
      applyFilters();
    });
  });

  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      searchInput.value = "";
      activeCategory = "";
      chips.forEach(function (c) { c.classList.toggle("active", c.dataset.categoryFilter === ""); });
      applyFilters();
    });
  }

  applyFilters();
})();
