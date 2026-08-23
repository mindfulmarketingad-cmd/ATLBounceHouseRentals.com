(function () {
  const grid = document.getElementById("products-grid");
  if (!grid) return;

  const searchInput = document.getElementById("products-search-input");
  const catLinks = Array.from(document.querySelectorAll("button.products-cat-link"));
  const sortSelect = document.getElementById("products-sort-select");
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
    countEl.textContent = (visible === cards.length ? cards.length : visible + " of " + cards.length) + " Product" + (cards.length === 1 ? "" : "s");
    emptyEl.hidden = visible !== 0;
    grid.hidden = visible === 0;
  }

  function applySort() {
    const mode = sortSelect ? sortSelect.value : "name-asc";
    const sorted = cards.slice().sort(function (a, b) {
      if (mode === "price-asc") return parseFloat(a.dataset.price) - parseFloat(b.dataset.price);
      if (mode === "price-desc") return parseFloat(b.dataset.price) - parseFloat(a.dataset.price);
      return a.dataset.name.localeCompare(b.dataset.name);
    });
    sorted.forEach(function (card) { grid.appendChild(card); });
  }

  searchInput.addEventListener("input", applyFilters);

  catLinks.forEach(function (link) {
    link.addEventListener("click", function () {
      activeCategory = link.dataset.categoryFilter || "";
      catLinks.forEach(function (c) { c.classList.toggle("active", c === link); });
      applyFilters();
    });
  });

  if (sortSelect) sortSelect.addEventListener("change", applySort);

  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      searchInput.value = "";
      activeCategory = "";
      catLinks.forEach(function (c) { c.classList.toggle("active", c.dataset.categoryFilter === ""); });
      applyFilters();
    });
  }

  applyFilters();
})();
