/* Booking form: business-hour time slots, valid date range, absolute redirect URL */
(function () {
  var dateInput = document.getElementById("date");
  var timeSelect = document.getElementById("time");
  var redirect = document.getElementById("redirect-url");
  if (!dateInput || !timeSelect) return;

  // FormSubmit requires an absolute _next URL
  if (redirect) {
    redirect.value = new URL("booking-confirmed.html", window.location.href).href;
  }

  // Shop hours: Tue–Fri 9–7, Sat 8–5. Closed Sun & Mon.
  var HOURS = { 2: [9, 19], 3: [9, 19], 4: [9, 19], 5: [9, 19], 6: [8, 17] };

  function fmt(d) {
    return d.toISOString().split("T")[0];
  }

  var today = new Date();
  var max = new Date();
  max.setDate(max.getDate() + 60);
  dateInput.min = fmt(today);
  dateInput.max = fmt(max);

  function label(hour, half) {
    var h12 = ((hour + 11) % 12) + 1;
    return h12 + (half ? ":30 " : ":00 ") + (hour < 12 ? "AM" : "PM");
  }

  function buildSlots() {
    var day = new Date(dateInput.value + "T12:00:00").getDay();
    timeSelect.innerHTML = "";
    var hours = HOURS[day];
    var first = document.createElement("option");
    first.value = "";
    first.disabled = true;
    first.selected = true;
    if (!hours) {
      first.textContent = "Closed Sun & Mon — pick another day";
      timeSelect.appendChild(first);
      return;
    }
    first.textContent = "Select a time";
    timeSelect.appendChild(first);
    for (var h = hours[0]; h < hours[1]; h++) {
      [false, true].forEach(function (half) {
        var opt = document.createElement("option");
        opt.textContent = label(h, half);
        timeSelect.appendChild(opt);
      });
    }
  }

  dateInput.addEventListener("change", buildSlots);
})();
