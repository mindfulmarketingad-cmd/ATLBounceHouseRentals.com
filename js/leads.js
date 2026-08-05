/* Leads leaderboard — pulls real leads from Supabase.
   Three tiers:
   - Not logged in / not subscribed: name only. Every other field is
     genuinely never sent by the server (public.leads_board view only
     exposes id/name/created_at), so there's nothing for devtools or
     view-source to reveal — the blur you see is real placeholder text,
     not hidden real data.
   - Logged in + active row in public.subscribers: full lead details.
   - Logged in as the site admin email: full lead details.
   Requires supabase/schema.sql and supabase/schema_leads_board.sql to
   have been run in the Supabase project.
*/
(function () {
  "use strict";

  var SUPABASE_URL = "https://tbqigevoksabizjogvtm.supabase.co";
  var SUPABASE_ANON_KEY = "sb_publishable_aHlx0Tdu2rhOTBUp3lhkQw_Lv6Awz7a";
  var ADMIN_EMAIL = "mindfulmarketingad@gmail.com";
  var STRIPE_SUBSCRIBE_URL = "https://buy.stripe.com/00wdRa5U644Ed6S6dwfrW0i";

  var supa = null;
  var currentUser = null;
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

  function initClient() {
    if (!window.supabase || !window.supabase.createClient) return null;
    return window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  }

  function checkEntitlement(user) {
    if (!user) return Promise.resolve(false);
    var email = (user.email || "").toLowerCase();
    if (email === ADMIN_EMAIL) return Promise.resolve(true);
    return supa.from("subscribers").select("active").eq("email", email).eq("active", true).maybeSingle()
      .then(function (res) { return !!(res && res.data && !res.error); })
      .catch(function () { return false; });
  }

  function fetchPublicBoard() {
    return supa.from("leads_board").select("id,name,created_at").order("created_at", { ascending: false }).limit(50)
      .then(function (res) { return (res && res.data) || []; })
      .catch(function () { return []; });
  }

  function fetchFullBoard() {
    return supa.from("leads").select("*")
      .ilike("page_url", "%atlbouncehouserentals.com%")
      .order("created_at", { ascending: false }).limit(50)
      .then(function (res) { return (res && res.data) || []; })
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
    board.innerHTML = rows.map(function (l) {
      return '' +
        '<article class="lead-row locked">' +
          '<div class="lead-main">' +
            '<h3>' + esc(l.name || "New Inquiry") + '</h3>' +
            '<div class="muted" style="font-size:0.9rem;"><span class="lead-protect">Birthday Party &middot; ZIP 30xxx</span></div>' +
            '<p style="margin:8px 0 0;font-size:0.92rem;"><span class="lead-protect">(xxx) xxx-xxxx &middot; hidden@email.com</span></p>' +
            '<div class="lead-tags"><span class="tag new">New</span><span class="tag">Website</span></div>' +
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
    board.innerHTML = rows.map(function (l) {
      var svc = (l.services || []).join(", ") || l.event_type || "General Inquiry";
      var phoneDigits = (l.phone || "").replace(/[^+\d]/g, "");
      var tags = ['<span class="tag new">New</span>', '<span class="tag">' + esc(l.source || "Website Quote Form") + '</span>'];
      if (l.zip_code) tags.push('<span class="tag">ZIP ' + esc(l.zip_code) + '</span>');
      if (l.event_date) tags.push('<span class="tag">Event: ' + esc(l.event_date) + '</span>');
      if (l.guest_count) tags.push('<span class="tag">' + esc(l.guest_count) + ' guests</span>');
      return '' +
        '<article class="lead-row">' +
          '<div class="lead-main">' +
            '<h3>' + esc(l.name || "New Inquiry") + ' &mdash; ' + esc(svc) + '</h3>' +
            '<div class="muted" style="font-size:0.9rem;">' + esc(l.phone || "") + ' &middot; ' + esc(l.email || "") + '</div>' +
            '<p style="margin:8px 0 0;font-size:0.92rem;">' + esc(l.message || "Submitted via website Free Instant Quote form.") + '</p>' +
            '<div class="lead-tags">' + tags.join("") + '</div>' +
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
    if (!board || !supa) return Promise.resolve();
    renderLoading(board);

    if (isEntitled) {
      setDisplay("login-banner", "none");
      setDisplay("subscribe-banner", "none");
      setDisplay("logged-bar", "flex");
      return fetchFullBoard().then(function (rows) { renderFull(board, rows); });
    }

    setDisplay("logged-bar", "none");
    if (currentUser) {
      setDisplay("login-banner", "none");
      setDisplay("subscribe-banner", "flex");
    } else {
      setDisplay("login-banner", "flex");
      setDisplay("subscribe-banner", "none");
    }
    return fetchPublicBoard().then(function (rows) { renderLocked(board, rows); });
  }

  function refreshSession() {
    return supa.auth.getSession().then(function (res) {
      var session = res && res.data && res.data.session;
      currentUser = session ? session.user : null;
      return checkEntitlement(currentUser);
    }).then(function (entitled) {
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
        supa.auth.signInWithPassword({ email: email, password: password }).then(function (res) {
          if (res.error) {
            if (err) { err.textContent = res.error.message || "Incorrect email or password."; err.style.display = "block"; }
            return;
          }
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
        supa.auth.signUp({ email: email, password: password }).then(function (res) {
          if (!signupMsg) return;
          signupMsg.style.display = "block";
          if (res.error) {
            signupMsg.textContent = res.error.message || "Something went wrong creating your account.";
          } else {
            signupMsg.textContent = "Account created! Check your email to confirm it, then log in and subscribe to unlock full lead details.";
            signupForm.reset();
          }
        });
      });
    }

    var logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", function () {
        supa.auth.signOut().then(refreshSession);
      });
    }
  }

  function init() {
    supa = initClient();
    var board = document.getElementById("leads-board");
    if (!supa) {
      if (board) board.innerHTML = '<div class="info-box" style="text-align:center;"><h3>Unable to load leads</h3><p class="muted" style="margin:0;">Please refresh the page.</p></div>';
      return;
    }
    wireAuthForms();
    refreshSession();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
