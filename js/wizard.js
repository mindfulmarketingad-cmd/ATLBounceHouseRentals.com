/* Atlanta Bounce House Rentals — Multi-step Booking Wizard
   Vanilla JS, no external dependencies. Self-contained IIFE.
*/
(function () {
  "use strict";

  var SUPABASE_URL = "https://tbqigevoksabizjogvtm.supabase.co";
  var SUPABASE_ANON_KEY = "sb_publishable_aHlx0Tdu2rhOTBUp3lhkQw_Lv6Awz7a";

  // ─── Data definitions ────────────────────────────────────────────────────

  var EVENT_TYPES = [
    { value: "Birthday Party",               icon: "🎂" },
    { value: "School / Church Event",         icon: "🏫" },
    { value: "Corporate Event",               icon: "🏢" },
    { value: "Wedding / Engagement",          icon: "💍" },
    { value: "Block Party / Community Event", icon: "🏘️" },
    { value: "Other",                         icon: "📋" }
  ];

  var SERVICES_LIST = [
    { value: "Bounce Houses / Inflatables",             icon: "🏰", key: "bounce" },
    { value: "Water Slides",                            icon: "💧", key: "water" },
    { value: "Tables, Chairs & Tents",                 icon: "🪑", key: "tables" },
    { value: "Concessions (popcorn, snow cones, etc.)", icon: "🍿", key: "concessions" },
    { value: "Photo Booth",                             icon: "📸", key: "photo" },
    { value: "Silent Disco Headphones",                 icon: "🎧", key: "disco" },
    { value: "Entertainment & Staff (DJ, face painting, etc.)", icon: "🎤", key: "entertainment" },
    { value: "Other / Not Sure",                        icon: "❓", key: "other" }
  ];

  var GUEST_COUNTS = ["Under 25", "25–50", "50–100", "100–200", "200+"];

  var CHAIR_STYLES = [
    { value: "Folding Chairs",  icon: "🪑" },
    { value: "Chiavari Chairs", icon: "✨" },
    { value: "Ghost Chairs",    icon: "🔮" },
    { value: "Kids Chairs",     icon: "🧒" },
    { value: "Throne Chairs",   icon: "👑" },
    { value: "Mix / Not Sure",  icon: "❓" }
  ];

  var TENT_OPTIONS = ["Yes", "No", "Not Sure"];

  var CONCESSIONS_LIST = [
    { value: "Popcorn Machine",                icon: "🍿" },
    { value: "Snow Cone / Slushy Machine",     icon: "🧊" },
    { value: "Cotton Candy Machine",           icon: "🩷" },
    { value: "Hotdog Warmer",                  icon: "🌭" },
    { value: "Chafing Dishes (food warmers)",  icon: "🍲" },
    { value: "Full Catering Service",          icon: "🍽️" },
    { value: "Not Sure",                       icon: "❓" }
  ];

  // ─── State ────────────────────────────────────────────────────────────────

  var state = {
    currentStep: 1,
    eventType:   "",
    services:    [],
    eventDate:   "",
    zipCode:     "",
    guestCount:  "",
    chairCount:  "",
    chairStyle:  "",
    tableCount:  "",
    needsTent:   "",
    concessions: [],
    name:        "",
    phone:       "",
    email:       "",
    message:     ""
  };

  // Compute which step numbers are active based on step-2 selections
  function activeSteps() {
    var steps = [1, 2, 3];
    var hasTables = state.services.indexOf("Tables, Chairs & Tents") !== -1;
    var hasConcessions = state.services.some(function (s) {
      return s.indexOf("Concessions") === 0;
    });
    if (hasTables) steps.push(4);
    if (hasConcessions) steps.push(5);
    steps.push(6);
    return steps;
  }

  // ─── DOM helpers ──────────────────────────────────────────────────────────

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ─── Build wizard HTML shell ───────────────────────────────────────────────

  function buildShell() {
    var overlay = el("div", "wizard-overlay");
    overlay.id = "booking-wizard-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-label", "Book Your Atlanta Rental");

    overlay.innerHTML = [
      '<div class="wizard-modal">',
        '<button class="wizard-close" aria-label="Close">&times;</button>',
        '<div class="wizard-progress">',
          '<div class="wizard-steps-bar">',
            '<span class="wizard-step-dot active" data-step="1">1</span>',
            '<span class="wizard-step-dot" data-step="2">2</span>',
            '<span class="wizard-step-dot" data-step="3">3</span>',
            '<span class="wizard-step-dot" data-step="4">4</span>',
            '<span class="wizard-step-dot" data-step="5">5</span>',
            '<span class="wizard-step-dot" data-step="6">6</span>',
          '</div>',
          '<div class="wizard-step-label">Step 1 of 6</div>',
        '</div>',
        '<div class="wizard-body"></div>',
        '<div class="wizard-nav">',
          '<button class="btn btn-ghost wizard-back" style="display:none">Back</button>',
          '<button class="btn wizard-next">Next</button>',
        '</div>',
      '</div>'
    ].join("");

    document.body.appendChild(overlay);
    return overlay;
  }

  // ─── Step renderers ───────────────────────────────────────────────────────

  function renderStep1(body) {
    body.innerHTML = "";
    body.appendChild(el("h3", "", "What kind of event is this?"));
    var grid = el("div", "wizard-option-grid");
    EVENT_TYPES.forEach(function (t) {
      var card = el("div", "wizard-option" + (state.eventType === t.value ? " selected" : ""));
      card.innerHTML = '<span class="opt-icon">' + t.icon + "</span>" + esc(t.value);
      card.dataset.value = t.value;
      card.addEventListener("click", function () {
        state.eventType = t.value;
        grid.querySelectorAll(".wizard-option").forEach(function (c) {
          c.classList.remove("selected");
        });
        card.classList.add("selected");
        // Auto-advance after short delay for visual feedback
        setTimeout(function () { advance(); }, 150);
      });
      grid.appendChild(card);
    });
    body.appendChild(grid);
  }

  function renderStep2(body) {
    body.innerHTML = "";
    body.appendChild(el("h3", "", "What do you need?"));
    body.appendChild(el("p", "sub", "Select all that apply."));
    var grid = el("div", "wizard-option-grid");
    SERVICES_LIST.forEach(function (s) {
      var selected = state.services.indexOf(s.value) !== -1;
      var card = el("div", "wizard-option" + (selected ? " selected" : ""));
      card.innerHTML = '<span class="opt-icon">' + s.icon + "</span>" + esc(s.value);
      card.dataset.value = s.value;
      card.addEventListener("click", function () {
        var idx = state.services.indexOf(s.value);
        if (idx === -1) {
          state.services.push(s.value);
          card.classList.add("selected");
        } else {
          state.services.splice(idx, 1);
          card.classList.remove("selected");
        }
      });
      grid.appendChild(card);
    });
    body.appendChild(grid);
  }

  function renderStep3(body) {
    body.innerHTML = "";
    body.appendChild(el("h3", "", "Event Details"));

    // Date + ZIP row
    var row = el("div", "");
    row.style.cssText = "display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:20px;";

    var dateWrap = el("div", "field");
    dateWrap.innerHTML =
      '<label for="wiz-date">Event Date</label>' +
      '<input id="wiz-date" type="date" style="width:100%;padding:10px;border:1px solid var(--line);border-radius:8px;font-size:0.95rem;" value="' +
      esc(state.eventDate) + '">';

    var zipWrap = el("div", "field");
    zipWrap.innerHTML =
      '<label for="wiz-zip">ZIP Code</label>' +
      '<input id="wiz-zip" type="text" placeholder="30303" style="width:100%;padding:10px;border:1px solid var(--line);border-radius:8px;font-size:0.95rem;" value="' +
      esc(state.zipCode) + '">';

    row.appendChild(dateWrap);
    row.appendChild(zipWrap);
    body.appendChild(row);

    body.appendChild(el("h3", "", "Roughly how many guests?"));
    var gGrid = el("div", "wizard-option-grid");
    GUEST_COUNTS.forEach(function (g) {
      var card = el("div", "wizard-option" + (state.guestCount === g ? " selected" : ""));
      card.textContent = g;
      card.dataset.value = g;
      card.addEventListener("click", function () {
        state.guestCount = g;
        gGrid.querySelectorAll(".wizard-option").forEach(function (c) {
          c.classList.remove("selected");
        });
        card.classList.add("selected");
      });
      gGrid.appendChild(card);
    });
    body.appendChild(gGrid);

    // Wire up inputs
    body.querySelector("#wiz-date").addEventListener("change", function () {
      state.eventDate = this.value;
    });
    body.querySelector("#wiz-zip").addEventListener("input", function () {
      state.zipCode = this.value;
    });
  }

  function renderStep4(body) {
    body.innerHTML = "";
    body.appendChild(el("h3", "", "Tables & Chairs"));
    body.appendChild(el("p", "sub", "Help us get an accurate quote for your setup."));

    // Chair count
    var chairRow = el("div", "field");
    chairRow.style.marginBottom = "16px";
    chairRow.innerHTML =
      '<label for="wiz-chairs">How many chairs?</label>' +
      '<input id="wiz-chairs" type="number" min="0" placeholder="e.g. 50" style="width:100%;padding:10px;border:1px solid var(--line);border-radius:8px;font-size:0.95rem;" value="' +
      esc(state.chairCount) + '">';
    body.appendChild(chairRow);

    // Chair style
    body.appendChild(el("h3", "", "Chair style?"));
    var styleGrid = el("div", "wizard-option-grid");
    CHAIR_STYLES.forEach(function (cs) {
      var card = el("div", "wizard-option" + (state.chairStyle === cs.value ? " selected" : ""));
      card.innerHTML = '<span class="opt-icon">' + cs.icon + "</span>" + esc(cs.value);
      card.dataset.value = cs.value;
      card.addEventListener("click", function () {
        state.chairStyle = cs.value;
        styleGrid.querySelectorAll(".wizard-option").forEach(function (c) {
          c.classList.remove("selected");
        });
        card.classList.add("selected");
      });
      styleGrid.appendChild(card);
    });
    body.appendChild(styleGrid);

    // Table count
    var tableRow = el("div", "field");
    tableRow.style.cssText = "margin-top:16px;margin-bottom:16px;";
    tableRow.innerHTML =
      '<label for="wiz-tables">How many tables?</label>' +
      '<input id="wiz-tables" type="number" min="0" placeholder="e.g. 10" style="width:100%;padding:10px;border:1px solid var(--line);border-radius:8px;font-size:0.95rem;" value="' +
      esc(state.tableCount) + '">';
    body.appendChild(tableRow);

    // Tent
    body.appendChild(el("h3", "", "Need a tent?"));
    var tentGrid = el("div", "wizard-option-grid");
    TENT_OPTIONS.forEach(function (t) {
      var card = el("div", "wizard-option" + (state.needsTent === t ? " selected" : ""));
      card.textContent = t;
      card.dataset.value = t;
      card.addEventListener("click", function () {
        state.needsTent = t;
        tentGrid.querySelectorAll(".wizard-option").forEach(function (c) {
          c.classList.remove("selected");
        });
        card.classList.add("selected");
      });
      tentGrid.appendChild(card);
    });
    body.appendChild(tentGrid);

    // Wire up number inputs
    body.querySelector("#wiz-chairs").addEventListener("input", function () {
      state.chairCount = this.value;
    });
    body.querySelector("#wiz-tables").addEventListener("input", function () {
      state.tableCount = this.value;
    });
  }

  function renderStep5(body) {
    body.innerHTML = "";
    body.appendChild(el("h3", "", "Catering & Concessions"));
    body.appendChild(el("p", "sub", "Which concession items are you interested in?"));
    var grid = el("div", "wizard-option-grid");
    CONCESSIONS_LIST.forEach(function (c) {
      var selected = state.concessions.indexOf(c.value) !== -1;
      var card = el("div", "wizard-option" + (selected ? " selected" : ""));
      card.innerHTML = '<span class="opt-icon">' + c.icon + "</span>" + esc(c.value);
      card.dataset.value = c.value;
      card.addEventListener("click", function () {
        var idx = state.concessions.indexOf(c.value);
        if (idx === -1) {
          state.concessions.push(c.value);
          card.classList.add("selected");
        } else {
          state.concessions.splice(idx, 1);
          card.classList.remove("selected");
        }
      });
      grid.appendChild(card);
    });
    body.appendChild(grid);
  }

  function renderStep6(body) {
    body.innerHTML = "";
    body.appendChild(el("h3", "", "Your Contact Info"));
    body.appendChild(el("p", "sub", "We'll use this to connect you with Atlanta providers."));

    var fields = [
      { id: "wiz-name",  label: "Full Name", type: "text",  stateKey: "name",  required: true },
      { id: "wiz-phone", label: "Phone",      type: "tel",   stateKey: "phone", required: true },
      { id: "wiz-email", label: "Email",      type: "email", stateKey: "email", required: true }
    ];

    fields.forEach(function (f) {
      var wrap = el("div", "field");
      wrap.style.marginBottom = "12px";
      wrap.innerHTML =
        '<label for="' + f.id + '">' + f.label +
        (f.required ? ' <span style="color:#e33">*</span>' : "") +
        '</label><input id="' + f.id + '" type="' + f.type +
        '" style="width:100%;padding:10px;border:1px solid var(--line);border-radius:8px;font-size:0.95rem;" value="' +
        esc(state[f.stateKey]) + '"' + (f.required ? " required" : "") + ">";
      body.appendChild(wrap);
    });

    var msgWrap = el("div", "field");
    msgWrap.style.marginBottom = "12px";
    msgWrap.innerHTML =
      '<label for="wiz-msg">Message <span style="color:var(--muted);font-weight:400;">(optional)</span></label>' +
      '<textarea id="wiz-msg" rows="3" placeholder="Any other details about your event..." style="width:100%;padding:10px;border:1px solid var(--line);border-radius:8px;font-size:0.95rem;resize:vertical;">' +
      esc(state.message) + "</textarea>";
    body.appendChild(msgWrap);

    // Wire up
    body.querySelector("#wiz-name").addEventListener("input",  function () { state.name    = this.value; });
    body.querySelector("#wiz-phone").addEventListener("input", function () { state.phone   = this.value; });
    body.querySelector("#wiz-email").addEventListener("input", function () { state.email   = this.value; });
    body.querySelector("#wiz-msg").addEventListener("input",   function () { state.message = this.value; });
  }

  function renderThankYou(body) {
    body.innerHTML = "";
    var div = el("div", "wizard-thank-you");
    div.innerHTML = [
      '<span class="ty-icon">&#10003;</span>',
      "<h3>Thanks " + esc(state.name) + "!</h3>",
      "<p>We received your event request. An Atlanta provider will be in touch shortly.</p>",
      "<p>For immediate help, call <strong><a href=\"tel:+14018890182\">(401) 889-0182</a></strong></p>"
    ].join("");
    body.appendChild(div);
  }

  // ─── Navigation ───────────────────────────────────────────────────────────

  var overlay, wizBody, nextBtn, backBtn, stepLabel, stepDots;

  function renderCurrentStep() {
    var steps = activeSteps();
    var visualIdx = steps.indexOf(state.currentStep); // 0-based position

    // Update progress dots
    stepDots.forEach(function (dot) {
      var n = parseInt(dot.dataset.step, 10);
      dot.classList.remove("active", "done");
      if (n === state.currentStep) {
        dot.classList.add("active");
      } else if (n < state.currentStep && steps.indexOf(n) !== -1) {
        dot.classList.add("done");
      } else if (n < state.currentStep) {
        // step number less than current but not in active steps (skipped) — still show done
        dot.classList.add("done");
      }
    });

    stepLabel.textContent = "Step " + (visualIdx + 1) + " of " + steps.length;

    // Back button
    backBtn.style.display = (visualIdx === 0) ? "none" : "";

    // Next button label
    nextBtn.textContent = (state.currentStep === 6) ? "Submit Request" : "Next";
    nextBtn.style.display = "";

    // Render body
    switch (state.currentStep) {
      case 1: renderStep1(wizBody); break;
      case 2: renderStep2(wizBody); break;
      case 3: renderStep3(wizBody); break;
      case 4: renderStep4(wizBody); break;
      case 5: renderStep5(wizBody); break;
      case 6: renderStep6(wizBody); break;
    }
  }

  function advance() {
    collectCurrentStepValues();

    if (state.currentStep === 6) {
      if (!state.name.trim() || !state.phone.trim() || !state.email.trim()) {
        alert("Please fill in your name, phone, and email before submitting.");
        return;
      }
      submitWizard();
      return;
    }

    var steps = activeSteps();
    var idx = steps.indexOf(state.currentStep);
    if (idx < steps.length - 1) {
      state.currentStep = steps[idx + 1];
      renderCurrentStep();
    }
  }

  function goBack() {
    collectCurrentStepValues();
    var steps = activeSteps();
    var idx = steps.indexOf(state.currentStep);
    if (idx > 0) {
      state.currentStep = steps[idx - 1];
      renderCurrentStep();
    }
  }

  // Collect values from any live inputs in the current body
  function collectCurrentStepValues() {
    function val(id) {
      var e = wizBody.querySelector(id);
      return e ? e.value : null;
    }
    var d = val("#wiz-date");   if (d !== null) state.eventDate  = d;
    var z = val("#wiz-zip");    if (z !== null) state.zipCode    = z;
    var n = val("#wiz-name");   if (n !== null) state.name       = n;
    var p = val("#wiz-phone");  if (p !== null) state.phone      = p;
    var em = val("#wiz-email"); if (em !== null) state.email     = em;
    var m = val("#wiz-msg");    if (m !== null) state.message    = m;
    var ch = val("#wiz-chairs");if (ch !== null) state.chairCount = ch;
    var tb = val("#wiz-tables");if (tb !== null) state.tableCount = tb;
  }

  // ─── Submit & persist ─────────────────────────────────────────────────────

  function submitToSupabase(lead) {
    if (!SUPABASE_URL || !SUPABASE_ANON_KEY) return;
    var row = {
      event_type:  lead.eventType,
      services:    lead.services,
      event_date:  lead.eventDate,
      zip_code:    lead.zipCode,
      guest_count: lead.guestCount,
      chair_count: lead.chairCount,
      chair_style: lead.chairStyle,
      table_count: lead.tableCount,
      needs_tent:  lead.needsTent,
      concessions: lead.concessions,
      name:        lead.name,
      phone:       lead.phone,
      email:       lead.email,
      message:     lead.message,
      source:      lead.source,
      page_url:    window.location.href
    };
    fetch(SUPABASE_URL + "/rest/v1/leads", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": "Bearer " + SUPABASE_ANON_KEY,
        "Prefer": "return=minimal"
      },
      body: JSON.stringify(row)
    }).then(function (res) {
      if (!res.ok) {
        res.text().then(function (t) {
          console.error("Supabase lead insert failed (" + res.status + "): " + t);
        });
      }
    }).catch(function (err) {
      console.error("Supabase lead insert error:", err);
    });
  }

  function submitWizard() {
    var lead = {
      id:          "WIZ-" + Date.now(),
      eventType:   state.eventType,
      services:    state.services.slice(),
      eventDate:   state.eventDate,
      zipCode:     state.zipCode,
      guestCount:  state.guestCount,
      chairCount:  state.chairCount,
      chairStyle:  state.chairStyle,
      tableCount:  state.tableCount,
      needsTent:   state.needsTent,
      concessions: state.concessions.slice(),
      name:        state.name,
      phone:       state.phone,
      email:       state.email,
      message:     state.message,
      source:      "Booking Wizard",
      created:     new Date().toISOString()
    };

    try {
      var key = "abhr_leads";
      var existing = JSON.parse(localStorage.getItem(key) || "[]");
      existing.unshift(lead);
      localStorage.setItem(key, JSON.stringify(existing));
    } catch (err) { /* storage unavailable */ }

    submitToSupabase(lead);

    // Show thank-you screen
    renderThankYou(wizBody);

    // Hide nav buttons
    nextBtn.style.display = "none";
    backBtn.style.display = "none";

    // Mark all dots done
    stepDots.forEach(function (dot) {
      dot.classList.remove("active");
      dot.classList.add("done");
    });
    stepLabel.textContent = "Request submitted!";
  }

  // ─── Open / close ─────────────────────────────────────────────────────────

  function resetState() {
    state.currentStep = 1;
    state.eventType   = "";
    state.services    = [];
    state.eventDate   = "";
    state.zipCode     = "";
    state.guestCount  = "";
    state.chairCount  = "";
    state.chairStyle  = "";
    state.tableCount  = "";
    state.needsTent   = "";
    state.concessions = [];
    state.name        = "";
    state.phone       = "";
    state.email       = "";
    state.message     = "";
  }

  function openWizard() {
    resetState();
    overlay.classList.add("open");
    document.body.style.overflow = "hidden";
    renderCurrentStep();
  }

  function closeWizard() {
    overlay.classList.remove("open");
    document.body.style.overflow = "";
  }

  // ─── Init ─────────────────────────────────────────────────────────────────

  function init() {
    overlay = buildShell();

    wizBody   = overlay.querySelector(".wizard-body");
    nextBtn   = overlay.querySelector(".wizard-next");
    backBtn   = overlay.querySelector(".wizard-back");
    stepLabel = overlay.querySelector(".wizard-step-label");
    stepDots  = Array.prototype.slice.call(overlay.querySelectorAll(".wizard-step-dot"));

    var closeBtn = overlay.querySelector(".wizard-close");

    // Open trigger — delegate so it works for any [data-wizard-open] or #wizard-open element
    document.addEventListener("click", function (e) {
      var t = e.target;
      while (t && t !== document.body) {
        if (t.id === "wizard-open" || t.hasAttribute("data-wizard-open")) {
          e.preventDefault();
          openWizard();
          return;
        }
        t = t.parentElement;
      }
    });

    // Close button
    closeBtn.addEventListener("click", closeWizard);

    // Click on overlay backdrop closes wizard
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) closeWizard();
    });

    // ESC key closes wizard
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && overlay.classList.contains("open")) closeWizard();
    });

    // Navigation buttons
    nextBtn.addEventListener("click", advance);
    backBtn.addEventListener("click", goBack);
  }

  // Run after DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})();
