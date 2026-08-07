/* Atlanta Bounce House Rentals — site analytics tracker.
   Vanilla JS, no dependencies. Fires directly at Supabase's REST API with
   the anon key (same pattern as wizard.js/leads.js) since this is a static
   site with no server to route through. Never throws, never blocks the
   page — every failure degrades to a silent no-op.

   Event types: pageview, listing_view, call_click, directions_click,
   search, review_click. See supabase/schema_analytics.sql.
*/
(function () {
  "use strict";

  var SUPABASE_URL = "https://tbqigevoksabizjogvtm.supabase.co";
  var SUPABASE_ANON_KEY = "sb_publishable_aHlx0Tdu2rhOTBUp3lhkQw_Lv6Awz7a";
  var SESSION_KEY = "abhr_analytics_session";
  var VISITOR_KEY = "abhr_analytics_visitor";

  function randomId() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return "id-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
  }

  function sessionId() {
    try {
      var id = sessionStorage.getItem(SESSION_KEY);
      if (!id) { id = randomId(); sessionStorage.setItem(SESSION_KEY, id); }
      return id;
    } catch (e) { return "no-session-storage"; }
  }

  function visitorId() {
    try {
      var id = localStorage.getItem(VISITOR_KEY);
      if (!id) { id = randomId(); localStorage.setItem(VISITOR_KEY, id); }
      return id;
    } catch (e) { return "no-local-storage"; }
  }

  // Maps a /partners/{slug}/ path to listing context using window.ABHR_PROVIDERS
  // (js/map-data.js) when it's available on the page; falls back to just the
  // slug parsed from the URL when it isn't.
  function classifyListingPath(path) {
    var m = /^\/partners\/([a-z0-9-]+)\/?$/.exec(path || "");
    if (!m) return null;
    var slug = m[1];
    var name = "", city = "";
    var list = window.ABHR_PROVIDERS;
    if (Array.isArray(list)) {
      for (var i = 0; i < list.length; i++) {
        if (list[i].slug === slug) { name = list[i].name || ""; city = list[i].city || ""; break; }
      }
    }
    return { listing_slug: slug, listing_name: name, city: city };
  }

  function trackEvent(eventType, extra) {
    try {
      var path = window.location.pathname;
      var body = {
        event_type: eventType,
        path: path,
        referrer: document.referrer || "",
        session_id: sessionId(),
        visitor_id: visitorId()
      };
      var listing = classifyListingPath(path);
      if (eventType === "pageview" && listing) {
        body.event_type = "listing_view";
        body.listing_slug = listing.listing_slug;
        body.listing_name = listing.listing_name;
        body.city = listing.city;
      }
      if (extra) {
        for (var k in extra) { if (extra.hasOwnProperty(k)) body[k] = extra[k]; }
      }
      fetch(SUPABASE_URL + "/rest/v1/ATLbounchouserentals_dashboard", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "apikey": SUPABASE_ANON_KEY,
          "Authorization": "Bearer " + SUPABASE_ANON_KEY,
          "Prefer": "return=minimal"
        },
        body: JSON.stringify(body),
        keepalive: true
      }).catch(function () { /* fire-and-forget, never throws */ });
    } catch (e) { /* never throws */ }
  }
  window.ABHR_trackEvent = trackEvent;

  function init() {
    trackEvent("pageview");

    // Click-to-call: every tel: link on the site (header, footer, quote
    // cards, etc.) — delegated so it covers links added after this runs.
    document.addEventListener("click", function (e) {
      var a = e.target.closest && e.target.closest('a[href^="tel:"]');
      if (a) trackEvent("call_click");
    });

    // Directions / reviews links carry a data-analytics-event attribute
    // (added to listicle cards and partner detail pages) instead of being
    // matched by href, so this stays correct if the destination URL format
    // ever changes.
    document.addEventListener("click", function (e) {
      var a = e.target.closest && e.target.closest("[data-analytics-event]");
      if (!a) return;
      var evt = a.getAttribute("data-analytics-event");
      if (evt === "directions_click" || evt === "review_click") {
        trackEvent(evt, {
          listing_slug: a.getAttribute("data-analytics-listing") || "",
          listing_name: a.getAttribute("data-analytics-name") || "",
          city: a.getAttribute("data-analytics-city") || ""
        });
      }
    });

    // Search: any <input type="search"> on the page (directory table,
    // listicle pages, /find/ hub), debounced so typing doesn't spam events.
    var searchTimers = new WeakMap();
    document.querySelectorAll('input[type="search"]').forEach(function (input) {
      input.addEventListener("input", function () {
        var existing = searchTimers.get(input);
        if (existing) clearTimeout(existing);
        var timer = setTimeout(function () {
          var q = input.value.trim();
          if (q) trackEvent("search", { query: q });
        }, 700);
        searchTimers.set(input, timer);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
