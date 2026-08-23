/* Atlanta Bounce House Rentals — shared cart.
   localStorage-backed so it persists across pages with no backend of its
   own. Products are added here from /products/ and individual product
   pages; /cart/ page renders and checks out the whole cart in one request
   to the Supabase `leads` table (see supabase/migrate_cart_orders.sql).
*/
(function () {
  "use strict";

  var STORAGE_KEY = "abhr_cart";

  function readCart() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      var items = raw ? JSON.parse(raw) : [];
      return Array.isArray(items) ? items : [];
    } catch (e) {
      return [];
    }
  }

  function writeCart(items) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch (e) {}
    updateBadges();
    document.dispatchEvent(new CustomEvent("abhr:cart:change", { detail: { items: items } }));
  }

  function cartCount(items) {
    items = items || readCart();
    var n = 0;
    items.forEach(function (i) { n += i.qty || 0; });
    return n;
  }

  function updateBadges() {
    var n = cartCount();
    document.querySelectorAll(".cart-count").forEach(function (el) {
      if (n > 0) {
        el.textContent = n;
        el.hidden = false;
      } else {
        el.hidden = true;
      }
    });
  }

  function addItem(item, qty) {
    qty = Math.max(1, parseInt(qty, 10) || item.minQty || 1);
    var items = readCart();
    var existing = items.filter(function (i) { return i.slug === item.slug; })[0];
    if (existing) {
      existing.qty += qty;
    } else {
      items.push({
        slug: item.slug,
        name: item.name,
        unit: item.unit,
        unitPlural: item.unitPlural || item.unit + "s",
        price: item.price,
        qty: qty,
        href: item.href,
        parentName: item.parentName || "",
        minQty: item.minQty || 1
      });
    }
    writeCart(items);
    return items;
  }

  function updateQty(slug, qty) {
    var items = readCart();
    var row = items.filter(function (i) { return i.slug === slug; })[0];
    if (!row) return items;
    qty = parseInt(qty, 10);
    if (isNaN(qty) || qty < (row.minQty || 1)) qty = row.minQty || 1;
    row.qty = qty;
    writeCart(items);
    return items;
  }

  function removeItem(slug) {
    var items = readCart().filter(function (i) { return i.slug !== slug; });
    writeCart(items);
    return items;
  }

  function clearCart() {
    writeCart([]);
  }

  function itemsTotal(items) {
    items = items || readCart();
    var sum = 0;
    items.forEach(function (i) { sum += i.qty * i.price; });
    return sum;
  }

  window.ABHRCart = {
    get: readCart,
    add: addItem,
    updateQty: updateQty,
    remove: removeItem,
    clear: clearCart,
    count: cartCount,
    itemsTotal: itemsTotal,
    updateBadges: updateBadges
  };

  // ─── Wire up any [data-add-to-cart] buttons on the page ────────────────
  // On /products/, each button lives inside a [data-product-item] card that
  // carries the product's data via data-* attributes. On an individual
  // product page, the button (if present) reads from the page's own
  // [data-product] root plus the live quantity picker instead.
  function readItemFromCard(card) {
    return {
      slug: card.getAttribute("data-slug"),
      name: card.getAttribute("data-name-display") || card.querySelector("h3") && card.querySelector("h3").textContent.trim(),
      unit: card.getAttribute("data-unit"),
      price: parseFloat(card.getAttribute("data-price")) || 0,
      href: card.getAttribute("data-href"),
      parentName: card.getAttribute("data-parent"),
      minQty: parseInt(card.getAttribute("data-min-qty"), 10) || 1
    };
  }

  function flashButton(btn) {
    var original = btn.textContent;
    btn.textContent = "Added ✓";
    btn.disabled = true;
    setTimeout(function () {
      btn.textContent = original;
      btn.disabled = false;
    }, 1200);
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest("[data-add-to-cart]");
    if (!btn) return;
    e.preventDefault();

    var card = btn.closest("[data-product-item]");
    if (card) {
      addItem(readItemFromCard(card), card.getAttribute("data-min-qty"));
      flashButton(btn);
      return;
    }

    // Individual product page: read from the page's [data-product] root and
    // its live quantity input so "Add to Cart" respects whatever quantity
    // the visitor already picked.
    var root = document.querySelector("[data-product]");
    if (!root) return;
    var qtyInput = root.querySelector("[data-qty]");
    var qty = qtyInput ? parseInt(qtyInput.value, 10) : 1;
    addItem({
      slug: root.getAttribute("data-product-slug"),
      name: root.getAttribute("data-product-name"),
      unit: root.getAttribute("data-product-unit"),
      unitPlural: root.getAttribute("data-product-unit-plural"),
      price: parseFloat(root.getAttribute("data-product-price")) || 0,
      href: window.location.pathname,
      parentName: root.getAttribute("data-product-parent") || "",
      minQty: parseInt(root.getAttribute("data-product-min"), 10) || 1
    }, qty);
    flashButton(btn);
  });

  updateBadges();
  document.addEventListener("abhr:cart:change", updateBadges);
})();
