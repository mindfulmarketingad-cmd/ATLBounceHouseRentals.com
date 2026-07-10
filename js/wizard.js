/* Atlanta Bounce House Rentals — Booking Popup
   Single-page form, vanilla JS, no external dependencies. Self-contained IIFE.
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
        '<div class="wizard-body"></div>',
        '<div class="wizard-nav">',
          '<button class="btn wizard-submit">Submit Request</button>',
        '</div>',
      '</div>'
    ].join("");

    document.body.appendChild(overlay);
    return overlay;
  }

  // ─── Single-page form ───────────────────────────────────────────────────────

  function singleSelectGrid(list, currentVal, onPick, iconKey) {
    var grid = el("div", "wizard-option-grid");
    list.forEach(function (item) {
      var value = typeof item === "string" ? item : item.value;
      var icon = typeof item === "string" ? "" : item.icon;
      var card = el("div", "wizard-option" + (currentVal === value ? " selected" : ""));
      card.innerHTML = (icon ? '<span class="opt-icon">' + icon + "</span>" : "") + esc(value);
      card.dataset.value = value;
      card.addEventListener("click", function () {
        onPick(value);
        grid.querySelectorAll(".wizard-option").forEach(function (c) { c.classList.remove("selected"); });
        card.classList.add("selected");
      });
      grid.appendChild(card);
    });
    return grid;
  }

  function multiSelectGrid(list, currentList, onToggle) {
    var grid = el("div", "wizard-option-grid");
    list.forEach(function (item) {
      var selected = currentList.indexOf(item.value) !== -1;
      var card = el("div", "wizard-option" + (selected ? " selected" : ""));
      card.innerHTML = '<span class="opt-icon">' + item.icon + "</span>" + esc(item.value);
      card.dataset.value = item.value;
      card.addEventListener("click", function () {
        var nowSelected = onToggle(item.value);
        card.classList.toggle("selected", nowSelected);
      });
      grid.appendChild(card);
    });
    return grid;
  }

  function field(labelHtml, inputHtml) {
    var wrap = el("div", "field");
    wrap.innerHTML = '<label>' + labelHtml + "</label>" + inputHtml;
    return wrap;
  }

  function renderForm(body) {
    body.innerHTML = "";

    body.appendChild(el("h3", "", "Tell Us About Your Event"));
    body.appendChild(el("p", "sub", "One quick form — we'll match you with available Atlanta providers."));

    // Event type
    body.appendChild(el("h4", "wiz-section-label", "What kind of event is this?"));
    body.appendChild(singleSelectGrid(EVENT_TYPES, state.eventType, function (v) { state.eventType = v; }));

    // Services
    body.appendChild(el("h4", "wiz-section-label", "What do you need?"));
    body.appendChild(el("p", "sub-tight", "Select all that apply."));
    body.appendChild(multiSelectGrid(SERVICES_LIST, state.services, function (v) {
      var idx = state.services.indexOf(v);
      if (idx === -1) { state.services.push(v); } else { state.services.splice(idx, 1); }
      toggleConditionalSections(body);
      return state.services.indexOf(v) !== -1;
    }));

    // Date + ZIP
    var row = el("div", "wizard-row-2");
    var dateWrap = field("Event Date",
      '<input id="wiz-date" type="date" value="' + esc(state.eventDate) + '">');
    var zipWrap = field("ZIP Code",
      '<input id="wiz-zip" type="text" placeholder="30303" value="' + esc(state.zipCode) + '">');
    row.appendChild(dateWrap);
    row.appendChild(zipWrap);
    body.appendChild(row);

    // Guest count
    body.appendChild(el("h4", "wiz-section-label", "Roughly how many guests?"));
    body.appendChild(singleSelectGrid(GUEST_COUNTS, state.guestCount, function (v) { state.guestCount = v; }));

    // Tables & Chairs (conditional)
    var tablesSection = el("div", "wiz-conditional");
    tablesSection.id = "wiz-section-tables";
    tablesSection.appendChild(el("h4", "wiz-section-label", "Tables & Chairs"));
    var tcRow = el("div", "wizard-row-2");
    tcRow.appendChild(field("How many chairs?",
      '<input id="wiz-chairs" type="number" min="0" placeholder="e.g. 50" value="' + esc(state.chairCount) + '">'));
    tcRow.appendChild(field("How many tables?",
      '<input id="wiz-tables" type="number" min="0" placeholder="e.g. 10" value="' + esc(state.tableCount) + '">'));
    tablesSection.appendChild(tcRow);
    tablesSection.appendChild(el("p", "sub-tight", "Chair style"));
    tablesSection.appendChild(singleSelectGrid(CHAIR_STYLES, state.chairStyle, function (v) { state.chairStyle = v; }));
    tablesSection.appendChild(el("p", "sub-tight", "Need a tent?"));
    tablesSection.appendChild(singleSelectGrid(TENT_OPTIONS, state.needsTent, function (v) { state.needsTent = v; }));
    body.appendChild(tablesSection);

    // Concessions (conditional)
    var concessionsSection = el("div", "wiz-conditional");
    concessionsSection.id = "wiz-section-concessions";
    concessionsSection.appendChild(el("h4", "wiz-section-label", "Catering & Concessions"));
    concessionsSection.appendChild(el("p", "sub-tight", "Which items are you interested in?"));
    concessionsSection.appendChild(multiSelectGrid(CONCESSIONS_LIST, state.concessions, function (v) {
      var idx = state.concessions.indexOf(v);
      if (idx === -1) { state.concessions.push(v); } else { state.concessions.splice(idx, 1); }
      return state.concessions.indexOf(v) !== -1;
    }));
    body.appendChild(concessionsSection);

    // Contact info
    body.appendChild(el("h4", "wiz-section-label", "Your Contact Info"));
    var contactFields = [
      { id: "wiz-name",  label: "Full Name", type: "text",  stateKey: "name",  required: true },
      { id: "wiz-phone", label: "Phone",      type: "tel",   stateKey: "phone", required: true },
      { id: "wiz-email", label: "Email",      type: "email", stateKey: "email", required: true }
    ];
    contactFields.forEach(function (f) {
      body.appendChild(field(
        f.label + (f.required ? ' <span class="wiz-required">*</span>' : ""),
        '<input id="' + f.id + '" type="' + f.type + '" value="' + esc(state[f.stateKey]) + '"' + (f.required ? " required" : "") + ">"
      ));
    });
    body.appendChild(field(
      'Message <span class="wiz-optional">(optional)</span>',
      '<textarea id="wiz-msg" rows="3" placeholder="Any other details about your event...">' + esc(state.message) + "</textarea>"
    ));

    // Wire up all live inputs
    body.querySelector("#wiz-date").addEventListener("change", function () { state.eventDate = this.value; });
    body.querySelector("#wiz-zip").addEventListener("input", function () { state.zipCode = this.value; });
    body.querySelector("#wiz-chairs").addEventListener("input", function () { state.chairCount = this.value; });
    body.querySelector("#wiz-tables").addEventListener("input", function () { state.tableCount = this.value; });
    body.querySelector("#wiz-name").addEventListener("input", function () { state.name = this.value; });
    body.querySelector("#wiz-phone").addEventListener("input", function () { state.phone = this.value; });
    body.querySelector("#wiz-email").addEventListener("input", function () { state.email = this.value; });
    body.querySelector("#wiz-msg").addEventListener("input", function () { state.message = this.value; });

    toggleConditionalSections(body);
  }

  // Show/hide the Tables & Chairs and Concessions sections based on what's selected.
  function toggleConditionalSections(body) {
    var hasTables = state.services.indexOf("Tables, Chairs & Tents") !== -1;
    var hasConcessions = state.services.some(function (s) { return s.indexOf("Concessions") === 0; });
    var tablesSection = body.querySelector("#wiz-section-tables");
    var concessionsSection = body.querySelector("#wiz-section-concessions");
    if (tablesSection) tablesSection.style.display = hasTables ? "" : "none";
    if (concessionsSection) concessionsSection.style.display = hasConcessions ? "" : "none";
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

  // ─── Open / close ─────────────────────────────────────────────────────────

  var overlay, wizBody, submitBtn;

  function submitForm() {
    if (!state.name.trim() || !state.phone.trim() || !state.email.trim()) {
      alert("Please fill in your name, phone, and email before submitting.");
      return;
    }
    submitWizard();
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
    submitBtn.style.display = "none";
  }

  function resetState() {
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
    submitBtn.style.display = "";
    submitBtn.textContent = "Submit Request";
    renderForm(wizBody);
  }

  function closeWizard() {
    overlay.classList.remove("open");
    document.body.style.overflow = "";
  }

  // ─── Init ─────────────────────────────────────────────────────────────────

  function init() {
    overlay = buildShell();

    wizBody   = overlay.querySelector(".wizard-body");
    submitBtn = overlay.querySelector(".wizard-submit");

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

    // Submit
    submitBtn.addEventListener("click", submitForm);
  }

  // Run after DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})();
