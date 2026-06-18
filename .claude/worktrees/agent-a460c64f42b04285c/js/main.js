/* Atlanta Bounce House Rental Directory - shared site scripts */
(function () {
  "use strict";

  // Mobile nav toggle
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.querySelector(".main-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      nav.classList.toggle("open");
      var expanded = nav.classList.contains("open");
      toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
    });
  }

  // Set current year in footers
  var years = document.querySelectorAll("[data-year]");
  var y = new Date().getFullYear();
  years.forEach(function (el) { el.textContent = y; });

  /**
   * saveLead — persist an enriched lead object to localStorage key "abhr_leads".
   * Used by both the standard quote form and the booking wizard (wizard.js).
   * The wizard passes a fully-enriched object; the quote form builds a compatible
   * structure with the fields it collects.
   *
   * Enriched lead schema:
   *   id, eventType, services[], eventDate, zipCode, guestCount,
   *   chairCount, chairStyle, tableCount, needsTent, concessions[],
   *   name, phone, email, message, source, created
   */
  function saveLead(lead) {
    try {
      var key = "abhr_leads";
      var existing = JSON.parse(localStorage.getItem(key) || "[]");
      existing.unshift(lead);
      localStorage.setItem(key, JSON.stringify(existing));
    } catch (err) { /* storage unavailable */ }
  }

  // Expose so wizard.js (loaded after main.js) can call window.ABHR.saveLead
  window.ABHR = window.ABHR || {};
  window.ABHR.saveLead = saveLead;

  // Quote form handling (homepage + service pages)
  // Wizard leads are handled entirely in wizard.js using the same saveLead helper.
  var forms = document.querySelectorAll("form[data-quote-form]");
  forms.forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var data = {
        id:          "L-" + Date.now(),
        // Enriched fields (populated by wizard; left blank for simple form)
        eventType:   "",
        services:    form.service ? [form.service.value] : [],
        eventDate:   form.event_date ? form.event_date.value : "",
        zipCode:     form.zip ? form.zip.value : "",
        guestCount:  "",
        chairCount:  "",
        chairStyle:  "",
        tableCount:  "",
        needsTent:   "",
        concessions: [],
        // Contact fields
        name:        form.name ? form.name.value : "",
        phone:       form.phone ? form.phone.value : "",
        email:       form.email ? form.email.value : "",
        message:     form.message ? form.message.value : "",
        source:      "Website Quote Form",
        created:     new Date().toISOString()
      };
      saveLead(data);

      var success = form.querySelector("[data-success]");
      var fields  = form.querySelector("[data-fields]");
      if (success) success.style.display = "block";
      if (fields)  fields.style.display  = "none";
      form.reset();
    });
  });
})();
