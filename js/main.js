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

  // Quote form handling (homepage + service pages)
  var forms = document.querySelectorAll("form[data-quote-form]");
  forms.forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var data = {
        id: "L-" + Date.now(),
        name: form.name ? form.name.value : "",
        phone: form.phone ? form.phone.value : "",
        email: form.email ? form.email.value : "",
        service: form.service ? form.service.value : "",
        date: form.event_date ? form.event_date.value : "",
        zip: form.zip ? form.zip.value : "",
        message: form.message ? form.message.value : "",
        source: "Website Quote Form",
        created: new Date().toISOString()
      };
      // Persist locally so it appears on the Leads board (demo storage).
      try {
        var key = "abhr_leads";
        var existing = JSON.parse(localStorage.getItem(key) || "[]");
        existing.unshift(data);
        localStorage.setItem(key, JSON.stringify(existing));
      } catch (err) { /* storage unavailable */ }

      var success = form.querySelector("[data-success]");
      var fields = form.querySelector("[data-fields]");
      if (success) success.style.display = "block";
      if (fields) fields.style.display = "none";
      form.reset();
    });
  });
})();
