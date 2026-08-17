/* Atlanta Bounce House Rentals — "Lead Calls We Received" section on
   /dashboard. Vanilla JS, no dependencies. Fetches the sanitized call list
   from /api/calls (a Vercel serverless function that holds the CallRail API
   key server-side — this file never sees it and never should). Renders a
   trend chart, a stat banner and an expandable per-call list, all matching
   the existing dashboard's hand-rolled SVG/CSS look.
*/
(function () {
  "use strict";

  var TIME_ZONE = "America/New_York";
  var NEW_WINDOW_MS = 48 * 60 * 60 * 1000;

  function esc(str) {
    return String(str || "").replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function dayKey(iso, tz) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleDateString("en-CA", { timeZone: tz }); // "YYYY-MM-DD"
  }

  function formatDateTime(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    try {
      return d.toLocaleString("en-US", {
        timeZone: TIME_ZONE, month: "short", day: "numeric",
        year: "numeric", hour: "numeric", minute: "2-digit"
      }) + " ET";
    } catch (e) {
      return d.toLocaleString();
    }
  }

  function formatDuration(seconds) {
    seconds = seconds || 0;
    var m = Math.floor(seconds / 60);
    var s = seconds % 60;
    return m + ":" + (s < 10 ? "0" : "") + s;
  }

  function statusBadge(call) {
    if (call.voicemail) return '<span class="call-status voicemail">Voicemail</span>';
    if (call.answered) return '<span class="call-status answered">Answered</span>';
    return '<span class="call-status missed">Missed</span>';
  }

  function fetchCalls() {
    return fetch("/api/calls")
      .then(function (res) {
        if (!res.ok) return res.json().then(function (b) { throw new Error((b && b.error) || "Request failed"); });
        return res.json();
      });
  }

  function renderError(root, message) {
    var fills = root.querySelectorAll("[data-calls-fill]");
    fills.forEach(function (el) { el.innerHTML = ""; });
    if (fills.length) {
      fills[0].innerHTML = '<div class="info-box" style="text-align:center;"><h3>Call data is unavailable right now</h3>' +
        '<p class="muted" style="margin:0;">' + esc(message) + '</p></div>';
    }
  }

  function renderStats(root, calls, totalRecords) {
    var now = Date.now();
    var todayKey = dayKey(new Date().toISOString(), TIME_ZONE);
    var monthKey = todayKey.slice(0, 7);
    var weekAgo = now - 7 * 24 * 60 * 60 * 1000;

    var thisMonth = 0, thisWeek = 0, today = 0;
    calls.forEach(function (c) {
      var t = new Date(c.start_time).getTime();
      var k = dayKey(c.start_time, TIME_ZONE);
      if (k.slice(0, 7) === monthKey) thisMonth++;
      if (t >= weekAgo) thisWeek++;
      if (k === todayKey) today++;
    });

    var cards = [
      { label: "Total", value: totalRecords },
      { label: "This Month", value: thisMonth },
      { label: "This Week", value: thisWeek },
      { label: "Today", value: today, accent: true }
    ];
    var el = root.querySelector("#calls-stats");
    if (!el) return;
    el.innerHTML = cards.map(function (c) {
      return '<div class="dash-stat' + (c.accent ? " accent" : "") + '">' +
        '<div class="dash-stat-value">' + c.value.toLocaleString() + '</div>' +
        '<div class="dash-stat-label">' + esc(c.label) + '</div>' +
        '</div>';
    }).join("");
  }

  function renderTrendChart(root, calls) {
    var el = root.querySelector("#calls-line-chart");
    if (!el) return;
    var byDay = {};
    var labels = [];
    for (var i = 7; i >= 0; i--) {
      var d = new Date(Date.now() - i * 86400000);
      var key = d.toLocaleDateString("en-CA", { timeZone: TIME_ZONE });
      byDay[key] = 0;
      labels.push(key);
    }
    calls.forEach(function (c) {
      var k = dayKey(c.start_time, TIME_ZONE);
      if (byDay.hasOwnProperty(k)) byDay[k]++;
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
    var xLabels = labels.map(function (k, i) {
      var x = pad + i * stepX;
      var short = k.slice(5);
      return '<text x="' + x.toFixed(1) + '" y="' + (h - 6) + '" class="dash-axis-label" text-anchor="middle">' + short + '</text>';
    }).join("");
    el.innerHTML =
      '<svg viewBox="0 0 ' + w + ' ' + h + '" class="dash-svg" role="img" aria-label="Calls per day, last 8 days">' +
        '<polyline points="' + areaPoints.join(" ") + '" class="dash-area"></polyline>' +
        '<polyline points="' + points.join(" ") + '" class="dash-line"></polyline>' +
        xLabels +
      '</svg>';
  }

  function callDetailHtml(c) {
    var tagsHtml = c.tags.length
      ? c.tags.map(function (t) { return '<span class="tag">' + esc(t) + '</span>'; }).join(" ")
      : '<span class="muted">None</span>';
    var recordingHtml = c.recording
      ? '<audio controls preload="none" src="' + esc(c.recording) + '" style="width:100%;margin-top:6px;"></audio>'
      : '<p class="muted" style="margin:6px 0 0;">No recording available.</p>';
    var transcriptHtml = c.transcription
      ? '<p style="white-space:pre-wrap;margin:6px 0 0;">' + esc(c.transcription) + '</p>'
      : '<p class="muted" style="margin:6px 0 0;">No transcript available.</p>';
    var callerType = c.first_call
      ? "First-time caller"
      : "Returning caller (" + c.total_calls + " total call" + (c.total_calls === 1 ? "" : "s") + (c.prior_calls ? ", " + c.prior_calls + " prior" : "") + ")";

    return '' +
      '<dl class="call-detail-grid">' +
        '<dt>Call length</dt><dd>' + formatDuration(c.duration) + '</dd>' +
        '<dt>Forwarded to</dt><dd>' + esc(c.business_phone_masked) + '</dd>' +
        '<dt>Caller history</dt><dd>' + esc(callerType) + '</dd>' +
        (c.source_name ? '<dt>Source</dt><dd>' + esc(c.source_name) + '</dd>' : '') +
        (c.medium ? '<dt>Medium</dt><dd>' + esc(c.medium) + '</dd>' : '') +
        (c.device_type ? '<dt>Device</dt><dd>' + esc(c.device_type) + '</dd>' : '') +
        (c.keywords ? '<dt>Keywords</dt><dd>' + esc(c.keywords) + '</dd>' : '') +
        (c.landing_page_url ? '<dt>Landing page</dt><dd><a href="' + esc(c.landing_page_url) + '" target="_blank" rel="noopener">' + esc(c.landing_page_url) + '</a></dd>' : '') +
        '<dt>Tags</dt><dd>' + tagsHtml + '</dd>' +
      '</dl>' +
      '<div style="margin-top:10px;"><strong>Recording</strong>' + recordingHtml + '</div>' +
      '<div style="margin-top:10px;"><strong>Transcript</strong>' + transcriptHtml + '</div>';
  }

  function renderList(root, calls) {
    var el = root.querySelector("#calls-list");
    if (!el) return;
    if (!calls.length) {
      el.innerHTML = '<div class="info-box" style="text-align:center;"><h3>No calls yet</h3>' +
        '<p class="muted" style="margin:0;">Inbound calls to the site will show up here as they come in.</p></div>';
      return;
    }
    var now = Date.now();
    el.innerHTML = calls.map(function (c) {
      var isNew = (now - new Date(c.start_time).getTime()) < NEW_WINDOW_MS;
      var displayName = c.customer_name || c.customer_phone_masked || "Unknown Caller";
      return '' +
        '<details class="call-row">' +
          '<summary>' +
            '<div class="call-row-main">' +
              '<div class="call-row-badges">' +
                '<span class="tag verified-lead">&#10003; Verified</span>' +
                (isNew ? '<span class="tag new">New</span>' : '') +
              '</div>' +
              '<div class="call-row-name">' + esc(displayName) + '</div>' +
              '<div class="call-row-time">' + formatDateTime(c.start_time) + '</div>' +
            '</div>' +
            '<div class="call-row-side">' +
              '<span class="muted">' + formatDuration(c.duration) + '</span>' +
              statusBadge(c) +
            '</div>' +
          '</summary>' +
          '<div class="call-row-detail">' + callDetailHtml(c) + '</div>' +
        '</details>';
    }).join("");
  }

  function init() {
    var root = document.querySelector(".calls-panel");
    if (!root) return;
    root.querySelectorAll("[id^='calls-']").forEach(function (el) { el.setAttribute("data-calls-fill", ""); });

    fetchCalls().then(function (data) {
      var calls = data.calls || [];
      renderStats(root, calls, data.totalRecords || calls.length);
      renderTrendChart(root, calls);
      renderList(root, calls);
    }).catch(function (err) {
      renderError(root, "Lead-call tracking isn't fully connected yet. Check back soon.");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
