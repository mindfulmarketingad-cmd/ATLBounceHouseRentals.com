/* Atlanta Bounce House Rentals — Listicle directory (used on /cities/ and
   /services/ subpages). Vanilla JS, no dependencies.
   Handles: live search, filter dropdown, sort (rating/reviews/name/distance),
   reset, "show distance from me" (geolocation), list/map view toggle, and
   computing each card's "open today" hours client-side (so it's never stale
   from build time).
*/
(function () {
  "use strict";

  var DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

  function toRad(deg) { return deg * Math.PI / 180; }

  function milesBetween(lat1, lng1, lat2, lng2) {
    var R = 3958.8;
    var dLat = toRad(lat2 - lat1);
    var dLng = toRad(lng2 - lng1);
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  function applyTodayHours(card) {
    var raw = card.getAttribute("data-hours");
    var target = card.querySelector("[data-hours-text]");
    if (!target) return;
    if (!raw) { target.textContent = "Call to confirm today's hours"; return; }
    var hours;
    try { hours = JSON.parse(raw); } catch (e) { hours = null; }
    if (!hours || !Object.keys(hours).length) {
      target.textContent = "Call to confirm today's hours";
      return;
    }
    var todayName = DAY_NAMES[new Date().getDay()];
    var todayHours = hours[todayName];
    if (!todayHours) {
      target.textContent = "Call to confirm today's hours";
    } else if (/closed/i.test(todayHours)) {
      target.textContent = "Closed today (" + todayName + ")";
    } else {
      target.textContent = "Open today (" + todayName + "): " + todayHours;
    }
  }

  function initListicle(list) {
    var root = list.parentElement;
    if (!root) return;
    var toolbar = root.querySelector(".lc-toolbar");
    var controls = root.querySelector(".lc-controls");
    var mapView = root.querySelector("[data-lc-map]");
    var emptyMsg = root.querySelector("[data-lc-empty]");
    if (!controls) return;

    var searchInput = controls.querySelector(".lc-search");
    var filterSelect = controls.querySelector(".lc-filter");
    var sortSelect = controls.querySelector(".lc-sort");
    var resetBtn = controls.querySelector(".lc-reset");
    var distanceBtn = controls.querySelector(".lc-distance");
    var countLive = controls.querySelector(".lc-count-live");
    var countHeader = toolbar ? toolbar.querySelector(".lc-count") : null;

    var cards = Array.prototype.slice.call(list.querySelectorAll(".lc-card"));
    cards.forEach(applyTodayHours);

    var userLoc = null; // { lat, lng }

    function cardData(card) {
      return {
        el: card,
        name: (card.getAttribute("data-lc-name") || ""),
        city: (card.getAttribute("data-lc-city") || ""),
        services: (card.getAttribute("data-lc-services") || "").split(",").filter(Boolean),
        rating: parseFloat(card.getAttribute("data-lc-rating")) || 0,
        reviews: parseInt(card.getAttribute("data-lc-reviews"), 10) || 0,
        lat: parseFloat(card.getAttribute("data-lc-lat")),
        lng: parseFloat(card.getAttribute("data-lc-lng"))
      };
    }

    function updateCounts(n) {
      var total = cards.length;
      var word = n === 1 ? "listing" : "listings";
      if (countLive) countLive.textContent = n + " " + word + (n !== total ? " of " + total : "");
      if (countHeader) countHeader.textContent = total + " listing" + (total !== 1 ? "s" : "") + " on this page";
    }

    function render() {
      var q = (searchInput && searchInput.value || "").trim().toLowerCase();
      var filterVal = (filterSelect && filterSelect.value || "").toLowerCase();
      var sortVal = (sortSelect && sortSelect.value) || "rating";

      var items = cards.map(cardData);

      items.forEach(function (it) {
        var matchesSearch = !q || it.name.indexOf(q) >= 0 || it.city.indexOf(q) >= 0;
        var matchesFilter = !filterVal ||
          it.services.indexOf(filterVal) >= 0 ||
          it.city === filterVal;
        it.visible = matchesSearch && matchesFilter;
      });

      if (sortVal === "distance" && userLoc) {
        items.forEach(function (it) {
          it.distance = (!isNaN(it.lat) && !isNaN(it.lng))
            ? milesBetween(userLoc.lat, userLoc.lng, it.lat, it.lng) : Infinity;
        });
        items.sort(function (a, b) { return a.distance - b.distance; });
      } else if (sortVal === "reviews") {
        items.sort(function (a, b) { return b.reviews - a.reviews; });
      } else if (sortVal === "name") {
        items.sort(function (a, b) { return a.name.localeCompare(b.name); });
      } else {
        items.sort(function (a, b) { return (b.rating - a.rating) || (b.reviews - a.reviews); });
      }

      var visibleCount = 0;
      items.forEach(function (it) {
        list.appendChild(it.el);
        it.el.style.display = it.visible ? "" : "none";
        if (it.visible) visibleCount++;
      });

      if (emptyMsg) emptyMsg.hidden = visibleCount !== 0;
      updateCounts(visibleCount);
    }

    if (searchInput) searchInput.addEventListener("input", render);
    if (filterSelect) filterSelect.addEventListener("change", render);
    if (sortSelect) sortSelect.addEventListener("change", render);
    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        if (searchInput) searchInput.value = "";
        if (filterSelect) filterSelect.value = "";
        if (sortSelect) sortSelect.value = "rating";
        render();
      });
    }
    if (distanceBtn && navigator.geolocation) {
      distanceBtn.addEventListener("click", function () {
        distanceBtn.disabled = true;
        var original = distanceBtn.textContent;
        distanceBtn.textContent = "Locating…";
        navigator.geolocation.getCurrentPosition(function (pos) {
          userLoc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
          cards.forEach(function (card) {
            var lat = parseFloat(card.getAttribute("data-lc-lat"));
            var lng = parseFloat(card.getAttribute("data-lc-lng"));
            var badge = card.querySelector(".lc-distance-badge");
            if (badge && !isNaN(lat) && !isNaN(lng)) {
              var mi = milesBetween(userLoc.lat, userLoc.lng, lat, lng);
              badge.textContent = "· " + mi.toFixed(1) + " mi away";
              badge.hidden = false;
            }
          });
          if (sortSelect) sortSelect.value = "distance";
          distanceBtn.disabled = false;
          distanceBtn.textContent = original;
          render();
        }, function () {
          distanceBtn.disabled = false;
          distanceBtn.textContent = original;
          alert("Couldn't get your location. Check your browser's location permission and try again.");
        });
      });
    } else if (distanceBtn) {
      distanceBtn.style.display = "none";
    }

    // List / Map toggle
    if (toolbar && mapView) {
      var viewBtns = toolbar.querySelectorAll(".lc-view-btn");
      viewBtns.forEach(function (btn) {
        btn.addEventListener("click", function () {
          var view = btn.getAttribute("data-lc-view");
          viewBtns.forEach(function (b) { b.classList.toggle("active", b === btn); });
          if (view === "map") {
            controls.style.display = "none";
            list.style.display = "none";
            if (emptyMsg) emptyMsg.hidden = true;
            mapView.hidden = false;
            window.dispatchEvent(new Event("resize"));
          } else {
            controls.style.display = "";
            list.style.display = "";
            mapView.hidden = true;
            render();
          }
        });
      });
    }

    render();
  }

  function init() {
    var lists = document.querySelectorAll("[data-lc-list]");
    for (var i = 0; i < lists.length; i++) initListicle(lists[i]);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
