/* Leads board: login gating + blur for anonymous visitors.
   NOTE: This is a front-end demonstration. For production, replace the
   demo auth with a real server-side authentication + database backend
   so lead contact details are never sent to anonymous browsers. */
(function () {
  "use strict";

  var AUTH_KEY = "abhr_auth";
  // Demo partner credentials. Replace with real auth in production.
  var DEMO_USER = "partner@atlbouncehouserentals.com";
  var DEMO_PASS = "atlanta2026";

  // Seed leads (simulating quote form + VAPI phone leads).
  var SEED = [
    { id:"S1", name:"Marcus T.", phone:"+1 (404) 555-0192", email:"marcus.t@email.com", service:"Water Slide Rentals", date:"2026-06-14", zip:"30309", area:"Midtown Atlanta", message:"Need a large water slide for a 9-yr-old birthday, ~30 kids.", source:"VAPI Phone Line", created:hoursAgo(1), tags:["New","Phone","Large Job"] },
    { id:"S2", name:"Priya R.", phone:"+1 (678) 555-0144", email:"priya.r@email.com", service:"Party Package Rentals", date:"2026-06-21", zip:"30316", area:"East Atlanta", message:"Full package: bounce house, tables, chairs and concessions for a graduation party.", source:"Website Quote Form", created:hoursAgo(3), tags:["New","Package"] },
    { id:"S3", name:"DeShawn W.", phone:"+1 (470) 555-0177", email:"deshawn.w@email.com", service:"Obstacle Course Rentals", date:"2026-07-04", zip:"30331", area:"Southwest Atlanta", message:"July 4th block party, looking for a large obstacle course.", source:"VAPI Phone Line", created:hoursAgo(6), tags:["Phone","Large Job"] },
    { id:"S4", name:"Emily C.", phone:"+1 (404) 555-0108", email:"emily.c@email.com", service:"Classic Bounce House Rentals", date:"2026-06-08", zip:"30307", area:"Inman Park", message:"Small backyard party, standard bounce house for one afternoon.", source:"Website Quote Form", created:hoursAgo(11), tags:["Small Job"] },
    { id:"S5", name:"Robert & Lina G.", phone:"+1 (678) 555-0136", email:"the.gs@email.com", service:"Tents, Tables and Chair Rentals", date:"2026-08-02", zip:"30342", area:"Sandy Springs", message:"Backyard wedding reception, need a 20x40 tent plus seating for 80.", source:"Website Quote Form", created:hoursAgo(20), tags:["Large Job"] },
    { id:"S6", name:"Tasha M.", phone:"+1 (470) 555-0163", email:"tasha.m@email.com", service:"Concession Rentals", date:"2026-06-29", zip:"30315", area:"South Atlanta", message:"Popcorn and snow cone machines for a community fundraiser.", source:"VAPI Phone Line", created:hoursAgo(28), tags:["Phone"] }
  ];

  function hoursAgo(h){ return new Date(Date.now() - h*3600*1000).toISOString(); }
  function timeAgo(iso){
    var s = Math.floor((Date.now()-new Date(iso).getTime())/1000);
    if (s < 60) return "just now";
    var m = Math.floor(s/60); if (m < 60) return m+" min ago";
    var hr = Math.floor(m/60); if (hr < 24) return hr+" hr ago";
    var d = Math.floor(hr/24); return d+" day"+(d>1?"s":"")+" ago";
  }
  function esc(str){ return String(str||"").replace(/[&<>"]/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]; }); }

  function getStoredLeads(){
    try { return JSON.parse(localStorage.getItem("abhr_leads") || "[]"); }
    catch(e){ return []; }
  }
  function isLoggedIn(){
    try { return localStorage.getItem(AUTH_KEY) === "1"; } catch(e){ return false; }
  }
  function srcIcon(src){ return /phone|vapi/i.test(src) ? "📞" : "📝"; }

  function allLeads(){
    // Combine user-submitted (from quote form) with seed leads, newest first.
    var submitted = getStoredLeads().map(function(l){
      return {
        id:l.id, name:l.name||"New Inquiry", phone:l.phone, email:l.email,
        service:l.service||"General Inquiry", date:l.date, zip:l.zip,
        area: l.zip ? ("ZIP "+l.zip) : "Atlanta, GA",
        message:l.message||"Submitted via website quote form.",
        source:l.source||"Website Quote Form", created:l.created,
        tags:["New","Website"]
      };
    });
    return submitted.concat(SEED).sort(function(a,b){
      return new Date(b.created) - new Date(a.created);
    });
  }

  function render(){
    var board = document.getElementById("leads-board");
    if (!board) return;
    var loggedIn = isLoggedIn();
    var leads = allLeads();

    var banner = document.getElementById("login-banner");
    var loggedBar = document.getElementById("logged-bar");
    if (banner) banner.style.display = loggedIn ? "none" : "flex";
    if (loggedBar) loggedBar.style.display = loggedIn ? "flex" : "none";

    board.innerHTML = leads.map(function(l){
      var locked = !loggedIn;
      var contact = locked
        ? '<span class="lead-protect">'+esc(l.phone||"+1 (xxx) xxx-xxxx")+' &middot; '+esc(l.email||"hidden@email.com")+'</span>'
        : esc(l.phone||"")+' &middot; '+esc(l.email||"");
      var msg = locked
        ? '<span class="lead-protect">'+esc(l.message)+'</span>'
        : esc(l.message);
      var side = locked
        ? '<span class="lock-pill">🔒 Locked</span>'
        : '<a class="btn" href="tel:'+esc((l.phone||"").replace(/[^+\d]/g,""))+'">Call Lead</a>';
      var tags = (l.tags||[]).map(function(t){
        return '<span class="tag'+(t==="New"?" new":"")+'">'+esc(t)+'</span>';
      }).join("");
      return ''+
        '<article class="lead-row'+(locked?" locked":"")+'">'+
          '<div class="src" title="'+esc(l.source)+'">'+srcIcon(l.source)+'</div>'+
          '<div class="lead-main">'+
            '<h3>'+esc(l.service)+' &mdash; '+esc(l.area)+'</h3>'+
            '<div class="muted" style="font-size:0.9rem;">'+contact+'</div>'+
            '<p style="margin:8px 0 0;font-size:0.92rem;">'+msg+'</p>'+
            '<div class="lead-tags">'+tags+'<span class="tag">'+esc(l.source)+'</span>'+
              (l.date?'<span class="tag">Event: '+esc(l.date)+'</span>':'')+'</div>'+
          '</div>'+
          '<div class="lead-side">'+
            '<div class="lead-time">'+timeAgo(l.created)+'</div>'+
            '<div style="margin-top:10px;">'+side+'</div>'+
          '</div>'+
        '</article>';
    }).join("");
  }

  // Modal + auth wiring
  function wire(){
    var modal = document.getElementById("login-modal");
    var openers = document.querySelectorAll("[data-open-login]");
    var closers = document.querySelectorAll("[data-close-login]");
    var loginForm = document.getElementById("login-form");
    var logoutBtn = document.getElementById("logout-btn");
    var err = document.getElementById("login-error");

    openers.forEach(function(b){ b.addEventListener("click", function(){ if(modal) modal.classList.add("open"); }); });
    closers.forEach(function(b){ b.addEventListener("click", function(){ if(modal) modal.classList.remove("open"); }); });
    if (modal) modal.addEventListener("click", function(e){ if(e.target===modal) modal.classList.remove("open"); });

    if (loginForm) {
      loginForm.addEventListener("submit", function(e){
        e.preventDefault();
        var u = loginForm.email.value.trim().toLowerCase();
        var p = loginForm.password.value;
        if (u === DEMO_USER && p === DEMO_PASS) {
          try { localStorage.setItem(AUTH_KEY, "1"); } catch(err2){}
          if (modal) modal.classList.remove("open");
          if (err) err.style.display = "none";
          loginForm.reset();
          render();
        } else {
          if (err) err.style.display = "block";
        }
      });
    }
    if (logoutBtn) {
      logoutBtn.addEventListener("click", function(){
        try { localStorage.removeItem(AUTH_KEY); } catch(e){}
        render();
      });
    }
  }

  document.addEventListener("DOMContentLoaded", function(){ wire(); render(); });
})();
