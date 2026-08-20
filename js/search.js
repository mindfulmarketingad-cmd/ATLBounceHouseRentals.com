/* Atlanta Bounce House Rentals — header search bar.
   Vanilla JS, no dependencies. Matches against window.ABHR_SEARCH_INDEX
   (js/search-index.js, generated at build time from every page's <title>)
   entirely client-side — no network request, works instantly.
*/
(function () {
  "use strict";

  function esc(str) {
    return String(str || "").replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function init() {
    var wrap = document.getElementById("header-search");
    var input = document.getElementById("site-search-input");
    var results = document.getElementById("site-search-results");
    if (!wrap || !input || !results) return;
    var index = window.ABHR_SEARCH_INDEX || [];

    function search(q) {
      var terms = q.toLowerCase().trim().split(/\s+/).filter(Boolean);
      if (!terms.length) return [];
      var scored = [];
      for (var i = 0; i < index.length; i++) {
        var p = index[i];
        var hay = (p.t + " " + p.u).toLowerCase();
        if (!terms.every(function (t) { return hay.indexOf(t) >= 0; })) continue;
        var score = p.t.toLowerCase().indexOf(terms[0]) === 0 ? 0 : 1;
        scored.push({ p: p, score: score });
      }
      scored.sort(function (a, b) { return a.score - b.score; });
      return scored.map(function (s) { return s.p; });
    }

    function render(matches, q) {
      if (!q) { results.hidden = true; results.innerHTML = ""; return; }
      if (!matches.length) {
        results.innerHTML = '<div class="header-search-empty">No pages match &ldquo;' + esc(q) + '&rdquo;.</div>';
      } else {
        results.innerHTML = matches.slice(0, 12).map(function (m) {
          return '<a href="' + esc(m.u) + '">' + esc(m.t) + '</a>';
        }).join("");
      }
      results.hidden = false;
    }

    var timer;
    input.addEventListener("input", function () {
      clearTimeout(timer);
      var q = input.value;
      timer = setTimeout(function () { render(search(q), q.trim()); }, 100);
    });
    input.addEventListener("focus", function () {
      if (input.value.trim()) render(search(input.value), input.value.trim());
    });
    document.addEventListener("click", function (e) {
      if (!wrap.contains(e.target)) results.hidden = true;
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { results.hidden = true; input.blur(); }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
