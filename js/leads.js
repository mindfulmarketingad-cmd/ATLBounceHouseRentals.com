/* Leads leaderboard — pulls real leads from Supabase.
   No external dependencies (plain fetch against Supabase's REST + Auth
   HTTP APIs, same pattern wizard.js already uses) — nothing to fail to
   load from a CDN.

   Three tiers:
   - Not logged in / not subscribed: name only. Every other field is
     genuinely never sent by the server (public.leads_board view only
     exposes id/name/created_at), so there's nothing for devtools or
     view-source to reveal — the blur you see is real placeholder text,
     not hidden real data.
   - Logged in + active row in public.subscribers: full lead details.
   - Logged in as the site admin email: full lead details.
   Requires supabase/schema.sql and supabase/schema_leads_board.sql to
   have been run in the Supabase project (named
   ATLBounceHouseRentals_Leads_Board in the Supabase dashboard).
*/
(function () {
  "use strict";

  var SUPABASE_URL = "https://tbqigevoksabizjogvtm.supabase.co";
  var SUPABASE_ANON_KEY = "sb_publishable_aHlx0Tdu2rhOTBUp3lhkQw_Lv6Awz7a";
  var ADMIN_EMAIL = "mindfulmarketingad@gmail.com";
  var STRIPE_SUBSCRIBE_URL = "https://buy.stripe.com/00wdRa5U644Ed6S6dwfrW0i";
  var SESSION_KEY = "abhr_leads_session";

  var session = null; // { access_token, refresh_token, user }
  var isEntitled = false;

  function esc(str) {
    return String(str || "").replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function timeAgo(iso) {
    var s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
    if (isNaN(s)) return "";
    if (s < 60) return "just now";
    var m = Math.floor(s / 60); if (m < 60) return m + " min ago";
    var hr = Math.floor(m / 60); if (hr < 24) return hr + " hr ago";
    var d = Math.floor(hr / 24); return d + " day" + (d > 1 ? "s" : "") + " ago";
  }

  function exactTime(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    try {
      return d.toLocaleString("en-US", {
        timeZone: "America/New_York", month: "short", day: "numeric",
        year: "numeric", hour: "numeric", minute: "2-digit"
      }) + " ET";
    } catch (e) {
      return d.toLocaleString();
    }
  }

  function verifiedBadge() {
    return '<span class="tag verified-lead">&#10003; Verified Lead</span>';
  }

  function loadSession() {
    try {
      var raw = localStorage.getItem(SESSION_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }
  function saveSession(s) {
    session = s;
    try {
      if (s) localStorage.setItem(SESSION_KEY, JSON.stringify(s));
      else localStorage.removeItem(SESSION_KEY);
    } catch (e) { /* ignore */ }
  }

  function authHeaders() {
    var token = (session && session.access_token) || SUPABASE_ANON_KEY;
    return {
      "apikey": SUPABASE_ANON_KEY,
      "Authorization": "Bearer " + token
    };
  }

  function authFetch(path, opts) {
    opts = opts || {};
    opts.headers = Object.assign({ "Content-Type": "application/json" }, authHeaders(), opts.headers || {});
    return fetch(SUPABASE_URL + path, opts);
  }

  function signUp(email, password) {
    return fetch(SUPABASE_URL + "/auth/v1/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json", "apikey": SUPABASE_ANON_KEY },
      body: JSON.stringify({ email: email, password: password })
    }).then(function (res) {
      return res.json().then(function (body) { return { ok: res.ok, body: body }; });
    });
  }

  function signIn(email, password) {
    return fetch(SUPABASE_URL + "/auth/v1/token?grant_type=password", {
      method: "POST",
      headers: { "Content-Type": "application/json", "apikey": SUPABASE_ANON_KEY },
      body: JSON.stringify({ email: email, password: password })
    }).then(function (res) {
      return res.json().then(function (body) { return { ok: res.ok, body: body }; });
    });
  }

  function signOut() {
    if (!session) return Promise.resolve();
    return fetch(SUPABASE_URL + "/auth/v1/logout", {
      method: "POST",
      headers: { "apikey": SUPABASE_ANON_KEY, "Authorization": "Bearer " + session.access_token }
    }).catch(function () { /* ignore network errors on logout */ });
  }

  function checkEntitlement() {
    if (!session || !session.user) return Promise.resolve(false);
    var email = (session.user.email || "").toLowerCase();
    if (email === ADMIN_EMAIL) return Promise.resolve(true);
    var url = "/rest/v1/subscribers?select=active&email=eq." + encodeURIComponent(email) + "&active=eq.true&limit=1";
    return authFetch(url).then(function (res) {
      if (!res.ok) return false;
      return res.json();
    }).then(function (rows) {
      return Array.isArray(rows) && rows.length > 0;
    }).catch(function () { return false; });
  }

  function fetchPublicBoard() {
    return authFetch("/rest/v1/leads_board?select=id,name,created_at&order=created_at.desc&limit=50")
      .then(function (res) { return res.ok ? res.json() : []; })
      .catch(function () { return []; });
  }

  function fetchFullBoard() {
    var url = "/rest/v1/leads?select=*&page_url=ilike.*atlbouncehouserentals.com*&order=created_at.desc&limit=50";
    return authFetch(url)
      .then(function (res) { return res.ok ? res.json() : []; })
      .catch(function () { return []; });
  }

  function renderLoading(board) {
    board.innerHTML = '<div class="info-box" style="text-align:center;"><h3>Loading leads&hellip;</h3></div>';
  }

  function renderEmpty(board) {
    board.innerHTML = '<div class="info-box" style="text-align:center;">' +
      '<h3>No leads yet</h3>' +
      '<p class="muted" style="margin:0;">New inquiries from the website Free Instant Quote form will appear here in real time.</p>' +
      '</div>';
  }

  function renderLocked(board, rows) {
    if (!rows.length) return renderEmpty(board);
    board.innerHTML = rows.map(function (l, i) {
      return '' +
        '<article class="lead-row locked">' +
          '<div class="lead-main">' +
            '<div class="lead-tags">' + verifiedBadge() + '<span class="tag new">New</span><span class="tag">Website</span></div>' +
            '<h3><span class="lead-num">#' + (rows.length - i) + '</span> ' + esc(l.name || "New Inquiry") + '</h3>' +
            '<div class="muted" style="font-size:0.9rem;"><span class="lead-protect">Birthday Party &middot; ZIP 30xxx</span></div>' +
            '<p style="margin:8px 0 0;font-size:0.92rem;"><span class="lead-protect">(xxx) xxx-xxxx &middot; hidden@email.com</span></p>' +
            '<div class="lead-received">Received ' + esc(exactTime(l.created_at)) + '</div>' +
          '</div>' +
          '<div class="lead-side">' +
            '<div class="lead-time">' + timeAgo(l.created_at) + '</div>' +
            '<div style="margin-top:10px;"><span class="lock-pill">&#128274; Subscriber Only</span></div>' +
          '</div>' +
        '</article>';
    }).join("");
  }

  function renderFull(board, rows) {
    if (!rows.length) return renderEmpty(board);
    board.innerHTML = rows.map(function (l, i) {
      var svc = (l.services || []).join(", ") || l.event_type || "General Inquiry";
      var phoneDigits = (l.phone || "").replace(/[^+\d]/g, "");
      var tags = [verifiedBadge(), '<span class="tag new">New</span>', '<span class="tag">' + esc(l.source || "Website Quote Form") + '</span>'];
      if (l.zip_code) tags.push('<span class="tag">ZIP ' + esc(l.zip_code) + '</span>');
      if (l.event_date) tags.push('<span class="tag">Event: ' + esc(l.event_date) + '</span>');
      if (l.guest_count) tags.push('<span class="tag">' + esc(l.guest_count) + ' guests</span>');
      return '' +
        '<article class="lead-row">' +
          '<div class="lead-main">' +
            '<div class="lead-tags">' + tags.join("") + '</div>' +
            '<h3><span class="lead-num">#' + (rows.length - i) + '</span> ' + esc(l.name || "New Inquiry") + ' &mdash; ' + esc(svc) + '</h3>' +
            '<div class="muted" style="font-size:0.9rem;">' + esc(l.phone || "") + ' &middot; ' + esc(l.email || "") + '</div>' +
            '<p style="margin:8px 0 0;font-size:0.92rem;">' + esc(l.message || "Submitted via website Free Instant Quote form.") + '</p>' +
            '<div class="lead-received">Received ' + esc(exactTime(l.created_at)) + '</div>' +
          '</div>' +
          '<div class="lead-side">' +
            '<div class="lead-time">' + timeAgo(l.created_at) + '</div>' +
            '<div style="margin-top:10px;">' + (phoneDigits ? '<a class="btn" href="tel:' + esc(phoneDigits) + '">Call Lead</a>' : '') + '</div>' +
          '</div>' +
        '</article>';
    }).join("");
  }

  function setDisplay(id, value) {
    var el = document.getElementById(id);
    if (el) el.style.display = value;
  }

  function refresh() {
    var board = document.getElementById("leads-board");
    if (!board) return Promise.resolve();
    renderLoading(board);

    if (isEntitled) {
      setDisplay("login-banner", "none");
      setDisplay("subscribe-banner", "none");
      setDisplay("logged-bar", "flex");
      return fetchFullBoard().then(function (rows) { renderFull(board, rows); });
    }

    setDisplay("logged-bar", "none");
    if (session && session.user) {
      setDisplay("login-banner", "none");
      setDisplay("subscribe-banner", "flex");
    } else {
      setDisplay("login-banner", "flex");
      setDisplay("subscribe-banner", "none");
    }
    return fetchPublicBoard().then(function (rows) { renderLocked(board, rows); });
  }

  function refreshSession() {
    return checkEntitlement().then(function (entitled) {
      isEntitled = entitled;
      return refresh();
    });
  }

  function wireAuthForms() {
    var modal = document.getElementById("login-modal");
    document.querySelectorAll("[data-open-login]").forEach(function (b) {
      b.addEventListener("click", function () { if (modal) modal.classList.add("open"); });
    });
    document.querySelectorAll("[data-close-login]").forEach(function (b) {
      b.addEventListener("click", function () { if (modal) modal.classList.remove("open"); });
    });
    if (modal) modal.addEventListener("click", function (e) { if (e.target === modal) modal.classList.remove("open"); });

    var loginForm = document.getElementById("login-form");
    var err = document.getElementById("login-error");
    if (loginForm) {
      loginForm.addEventListener("submit", function (e) {
        e.preventDefault();
        if (err) err.style.display = "none";
        var email = loginForm.email.value.trim();
        var password = loginForm.password.value;
        signIn(email, password).then(function (res) {
          if (!res.ok || !res.body || !res.body.access_token) {
            if (err) {
              err.textContent = (res.body && (res.body.error_description || res.body.msg)) || "Incorrect email or password.";
              err.style.display = "block";
            }
            return;
          }
          saveSession({
            access_token: res.body.access_token,
            refresh_token: res.body.refresh_token,
            user: res.body.user
          });
          loginForm.reset();
          if (modal) modal.classList.remove("open");
          return refreshSession();
        });
      });
    }

    var signupForm = document.getElementById("signup-form");
    var signupMsg = document.getElementById("signup-message");
    if (signupForm) {
      signupForm.addEventListener("submit", function (e) {
        e.preventDefault();
        if (signupMsg) signupMsg.style.display = "none";
        var email = signupForm.email.value.trim();
        var password = signupForm.password.value;
        signUp(email, password).then(function (res) {
          if (!signupMsg) return;
          signupMsg.style.display = "block";
          if (!res.ok) {
            signupMsg.textContent = (res.body && (res.body.error_description || res.body.msg)) || "Something went wrong creating your account.";
            return;
          }
          signupForm.reset();
          if (res.body && res.body.access_token) {
            saveSession({ access_token: res.body.access_token, refresh_token: res.body.refresh_token, user: res.body.user });
            signupMsg.textContent = "Account created! Now subscribe to unlock full lead details.";
            refreshSession();
          } else {
            signupMsg.textContent = "Account created! Check your email to confirm it, then log in and subscribe to unlock full lead details.";
          }
        });
      });
    }

    var logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", function () {
        signOut().then(function () {
          saveSession(null);
          isEntitled = false;
          return refresh();
        });
      });
    }
  }

  function init() {
    var board = document.getElementById("leads-board");
    if (!board) return;
    session = loadSession();
    wireAuthForms();
    refreshSession();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
