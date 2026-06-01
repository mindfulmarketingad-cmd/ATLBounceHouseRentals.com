/* Leads board: login gating + blur for anonymous visitors.
   Shows only real leads captured from the website quote form (and, in
   production, your phone line). No demo/seed leads.
   NOTE: This is a front-end demonstration of the gating UX. For production,
   replace the demo auth with real server-side authentication + a database
   so lead contact details are never sent to anonymous browsers. */
(function () {
  "use strict";

  var AUTH_KEY = "abhr_auth";
  // Demo partner credentials. Replace with real auth in production.
  var DEMO_USER = "partner@atlbouncehouserentals.com";
  var DEMO_PASS = "atlanta2026";

  function timeAgo(iso) {
    var s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
    if (isNaN(s)) return "";
    if (s < 60) return "just now";
    var m = Math.floor(s / 60); if (m < 60) return m + " min ago";
    var hr = Math.floor(m / 60); if (hr < 24) return hr + " hr ago";
    var d = Math.floor(hr / 24); return d + " day" + (d > 1 ? "s" : "") + " ago";
  }
  function esc(str) {
    return String(str || "").replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function getStoredLeads() {
    try { return JSON.parse(localStorage.getItem("abhr_leads") || "[]"); }
    catch (e) { return []; }
  }
  function isLoggedIn() {
    try { return localStorage.getItem(AUTH_KEY) === "1"; } catch (e) { return false; }
  }

  function allLeads() {
    return getStoredLeads().map(function (l) {
      return {
        id: l.id, name: l.name || "New Inquiry", phone: l.phone, email: l.email,
        service: l.service || "General Inquiry", date: l.date, zip: l.zip,
        area: l.zip ? ("ZIP " + l.zip) : "Atlanta, GA",
        message: l.message || "Submitted via website quote form.",
        source: l.source || "Website Quote Form", created: l.created, tags: ["New", "Website"]
      };
    }).sort(function (a, b) { return new Date(b.created) - new Date(a.created); });
  }

  function render() {
    var board = document.getElementById("leads-board");
    if (!board) return;
    var loggedIn = isLoggedIn();
    var leads = allLeads();

    var banner = document.getElementById("login-banner");
    var loggedBar = document.getElementById("logged-bar");
    if (banner) banner.style.display = loggedIn ? "none" : "flex";
    if (loggedBar) loggedBar.style.display = loggedIn ? "flex" : "none";

    if (!leads.length) {
      board.innerHTML = '<div class="info-box" style="text-align:center;">' +
        '<h3>No new leads yet</h3>' +
        '<p class="muted" style="margin:0;">New inquiries from the website quote form and phone line will appear here in real time.</p>' +
        '</div>';
      return;
    }

    board.innerHTML = leads.map(function (l) {
      var locked = !loggedIn;
      var contact = locked
        ? '<span class="lead-protect">' + esc(l.phone || "+1 (xxx) xxx-xxxx") + ' &middot; ' + esc(l.email || "hidden@email.com") + '</span>'
        : esc(l.phone || "") + ' &middot; ' + esc(l.email || "");
      var msg = locked ? '<span class="lead-protect">' + esc(l.message) + '</span>' : esc(l.message);
      var side = locked
        ? '<span class="lock-pill">Locked</span>'
        : '<a class="btn" href="tel:' + esc((l.phone || "").replace(/[^+\d]/g, "")) + '">Call Lead</a>';
      var tags = (l.tags || []).map(function (t) {
        return '<span class="tag' + (t === "New" ? " new" : "") + '">' + esc(t) + '</span>';
      }).join("");
      return '' +
        '<article class="lead-row' + (locked ? " locked" : "") + '">' +
          '<div class="lead-main">' +
            '<h3>' + esc(l.service) + ' &mdash; ' + esc(l.area) + '</h3>' +
            '<div class="muted" style="font-size:0.9rem;">' + contact + '</div>' +
            '<p style="margin:8px 0 0;font-size:0.92rem;">' + msg + '</p>' +
            '<div class="lead-tags">' + tags + '<span class="tag">' + esc(l.source) + '</span>' +
              (l.date ? '<span class="tag">Event: ' + esc(l.date) + '</span>' : '') + '</div>' +
          '</div>' +
          '<div class="lead-side">' +
            '<div class="lead-time">' + timeAgo(l.created) + '</div>' +
            '<div style="margin-top:10px;">' + side + '</div>' +
          '</div>' +
        '</article>';
    }).join("");
  }

  function wire() {
    var modal = document.getElementById("login-modal");
    var openers = document.querySelectorAll("[data-open-login]");
    var closers = document.querySelectorAll("[data-close-login]");
    var loginForm = document.getElementById("login-form");
    var logoutBtn = document.getElementById("logout-btn");
    var err = document.getElementById("login-error");

    openers.forEach(function (b) { b.addEventListener("click", function () { if (modal) modal.classList.add("open"); }); });
    closers.forEach(function (b) { b.addEventListener("click", function () { if (modal) modal.classList.remove("open"); }); });
    if (modal) modal.addEventListener("click", function (e) { if (e.target === modal) modal.classList.remove("open"); });

    if (loginForm) {
      loginForm.addEventListener("submit", function (e) {
        e.preventDefault();
        var u = loginForm.email.value.trim().toLowerCase();
        var p = loginForm.password.value;
        if (u === DEMO_USER && p === DEMO_PASS) {
          try { localStorage.setItem(AUTH_KEY, "1"); } catch (e2) {}
          if (modal) modal.classList.remove("open");
          if (err) err.style.display = "none";
          loginForm.reset();
          render();
        } else if (err) {
          err.style.display = "block";
        }
      });
    }
    if (logoutBtn) {
      logoutBtn.addEventListener("click", function () {
        try { localStorage.removeItem(AUTH_KEY); } catch (e) {}
        render();
      });
    }
  }

  document.addEventListener("DOMContentLoaded", function () { wire(); render(); });
})();
