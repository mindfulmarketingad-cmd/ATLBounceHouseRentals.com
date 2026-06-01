/* Highlights the current day of the week in business-hours tables.
   Each hours row carries data-day="Monday" etc. */
(function () {
  "use strict";
  var days = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
  var today = days[new Date().getDay()];
  document.querySelectorAll("[data-day]").forEach(function (row) {
    if (row.getAttribute("data-day") === today) {
      row.classList.add("today");
    }
  });
})();
