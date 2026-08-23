/* Atlanta Bounce House Rentals — /cart/ page.
   Renders the localStorage cart (js/cart.js) and submits one combined
   request across every item to the Supabase `leads` table — see
   supabase/migrate_cart_orders.sql for the columns this writes.
*/
(function () {
  "use strict";

  var SUPABASE_URL = "https://tbqigevoksabizjogvtm.supabase.co";
  var SUPABASE_ANON_KEY = "sb_publishable_aHlx0Tdu2rhOTBUp3lhkQw_Lv6Awz7a";

  var layout = document.getElementById("cart-layout");
  if (!layout) return;
  var DELIVERY_FEE = parseFloat(layout.getAttribute("data-delivery-fee")) || 0;

  var emptyEl = document.getElementById("cart-empty");
  var itemsEl = document.getElementById("cart-items");
  var summaryLinesEl = document.getElementById("cart-summary-lines");
  var summaryTotalEl = document.getElementById("cart-summary-total");
  var formSummaryEl = document.getElementById("cart-form-summary");
  var formTotalEl = document.getElementById("cart-form-total");
  var checkoutSection = document.getElementById("cart-checkout");

  function money(n) {
    return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function rowHtml(item) {
    var lineTotal = item.qty * item.price;
    return (
      '<div class="cart-row" data-cart-row data-slug="' + item.slug + '">' +
        '<div class="cart-row-info">' +
          '<a href="' + item.href + '">' + item.name + '</a>' +
          (item.parentName ? '<span class="muted">' + item.parentName + '</span>' : '') +
        '</div>' +
        '<div class="cart-row-qty">' +
          '<button type="button" class="pr-qty-btn" data-cart-qty-step="-1" aria-label="Decrease quantity">&minus;</button>' +
          '<input type="number" min="' + (item.minQty || 1) + '" step="1" value="' + item.qty + '" data-cart-qty>' +
          '<button type="button" class="pr-qty-btn" data-cart-qty-step="1" aria-label="Increase quantity">+</button>' +
        '</div>' +
        '<div class="cart-row-price muted">' + money(item.price) + ' / ' + item.unit + '</div>' +
        '<div class="cart-row-total">' + money(lineTotal) + '</div>' +
        '<button type="button" class="cart-row-remove" data-cart-remove aria-label="Remove ' + item.name + '">&times;</button>' +
      '</div>'
    );
  }

  var justSubmitted = false;

  function render() {
    var items = window.ABHRCart.get();
    if (!items.length) {
      itemsEl.innerHTML = "";
      emptyEl.hidden = false;
      layout.hidden = true;
      checkoutSection.hidden = justSubmitted ? false : true;
      return;
    }
    emptyEl.hidden = true;
    layout.hidden = false;
    checkoutSection.hidden = false;

    itemsEl.innerHTML = items.map(rowHtml).join("");

    var subtotal = window.ABHRCart.itemsTotal(items);
    var total = subtotal + DELIVERY_FEE;
    var count = window.ABHRCart.count(items);

    summaryLinesEl.innerHTML =
      '<div class="cart-summary-row"><span>' + count + ' item' + (count === 1 ? "" : "s") + '</span><span>' + money(subtotal) + '</span></div>' +
      '<div class="cart-summary-row"><span>Standard delivery fee</span><span>' + money(DELIVERY_FEE) + '</span></div>';
    summaryTotalEl.textContent = money(total);

    var summary = count + " item" + (count === 1 ? "" : "s") + " × subtotal " + money(subtotal) + " + " + money(DELIVERY_FEE) + " delivery";
    if (formSummaryEl) formSummaryEl.textContent = summary;
    if (formTotalEl) formTotalEl.textContent = money(total);
  }

  itemsEl.addEventListener("click", function (e) {
    var row = e.target.closest("[data-cart-row]");
    if (!row) return;
    var slug = row.getAttribute("data-slug");

    var stepBtn = e.target.closest("[data-cart-qty-step]");
    if (stepBtn) {
      var input = row.querySelector("[data-cart-qty]");
      var step = parseInt(stepBtn.getAttribute("data-cart-qty-step"), 10) || 0;
      var next = Math.max(parseInt(input.min, 10) || 1, (parseInt(input.value, 10) || 1) + step);
      window.ABHRCart.updateQty(slug, next);
      return;
    }
    if (e.target.closest("[data-cart-remove]")) {
      window.ABHRCart.remove(slug);
    }
  });

  itemsEl.addEventListener("change", function (e) {
    var input = e.target.closest("[data-cart-qty]");
    if (!input) return;
    var row = e.target.closest("[data-cart-row]");
    window.ABHRCart.updateQty(row.getAttribute("data-slug"), input.value);
  });

  document.addEventListener("abhr:cart:change", render);
  render();

  // ─── Submit ───────────────────────────────────────────────────────────
  var form = document.getElementById("cart-form");
  var successEl = form.querySelector("[data-cart-success]");
  var errorEl = form.querySelector("[data-cart-error]");
  var fieldsEl = form.querySelector("[data-cart-fields]");
  var submitBtn = document.getElementById("cart-submit");

  function val(name) {
    var el = form.querySelector('[name="' + name + '"]');
    return el ? el.value.trim() : "";
  }

  function showError(msg) {
    if (!errorEl) return;
    errorEl.textContent = msg;
    errorEl.style.display = "block";
    errorEl.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (errorEl) errorEl.style.display = "none";

    var items = window.ABHRCart.get();
    if (!items.length) {
      showError("Your cart is empty — add an item before sending a request.");
      return;
    }

    var required = [
      ["name", "your name"], ["phone", "a phone number"], ["email", "an email address"],
      ["delivery_address", "the delivery street address"], ["delivery_city", "the delivery city"],
      ["zip_code", "the delivery ZIP code"], ["delivery_date", "the delivery date"]
    ];
    for (var i = 0; i < required.length; i++) {
      if (!val(required[i][0])) {
        showError("Please add " + required[i][1] + " so we can quote and schedule your order.");
        var el = form.querySelector('[name="' + required[i][0] + '"]');
        if (el) el.focus();
        return;
      }
    }

    var subtotal = window.ABHRCart.itemsTotal(items);
    var grandTotal = subtotal + DELIVERY_FEE;
    var cartItems = items.map(function (i) {
      return { name: i.name, slug: i.slug, qty: i.qty, unit: i.unit, unit_price: i.price, line_total: i.qty * i.price };
    });

    var recap = ["Cart request — " + items.length + " item" + (items.length === 1 ? "" : "s") + ":"];
    items.forEach(function (i) {
      recap.push("  " + i.qty + " " + (i.qty === 1 ? i.unit : i.unitPlural) + " " + i.name + " @ " + money(i.price) + " = " + money(i.qty * i.price));
    });
    recap.push("Standard delivery fee: " + money(DELIVERY_FEE) + " (drop-off/pickup only, no setup)");
    recap.push("Estimated total: " + money(grandTotal));
    if (val("venue_name")) recap.push("Venue: " + val("venue_name"));
    if (val("company")) recap.push("Company: " + val("company"));
    if (val("delivery_time")) recap.push("Preferred delivery time: " + val("delivery_time"));
    if (val("pickup_date")) recap.push("Pickup: " + val("pickup_date"));
    if (val("message")) recap.push("Notes: " + val("message"));

    var row = {
      request_type: "cart_request",
      cart_items: cartItems,
      item_count: items.length,
      quantity: items.reduce(function (sum, i) { return sum + i.qty; }, 0),
      delivery_fee: DELIVERY_FEE,
      estimated_total: grandTotal,

      name: val("name"),
      phone: val("phone"),
      email: val("email"),

      venue_name: val("venue_name"),
      delivery_address: val("delivery_address"),
      delivery_city: val("delivery_city"),
      delivery_state: val("delivery_state"),
      zip_code: val("zip_code"),

      delivery_date: val("delivery_date"),
      delivery_time: val("delivery_time"),
      pickup_date: val("pickup_date"),
      event_date: val("delivery_date"),

      message: recap.join("\n"),
      source: "Cart Request — " + items.length + " item" + (items.length === 1 ? "" : "s"),
      page_url: window.location.href
    };

    if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Sending…"; }

    fetch(SUPABASE_URL + "/rest/v1/leads", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": "Bearer " + SUPABASE_ANON_KEY,
        "Prefer": "return=minimal"
      },
      body: JSON.stringify(row)
    }).then(function (res) {
      if (!res.ok) {
        return res.text().then(function (t) { throw new Error(t || ("HTTP " + res.status)); });
      }
      if (fieldsEl) fieldsEl.style.display = "none";
      if (successEl) {
        successEl.style.display = "block";
        successEl.scrollIntoView({ behavior: "smooth", block: "center" });
      }
      if (window.ABHR_trackEvent) {
        window.ABHR_trackEvent("search", { query: "cart_request:" + items.length + "_items" });
      }
      justSubmitted = true;
      window.ABHRCart.clear();
    }).catch(function (err) {
      console.error("Cart request failed:", err);
      if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = "Send My Request"; }
      showError("Sorry — something went wrong sending your request. Please call or text us and we'll take the order directly.");
    });
  });
})();
