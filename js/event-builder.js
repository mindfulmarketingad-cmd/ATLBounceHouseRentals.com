(function () {
  "use strict";

  var wrap = document.getElementById("eb-wrap");
  if (!wrap) return;

  var TOTAL_STEPS = 5;
  var state = { eventType: null, guestCount: null, setting: null, style: null, needs: [] };

  var progressBar = document.getElementById("eb-progress-bar");
  var stepLabel = document.getElementById("eb-step-label");
  var backBtn = document.getElementById("eb-back");
  var seeResultsBtn = document.getElementById("eb-see-results");
  var resultsEl = document.getElementById("eb-results");
  var resultsGrid = document.getElementById("eb-results-grid");
  var resultsSummary = document.getElementById("eb-results-summary");
  var resultsEmpty = document.getElementById("eb-results-empty");
  var startOverBtn = document.getElementById("eb-start-over");

  var steps = Array.from(wrap.querySelectorAll("[data-eb-step]"));
  var currentStep = 1;

  function money(n) {
    return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function showStep(n) {
    currentStep = n;
    steps.forEach(function (el) {
      el.hidden = parseInt(el.dataset.ebStep, 10) !== n;
    });
    progressBar.style.width = (n / TOTAL_STEPS * 100) + "%";
    stepLabel.textContent = "Question " + n + " of " + TOTAL_STEPS;
    backBtn.hidden = n === 1;
  }

  function fieldForStep(n) {
    var q = wrap.querySelector('[data-eb-step="' + n + '"] [data-eb-field]');
    return q ? q.dataset.ebField : null;
  }

  wrap.addEventListener("click", function (e) {
    var opt = e.target.closest(".eb-option");
    if (!opt) return;
    var group = opt.closest("[data-eb-field]");
    var field = group.dataset.ebField;
    var value = opt.dataset.value;
    var isMulti = group.classList.contains("eb-options-multi");

    if (isMulti) {
      opt.classList.toggle("selected");
      var idx = state.needs.indexOf(value);
      if (opt.classList.contains("selected") && idx === -1) state.needs.push(value);
      if (!opt.classList.contains("selected") && idx !== -1) state.needs.splice(idx, 1);
      return;
    }

    group.querySelectorAll(".eb-option").forEach(function (b) { b.classList.remove("selected"); });
    opt.classList.add("selected");
    state[field] = value;

    if (currentStep < TOTAL_STEPS) {
      setTimeout(function () { showStep(currentStep + 1); }, 150);
    }
  });

  backBtn.addEventListener("click", function () {
    if (currentStep > 1) showStep(currentStep - 1);
  });

  // ─── Recommendation engine ──────────────────────────────────────────────
  function pickFromParent(parentSlug, limit, filterFn) {
    var products = (window.ABHR_PRODUCTS || []).filter(function (p) { return p.parent_slug === parentSlug; });
    if (filterFn) {
      var filtered = products.filter(filterFn);
      if (filtered.length) products = filtered;
    }
    return products.slice(0, limit);
  }

  function buildRecommendations() {
    var picks = [];
    var isKids = state.eventType === "kids-party";
    var wantsBar = state.needs.indexOf("bar") !== -1;
    var wantsTables = state.needs.indexOf("tables") !== -1;
    var wantsTent = state.needs.indexOf("tent") !== -1 || state.setting === "outdoor" || state.setting === "both";
    var wantsAv = state.needs.indexOf("av") !== -1 || state.eventType === "corporate";
    var wantsDecor = state.needs.indexOf("decor") !== -1 || state.eventType === "wedding";

    // Seating — always recommended, driven by style (and kids-party override)
    if (isKids) {
      picks = picks.concat(pickFromParent("chiavari-chair-rentals", 2, function (p) { return p.slug.indexOf("child") !== -1; }));
      if (!picks.length) picks = picks.concat(pickFromParent("chair-rentals", 2));
    } else if (state.style === "classic") {
      picks = picks.concat(pickFromParent("chiavari-chair-rentals", 3, function (p) { return p.slug.indexOf("child") === -1; }));
    } else if (state.style === "modern") {
      picks = picks.concat(pickFromParent("ghost-chair-rentals", 2));
      if (wantsBar) picks = picks.concat(pickFromParent("chair-rentals", 1, function (p) { return p.slug.indexOf("ghost") !== -1; }));
    } else {
      picks = picks.concat(pickFromParent("chair-rentals", 3, function (p) { return p.slug.indexOf("resin") !== -1 || p.slug.indexOf("plastic") !== -1; }));
    }

    if (wantsTables) {
      picks = picks.concat(pickFromParent("table-rentals", 2));
    }
    if (wantsTent) {
      picks = picks.concat(pickFromParent("tent-rentals", 2));
    }
    if (wantsBar) {
      picks = picks.concat(pickFromParent("portable-bar-rentals", 1));
      picks = picks.concat(pickFromParent("bar-beverage-equipment-rentals", 1));
    }
    if (wantsAv) {
      picks = picks.concat(pickFromParent("audio-visual-equipment-rentals", 2));
    }
    if (wantsDecor) {
      picks = picks.concat(pickFromParent("wedding-equipment-rentals", 1));
    }

    // De-dupe by slug, cap at 9 cards
    var seen = {};
    picks = picks.filter(function (p) {
      if (seen[p.slug]) return false;
      seen[p.slug] = true;
      return true;
    }).slice(0, 9);

    return picks;
  }

  function cardHtml(p) {
    var media = p.image
      ? '<img src="' + p.image + '" alt="' + p.image_alt + '" width="' + p.image_w + '" height="' + p.image_h + '" loading="lazy">'
      : '<div class="prod-card-placeholder" role="img" aria-label="' + p.name + ' photo coming soon">' + p.short_name + '</div>';
    return (
      '<div class="prod-card" data-product-item data-name="' + p.name.toLowerCase() + '" data-category="' + p.category +
      '" data-parent="' + p.parent_name.toLowerCase() + '" data-price="' + p.price.toFixed(2) +
      '" data-slug="' + p.slug + '" data-href="' + p.href + '" data-unit="' + p.unit + '" data-min-qty="' + p.min_qty + '">' +
      '<a class="prod-card-media-link" href="' + p.href + '">' + media + '</a>' +
      '<div class="prod-card-body">' +
      '<p class="prod-card-category muted">' + p.category + '</p>' +
      '<h3><a href="' + p.href + '">' + p.name + '</a></h3>' +
      '<p class="prod-card-price"><span class="prod-was-price">' + money(p.price * 2) + '</span> <strong>' + money(p.price) + '</strong> <span class="muted">per ' + p.unit + '</span></p>' +
      '<p class="muted">' + p.includes + '</p>' +
      '<div class="prod-card-actions">' +
      '<a class="prod-card-cta" href="' + p.href + '">Pick your quantity &rsaquo;</a>' +
      '<button type="button" class="btn btn-outline btn-sm" data-add-to-cart>Add to Cart</button>' +
      '</div></div></div>'
    );
  }

  function showResults() {
    var picks = buildRecommendations();
    wrap.hidden = true;
    resultsEl.hidden = false;

    var guestWord = state.guestCount ? "around " + state.guestCount + " guests" : "your event";
    resultsSummary.textContent = "Based on a " + (state.eventType || "").replace("-", " ") + " for " + guestWord + ", here's what we'd recommend from our own catalog.";

    if (!picks.length) {
      resultsGrid.hidden = true;
      resultsEmpty.hidden = false;
      return;
    }
    resultsGrid.hidden = false;
    resultsEmpty.hidden = true;
    resultsGrid.innerHTML = picks.map(cardHtml).join("");

    if (window.ABHR_trackEvent) {
      window.ABHR_trackEvent("search", { query: "event_builder:" + state.eventType + ":" + state.style });
    }
  }

  seeResultsBtn.addEventListener("click", showResults);

  startOverBtn.addEventListener("click", function () {
    state = { eventType: null, guestCount: null, setting: null, style: null, needs: [] };
    wrap.querySelectorAll(".eb-option").forEach(function (b) { b.classList.remove("selected"); });
    resultsEl.hidden = true;
    wrap.hidden = false;
    showStep(1);
    wrap.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  showStep(1);
})();
