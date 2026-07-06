/* Atlanta Bounce House Rentals — /find/ hub live search.
   Filters the find-page link lists as you type; hides section headings
   whose lists have no matches and shows a "no results" note. */
(function () {
  "use strict";

  function init() {
    var input = document.getElementById("find-search");
    var wrap = document.getElementById("find-sections");
    if (!input || !wrap) return;

    var headings = [].slice.call(wrap.querySelectorAll("h2"));
    var lists = [].slice.call(wrap.querySelectorAll("ul"));
    var items = [].slice.call(wrap.querySelectorAll("li"));

    var empty = document.createElement("p");
    empty.className = "find-search-empty";
    empty.style.display = "none";
    empty.innerHTML = 'No matching pages. Try a different city or service, or <a href="#" data-wizard-open>request a free quote</a> and we\'ll match you with a provider.';
    wrap.appendChild(empty);

    function filter() {
      var q = input.value.trim().toLowerCase();
      var terms = q.split(/\s+/).filter(Boolean);
      var anyShown = false;

      items.forEach(function (li) {
        var text = li.textContent.toLowerCase();
        var show = terms.every(function (t) { return text.indexOf(t) >= 0; });
        li.style.display = show ? "" : "none";
        if (show) anyShown = true;
      });

      lists.forEach(function (ul, i) {
        var hasVisible = [].slice.call(ul.querySelectorAll("li")).some(function (li) {
          return li.style.display !== "none";
        });
        ul.style.display = hasVisible ? "" : "none";
        if (headings[i]) headings[i].style.display = hasVisible ? "" : "none";
      });

      empty.style.display = anyShown ? "none" : "";
    }

    input.addEventListener("input", filter);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
