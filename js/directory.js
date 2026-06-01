/* Provider directory search + filtering.
   Powers the homepage hero search, the in-table search box, and the
   service chips. All filter the same #provider-table by a data-search attr. */
(function () {
  "use strict";
  var table = document.getElementById("provider-table");
  if (!table) return;
  var rows = [].slice.call(table.querySelectorAll("tbody tr[data-search]"));
  var noResults = document.getElementById("no-results");

  function applyFilter(q) {
    q = (q || "").toLowerCase().trim();
    var n = 0;
    rows.forEach(function (r) {
      var match = !q || r.getAttribute("data-search").indexOf(q) > -1;
      r.style.display = match ? "" : "none";
      if (match) n++;
    });
    if (noResults) noResults.style.display = n === 0 ? "" : "none";
    document.querySelectorAll("[id$='-count']").forEach(function (c) {
      c.textContent = n + " provider" + (n === 1 ? "" : "s");
    });
    return n;
  }

  // In-table / partners-page search box
  var dirSearch = document.getElementById("dir-search");
  if (dirSearch) dirSearch.addEventListener("input", function () { applyFilter(this.value); });

  // Homepage hero search
  var heroInput = document.getElementById("hero-search-input");
  var heroBtn = document.getElementById("hero-search-btn");
  function runHero() {
    applyFilter(heroInput ? heroInput.value : "");
    if (dirSearch && heroInput) dirSearch.value = heroInput.value;
    var providers = document.getElementById("providers");
    if (providers) providers.scrollIntoView({ behavior: "smooth" });
  }
  if (heroInput) {
    heroInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); runHero(); }
    });
  }
  if (heroBtn) heroBtn.addEventListener("click", function (e) { e.preventDefault(); runHero(); });

  // Service quick-search chips
  document.querySelectorAll(".hero-search .chips button[data-q]").forEach(function (b) {
    b.addEventListener("click", function () {
      var q = this.getAttribute("data-q");
      if (heroInput) heroInput.value = q;
      runHero();
    });
  });
})();
