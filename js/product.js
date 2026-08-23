/* Atlanta Bounce House Rentals — product request pages
   (/services/{service}/{product}/). Vanilla JS, no dependencies.

   Handles the quantity picker + live running total, and posts the order
   request straight into the Supabase `leads` table with everything needed to
   raise an invoice and fulfil the order (contact, delivery address, dates,
   quantity, variant, unit price, total). Same fetch-based pattern as
   wizard.js — see supabase/migrate_product_orders.sql for the columns.
*/
(function () {
  "use strict";

  var SUPABASE_URL = "https://tbqigevoksabizjogvtm.supabase.co";
  var SUPABASE_ANON_KEY = "sb_publishable_aHlx0Tdu2rhOTBUp3lhkQw_Lv6Awz7a";

  var root = document.querySelector("[data-product]");
  if (!root) return;

  var PRODUCT = {
    name: root.getAttribute("data-product-name") || "",
    slug: root.getAttribute("data-product-slug") || "",
    price: parseFloat(root.getAttribute("data-product-price")) || 0,
    unit: root.getAttribute("data-product-unit") || "item",
    unitPlural: root.getAttribute("data-product-unit-plural") || "items",
    min: parseInt(root.getAttribute("data-product-min"), 10) || 1,
    deliveryFee: parseFloat(root.getAttribute("data-product-delivery-fee")) || 0
  };

  var qtyInput = root.querySelector("[data-qty]");
  var totalEl = root.querySelector("[data-total]");
  var noteEl = root.querySelector("[data-total-note]");
  var form = document.querySelector("[data-product-form]");
  var formSummary = form && form.querySelector("[data-form-summary]");
  var formTotal = form && form.querySelector("[data-form-total]");

  function money(n) {
    return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function currentQty() {
    var n = parseInt(qtyInput && qtyInput.value, 10);
    if (isNaN(n) || n < PRODUCT.min) n = PRODUCT.min;
    return n;
  }

  function selectedOptions() {
    var out = {};
    root.querySelectorAll("[data-product-option]").forEach(function (sel) {
      out[sel.name] = sel.value;
    });
    return out;
  }

  function render() {
    var qty = currentQty();
    var itemsTotal = qty * PRODUCT.price;
    var grandTotal = itemsTotal + PRODUCT.deliveryFee;
    var word = qty === 1 ? PRODUCT.unit : PRODUCT.unitPlural;
    var summary = qty + " " + word + " × " + money(PRODUCT.price) + " + " + money(PRODUCT.deliveryFee) + " delivery";
    if (totalEl) totalEl.textContent = money(grandTotal);
    if (noteEl) noteEl.textContent = qty + " " + word + " × " + money(PRODUCT.price) + " = " + money(itemsTotal);
    if (formSummary) formSummary.textContent = summary;
    if (formTotal) formTotal.textContent = money(grandTotal);
  }

  if (qtyInput) {
    qtyInput.addEventListener("input", render);
    qtyInput.addEventListener("change", function () {
      qtyInput.value = currentQty(); // snap invalid/blank input back to a real number
      render();
    });
  }
  root.querySelectorAll("[data-qty-step]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var step = parseInt(btn.getAttribute("data-qty-step"), 10) || 0;
      qtyInput.value = Math.max(PRODUCT.min, currentQty() + step);
      render();
    });
  });
  root.querySelectorAll("[data-product-option]").forEach(function (sel) {
    sel.addEventListener("change", render);
  });

  // ─── Photo gallery (click a thumbnail to swap the main photo) ─────────
  var galleryEl = root.querySelector("[data-pr-gallery]");
  var mainImageEl = document.getElementById("pr-main-image");
  if (galleryEl && mainImageEl) {
    galleryEl.querySelectorAll("[data-gallery-src]").forEach(function (thumb) {
      thumb.addEventListener("click", function () {
        mainImageEl.src = thumb.getAttribute("data-gallery-src");
        mainImageEl.alt = thumb.getAttribute("data-gallery-alt") || "";
        mainImageEl.width = thumb.getAttribute("data-gallery-w");
        mainImageEl.height = thumb.getAttribute("data-gallery-h");
        galleryEl.querySelectorAll(".pr-thumb").forEach(function (t) { t.classList.remove("active"); });
        thumb.classList.add("active");
      });
    });
  }

  render();

  // ─── Submit ───────────────────────────────────────────────────────────
  if (!form) return;
  var successEl = form.querySelector("[data-pr-success]");
  var errorEl = form.querySelector("[data-pr-error]");
  var fieldsEl = form.querySelector("[data-pr-fields]");
  var submitBtn = form.querySelector("[data-pr-submit]");

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

    var qty = currentQty();
    var opts = selectedOptions();
    var variant = opts.cushion_color || Object.keys(opts).map(function (k) { return opts[k]; }).join(", ");
    var itemsTotal = qty * PRODUCT.price;
    var grandTotal = itemsTotal + PRODUCT.deliveryFee;

    // Human-readable recap folded into `message` too, so the order is fully
    // legible straight from the leads table without joining any other data.
    var recap = [
      PRODUCT.name,
      qty + " " + (qty === 1 ? PRODUCT.unit : PRODUCT.unitPlural) + " @ " + money(PRODUCT.price) + " = " + money(itemsTotal),
      "Standard delivery fee: " + money(PRODUCT.deliveryFee) + " (drop-off/pickup only, no setup)",
      "Estimated total: " + money(grandTotal)
    ];
    if (variant) recap.push("Cushion/variant: " + variant);
    if (val("venue_name")) recap.push("Venue: " + val("venue_name"));
    if (val("company")) recap.push("Company: " + val("company"));
    if (val("delivery_time")) recap.push("Preferred delivery time: " + val("delivery_time"));
    if (val("pickup_date")) recap.push("Pickup: " + val("pickup_date"));
    if (val("message")) recap.push("Notes: " + val("message"));

    var row = {
      request_type: "product_request",
      product_name: PRODUCT.name,
      product_slug: PRODUCT.slug,
      product_variant: variant,
      quantity: qty,
      unit_price: PRODUCT.price,
      delivery_fee: PRODUCT.deliveryFee,
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
      // event_date is what the existing wizard/leads views read, so mirror the
      // delivery date into it rather than leaving those rows blank.
      event_date: val("delivery_date"),

      message: recap.join("\n"),
      source: "Product Request — " + PRODUCT.name,
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
        window.ABHR_trackEvent("search", { query: "product_request:" + PRODUCT.slug + ":" + qty });
      }
    }).catch(function (err) {
      console.error("Product request failed:", err);
      if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = "Send My Request"; }
      showError("Sorry — something went wrong sending your request. Please call or text us and we'll take the order directly.");
    });
  });
})();
