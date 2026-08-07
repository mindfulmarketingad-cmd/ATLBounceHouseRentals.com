/* Atlanta Bounce House Rentals — /dashboard analytics.
   Vanilla JS, no dependencies for stats/charts (hand-rolled SVG/CSS bars —
   this site avoids adding chart libraries after an earlier CDN dependency
   broke /leads/ in production). The one exception is the live activity
   panel: real Supabase Realtime requires the supabase-js client, so it's
   loaded from a CDN scoped to this page only, with a polling fallback if
   that script fails to load or connect — a CDN failure here degrades to
   "polling every 15s" instead of breaking the whole page.
*/
(function () {
  "use strict";

  var SUPABASE_URL = "https://tbqigevoksabizjogvtm.supabase.co";
  var SUPABASE_ANON_KEY = "sb_publishable_aHlx0Tdu2rhOTBUp3lhkQw_Lv6Awz7a";
  var EVENT_TYPES = ["pageview", "listing_view", "call_click", "directions_click", "search", "review_click"];
  var EVENT_LABELS = {
    pageview: "Pageviews", listing_view: "Listing Views", call_click: "Call Clicks",
    directions_click: "Directions Clicks", search: "Searches", review_click: "Review Clicks"
  };
  var LEAD_ACTION_TYPES = { call_click: 1, directions_click: 1, review_click: 1 };
  var IMPRESSION_TYPES = { pageview: 1, listing_view: 1 };

  var state = { range: 30, events: [], leadsCount: 0 };

  function restHeaders(extra) {
    var h = { "apikey": SUPABASE_ANON_KEY, "Authorization": "Bearer " + SUPABASE_ANON_KEY };
    if (extra) for (var k in extra) h[k] = extra[k];
    return h;
  }

  function sinceISO(days) {
    var d = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
    return d.toISOString();
  }

  function fetchEvents(days) {
    var url = SUPABASE_URL + "/rest/v1/atlbounchouserentals_dashboard?select=event_type,created_at,session_id,visitor_id,listing_slug,listing_name,city,query,path"
      + "&created_at=gte." + encodeURIComponent(sinceISO(days))
      + "&order=created_at.asc&limit=20000";
    return fetch(url, { headers: restHeaders() })
      .then(function (res) { return res.ok ? res.json() : []; })
      .catch(function () { return []; });
  }

  function fetchLeadsCount(days) {
    var url = SUPABASE_URL + "/rest/v1/leads_board?select=id"
      + "&created_at=gte." + encodeURIComponent(sinceISO(days))
      + "&limit=1";
    return fetch(url, { headers: restHeaders({ "Prefer": "count=exact" }) })
      .then(function (res) {
        var range = res.headers.get("Content-Range"); // "0-0/123"
        if (range && range.indexOf("/") >= 0) {
          var total = range.split("/")[1];
          return total === "*" ? 0 : parseInt(total, 10) || 0;
        }
        return 0;
      })
      .catch(function () { return 0; });
  }

  function esc(str) {
    return String(str || "").replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  // ─── Stat cards ──────────────────────────────────────────────────────
  function renderStats(events, leadsCount) {
    var sessions = new Set(), visitors = new Set();
    var counts = { leadActions: 0, searches: 0, impressions: 0 };
    events.forEach(function (e) {
      if (e.session_id) sessions.add(e.session_id);
      if (e.visitor_id) visitors.add(e.visitor_id);
      if (LEAD_ACTION_TYPES[e.event_type]) counts.leadActions++;
      if (e.event_type === "search") counts.searches++;
      if (IMPRESSION_TYPES[e.event_type]) counts.impressions++;
    });
    var cards = [
      { label: "Sessions", value: sessions.size },
      { label: "Unique Visitors", value: visitors.size },
      { label: "Impressions", value: counts.impressions },
      { label: "Lead Actions", value: counts.leadActions, sub: "calls, directions & review clicks" },
      { label: "Searches", value: counts.searches },
      { label: "Leads Received", value: leadsCount, sub: "real inbound quote requests", accent: true }
    ];
    var el = document.getElementById("dash-stats");
    if (!el) return;
    el.innerHTML = cards.map(function (c) {
      return '<div class="dash-stat' + (c.accent ? " accent" : "") + '">' +
        '<div class="dash-stat-value">' + c.value.toLocaleString() + '</div>' +
        '<div class="dash-stat-label">' + esc(c.label) + '</div>' +
        (c.sub ? '<div class="dash-stat-sub">' + esc(c.sub) + '</div>' : "") +
        '</div>';
    }).join("");
  }

  // ─── Action breakdown bar chart (hand-rolled, no library) ───────────
  function renderBarChart(events) {
    var counts = {};
    EVENT_TYPES.forEach(function (t) { counts[t] = 0; });
    events.forEach(function (e) { if (counts.hasOwnProperty(e.event_type)) counts[e.event_type]++; });
    var max = Math.max.apply(null, EVENT_TYPES.map(function (t) { return counts[t]; }).concat([1]));
    var el = document.getElementById("dash-bar-chart");
    if (!el) return;
    el.innerHTML = EVENT_TYPES.map(function (t) {
      var pct = Math.round((counts[t] / max) * 100);
      return '<div class="dash-bar-row">' +
        '<div class="dash-bar-label">' + esc(EVENT_LABELS[t]) + '</div>' +
        '<div class="dash-bar-track"><div class="dash-bar-fill" style="width:' + pct + '%"></div></div>' +
        '<div class="dash-bar-value">' + counts[t].toLocaleString() + '</div>' +
        '</div>';
    }).join("");
  }

  // ─── Daily trend line chart (hand-rolled SVG) ────────────────────────
  function renderLineChart(events, days) {
    var el = document.getElementById("dash-line-chart");
    if (!el) return;
    var byDay = {};
    var now = new Date();
    var labels = [];
    for (var i = days - 1; i >= 0; i--) {
      var d = new Date(now.getTime() - i * 86400000);
      var key = d.toISOString().slice(0, 10);
      byDay[key] = 0;
      labels.push(key);
    }
    events.forEach(function (e) {
      var key = (e.created_at || "").slice(0, 10);
      if (byDay.hasOwnProperty(key)) byDay[key]++;
    });
    var values = labels.map(function (k) { return byDay[k]; });
    var max = Math.max.apply(null, values.concat([1]));
    var w = 720, h = 220, pad = 28;
    var stepX = labels.length > 1 ? (w - pad * 2) / (labels.length - 1) : 0;
    var points = values.map(function (v, i) {
      var x = pad + i * stepX;
      var y = h - pad - (v / max) * (h - pad * 2);
      return x.toFixed(1) + "," + y.toFixed(1);
    });
    var areaPoints = points.concat([(pad + (labels.length - 1) * stepX).toFixed(1) + "," + (h - pad), pad + "," + (h - pad)]);
    var showEvery = Math.ceil(labels.length / 8) || 1;
    var xLabels = labels.map(function (k, i) {
      if (i % showEvery !== 0 && i !== labels.length - 1) return "";
      var x = pad + i * stepX;
      var short = k.slice(5); // MM-DD
      return '<text x="' + x.toFixed(1) + '" y="' + (h - 6) + '" class="dash-axis-label" text-anchor="middle">' + short + '</text>';
    }).join("");
    el.innerHTML =
      '<svg viewBox="0 0 ' + w + ' ' + h + '" class="dash-svg" role="img" aria-label="Daily activity trend">' +
        '<polyline points="' + areaPoints.join(" ") + '" class="dash-area"></polyline>' +
        '<polyline points="' + points.join(" ") + '" class="dash-line"></polyline>' +
        xLabels +
      '</svg>';
  }

  // ─── Per-business breakdown table ────────────────────────────────────
  function renderBusinessTable(events) {
    var byListing = {};
    events.forEach(function (e) {
      if (!e.listing_slug) return;
      var row = byListing[e.listing_slug] || (byListing[e.listing_slug] = {
        name: e.listing_name || e.listing_slug, city: e.city || "", views: 0, directions: 0, reviews: 0
      });
      if (e.event_type === "listing_view") row.views++;
      if (e.event_type === "directions_click") row.directions++;
      if (e.event_type === "review_click") row.reviews++;
      if (e.listing_name && !row.name) row.name = e.listing_name;
    });
    var rows = Object.keys(byListing).map(function (slug) {
      var r = byListing[slug];
      r.slug = slug;
      r.total = r.views + r.directions + r.reviews;
      return r;
    }).sort(function (a, b) { return b.total - a.total; });

    var el = document.getElementById("dash-business-table");
    if (!el) return;
    if (!rows.length) {
      el.innerHTML = '<div class="info-box" style="text-align:center;"><h3>No listing activity yet</h3><p class="muted" style="margin:0;">Views, directions and review clicks will show up here as visitors browse the directory.</p></div>';
      return;
    }
    el.innerHTML =
      '<table class="dash-table"><thead><tr>' +
        '<th>Business</th><th>City</th><th>Views</th><th>Directions</th><th>Reviews</th><th>Total</th>' +
      '</tr></thead><tbody>' +
      rows.map(function (r) {
        return '<tr>' +
          '<td><a href="/partners/' + esc(r.slug) + '/">' + esc(r.name) + '</a></td>' +
          '<td>' + esc(r.city) + '</td>' +
          '<td>' + r.views + '</td>' +
          '<td>' + r.directions + '</td>' +
          '<td>' + r.reviews + '</td>' +
          '<td><strong>' + r.total + '</strong></td>' +
        '</tr>';
      }).join("") +
      '</tbody></table>' +
      '<p class="muted" style="font-size:0.8rem;margin-top:10px;">Call clicks aren’t attributed to a specific business here — every call goes to the site’s own number, not a direct line to any one provider.</p>';
  }

  function renderAll() {
    renderStats(state.events, state.leadsCount);
    renderBarChart(state.events);
    renderLineChart(state.events, state.range);
    renderBusinessTable(state.events);
  }

  function loadRange(days) {
    state.range = days;
    var el = document.getElementById("dash-stats");
    if (el) el.innerHTML = '<div class="info-box" style="text-align:center;grid-column:1/-1;"><h3>Loading&hellip;</h3></div>';
    return Promise.all([fetchEvents(days), fetchLeadsCount(days)]).then(function (r) {
      state.events = r[0];
      state.leadsCount = r[1];
      renderAll();
    });
  }

  function wireRangeSelector() {
    var buttons = document.querySelectorAll("[data-dash-range]");
    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        buttons.forEach(function (b) { b.classList.toggle("active", b === btn); });
        loadRange(parseInt(btn.getAttribute("data-dash-range"), 10));
      });
    });
  }

  // ─── Live activity panel ──────────────────────────────────────────────
  var liveCount = 0;
  var pageOpenedAt = new Date();

  function prependLiveEvent(row) {
    var feed = document.getElementById("dash-live-feed");
    if (!feed) return;
    var empty = feed.querySelector("[data-live-empty]");
    if (empty) empty.remove();
    var el = document.createElement("div");
    el.className = "dash-live-row";
    var label = EVENT_LABELS[row.event_type] || row.event_type;
    var detail = row.listing_name ? (" — " + esc(row.listing_name)) : (row.path ? " — " + esc(row.path) : "");
    el.innerHTML = '<span class="dash-live-dot"></span><span>' + esc(label) + esc(detail) + '</span>' +
      '<span class="dash-live-time">' + new Date(row.created_at || Date.now()).toLocaleTimeString() + '</span>';
    feed.insertBefore(el, feed.firstChild);
    while (feed.children.length > 25) feed.removeChild(feed.lastChild);
    liveCount++;
    var counter = document.getElementById("dash-live-count");
    if (counter) counter.textContent = liveCount + " event" + (liveCount === 1 ? "" : "s") + " since you opened this page";
  }

  function setLiveStatus(text) {
    var el = document.getElementById("dash-live-status");
    if (el) el.textContent = text;
  }

  function startPollingFallback() {
    setLiveStatus("Live (polling)");
    var lastSeen = pageOpenedAt.toISOString();
    setInterval(function () {
      var url = SUPABASE_URL + "/rest/v1/atlbounchouserentals_dashboard?select=event_type,created_at,listing_name,path&created_at=gt." + encodeURIComponent(lastSeen) + "&order=created_at.asc&limit=50";
      fetch(url, { headers: restHeaders() }).then(function (res) { return res.ok ? res.json() : []; })
        .then(function (rows) {
          if (!rows.length) return;
          lastSeen = rows[rows.length - 1].created_at;
          rows.forEach(prependLiveEvent);
        }).catch(function () { /* ignore, try again next tick */ });
    }, 15000);
  }

  function startRealtime() {
    if (!window.supabase || !window.supabase.createClient) { startPollingFallback(); return; }
    try {
      var client = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
      var channel = client.channel("analytics-live")
        .on("postgres_changes", { event: "INSERT", schema: "public", table: "atlbounchouserentals_dashboard" }, function (payload) {
          prependLiveEvent(payload.new);
        })
        .subscribe(function (status) {
          if (status === "SUBSCRIBED") setLiveStatus("Live");
          else if (status === "CHANNEL_ERROR" || status === "TIMED_OUT" || status === "CLOSED") startPollingFallback();
        });
      setTimeout(function () {
        var status = document.getElementById("dash-live-status");
        if (status && status.textContent === "Connecting…") startPollingFallback();
      }, 8000);
    } catch (e) {
      startPollingFallback();
    }
  }

  function loadRealtimeSdk() {
    setLiveStatus("Connecting…");
    var script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.js";
    script.async = true;
    script.onload = startRealtime;
    script.onerror = startPollingFallback;
    document.head.appendChild(script);
  }

  function init() {
    if (!document.getElementById("dash-stats")) return;
    wireRangeSelector();
    loadRange(state.range);
    loadRealtimeSdk();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
