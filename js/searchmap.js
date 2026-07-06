/* Atlanta Bounce House Rentals — Search Map
   Interactive Leaflet map with synced business listing cards.
   Desktop: cards on the left, map on the right.
   Mobile:  full map with a floating "List" toggle that opens a bottom sheet.
   Data comes from window.ABHR_PROVIDERS (generated in /js/map-data.js).
   No API keys required — uses OpenStreetMap tiles via Leaflet.
*/
(function () {
  "use strict";

  var ATL = [33.749, -84.388]; // metro Atlanta fallback center

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function num(v, dflt) {
    var n = parseFloat(v);
    return isNaN(n) ? dflt : n;
  }

  // Haversine-ish squared distance is enough for sorting "near" a center.
  function dist2(aLat, aLng, bLat, bLng) {
    var dLat = aLat - bLat, dLng = (aLng - bLng) * Math.cos(aLat * Math.PI / 180);
    return dLat * dLat + dLng * dLng;
  }

  function starHtml(rating) {
    if (!rating) return '<span class="sm-noreview">New</span>';
    return '<span class="sm-star">&#9733;</span>' + rating;
  }

  function initMap(container) {
    if (!window.L) return; // Leaflet failed to load
    var providers = (window.ABHR_PROVIDERS || []).filter(function (p) {
      return p.lat && p.lng;
    });
    if (!providers.length) { container.style.display = "none"; return; }

    var centerLat = num(container.getAttribute("data-lat"), ATL[0]);
    var centerLng = num(container.getAttribute("data-lng"), ATL[1]);
    var zoom = num(container.getAttribute("data-zoom"), 11);
    var limit = num(container.getAttribute("data-limit"), 0);
    var areaName = container.getAttribute("data-area") || "";

    // Sort providers by proximity to the map center so the closest show first.
    providers = providers.slice().sort(function (a, b) {
      return dist2(centerLat, centerLng, a.lat, a.lng) - dist2(centerLat, centerLng, b.lat, b.lng);
    });
    if (limit > 0) providers = providers.slice(0, limit);

    // ── Build the shell ──────────────────────────────────────────────
    var panel = document.createElement("div");
    panel.className = "sm-panel";
    var listHead = document.createElement("div");
    listHead.className = "sm-panel-head";
    listHead.innerHTML = "<strong>" + providers.length + "</strong> provider" +
      (providers.length === 1 ? "" : "s") +
      (areaName ? " near " + esc(areaName) : " across metro Atlanta");
    var list = document.createElement("div");
    list.className = "sm-cards";
    panel.appendChild(listHead);
    panel.appendChild(list);

    var mapEl = document.createElement("div");
    mapEl.className = "sm-map";

    var toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "sm-list-toggle";
    toggle.innerHTML = '<span class="sm-toggle-list">&#9776; List</span><span class="sm-toggle-map">&#9678; Map</span>';

    container.appendChild(panel);
    container.appendChild(mapEl);
    container.appendChild(toggle);

    // ── Leaflet map ──────────────────────────────────────────────────
    var map = L.map(mapEl, {
      center: [centerLat, centerLng],
      zoom: zoom,
      scrollWheelZoom: false,
      zoomControl: true
    });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);
    // Let the wheel zoom only after the user clicks into the map.
    map.on("focus", function () { map.scrollWheelZoom.enable(); });
    map.on("blur", function () { map.scrollWheelZoom.disable(); });

    var markers = [];
    var cards = [];
    var bounds = [];

    function makeIcon(active) {
      return L.divIcon({
        className: "sm-pin" + (active ? " active" : ""),
        html: '<span class="sm-pin-dot"></span>',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      });
    }

    function highlight(idx) {
      cards.forEach(function (c, i) {
        c.classList.toggle("active", i === idx);
      });
      markers.forEach(function (m, i) {
        m.setIcon(makeIcon(i === idx));
        if (i === idx) m.setZIndexOffset(1000); else m.setZIndexOffset(0);
      });
    }

    providers.forEach(function (p, i) {
      // Marker
      var marker = L.marker([p.lat, p.lng], { icon: makeIcon(false) }).addTo(map);
      var svc = (p.services || []).slice(0, 3).join(", ");
      marker.bindPopup(
        '<div class="sm-popup">' +
          '<a class="sm-popup-name" href="/partners/' + esc(p.slug) + '/">' + esc(p.name) + '</a>' +
          '<div class="sm-popup-meta">' + starHtml(p.rating) +
            (p.reviews ? ' <span class="sm-muted">(' + p.reviews + ')</span>' : "") +
            ' &middot; ' + esc(p.city) + '</div>' +
          (svc ? '<div class="sm-popup-svc">' + esc(svc) + '</div>' : "") +
          '<a class="sm-popup-btn" href="/partners/' + esc(p.slug) + '/">View details &rsaquo;</a>' +
        '</div>'
      );
      marker.on("click", function () { highlight(i); scrollCardIntoView(i); });
      markers.push(marker);
      bounds.push([p.lat, p.lng]);

      // Card
      var card = document.createElement("div");
      card.className = "sm-card";
      card.innerHTML =
        '<div class="sm-card-body">' +
          '<a class="sm-card-name" href="/partners/' + esc(p.slug) + '/">' + esc(p.name) + '</a>' +
          '<div class="sm-card-meta">' + starHtml(p.rating) +
            (p.reviews ? ' <span class="sm-muted">(' + p.reviews + ' reviews)</span>' : "") +
          '</div>' +
          '<div class="sm-card-loc">' + esc(p.category || "Party rentals") + ' &middot; ' + esc(p.city) + ', GA</div>' +
          (svc ? '<div class="sm-card-svc">' + esc(svc) + '</div>' : "") +
        '</div>' +
        '<a class="sm-card-cta" href="/partners/' + esc(p.slug) + '/" aria-label="View ' + esc(p.name) + '">&#8599;</a>';
      card.addEventListener("mouseenter", function () { highlight(i); });
      card.addEventListener("click", function (e) {
        if (e.target.closest("a")) return; // let real links work
        highlight(i);
        map.setView([p.lat, p.lng], Math.max(map.getZoom(), 13), { animate: true });
        marker.openPopup();
      });
      list.appendChild(card);
      cards.push(card);
    });

    function scrollCardIntoView(idx) {
      var c = cards[idx];
      if (!c) return;
      if (typeof c.scrollIntoView === "function") {
        c.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    }

    // Fit to markers when we have a spread, otherwise keep the requested center.
    if (bounds.length > 1 && !container.hasAttribute("data-lat")) {
      map.fitBounds(bounds, { padding: [40, 40] });
    }

    // ── Mobile list toggle (bottom sheet) ────────────────────────────
    toggle.addEventListener("click", function () {
      container.classList.toggle("sm-show-list");
    });

    // Leaflet needs a size recalc once it becomes visible / on resize.
    setTimeout(function () { map.invalidateSize(); }, 200);
    window.addEventListener("resize", function () { map.invalidateSize(); });
  }

  function init() {
    var maps = document.querySelectorAll("[data-searchmap]");
    for (var i = 0; i < maps.length; i++) initMap(maps[i]);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
