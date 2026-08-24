(function () {
  "use strict";

  var root = document.querySelector("[data-gallery]");
  if (!root) return;

  var track = root.querySelector("[data-gallery-track]");
  var slides = Array.from(track.children);
  var dotsWrap = root.querySelector("[data-gallery-dots]");
  var prevBtn = root.querySelector("[data-gallery-prev]");
  var nextBtn = root.querySelector("[data-gallery-next]");
  if (!slides.length) return;

  var index = 0;
  var AUTO_MS = 5000;
  var timer = null;

  slides.forEach(function (_, i) {
    var dot = document.createElement("button");
    dot.type = "button";
    dot.className = "gallery-dot";
    dot.setAttribute("aria-label", "Go to photo " + (i + 1));
    dot.addEventListener("click", function () { goTo(i); restart(); });
    dotsWrap.appendChild(dot);
  });
  var dots = Array.from(dotsWrap.children);

  function render() {
    track.style.transform = "translateX(-" + (index * 100) + "%)";
    dots.forEach(function (d, i) { d.classList.toggle("active", i === index); });
  }

  function goTo(i) {
    index = (i + slides.length) % slides.length;
    render();
  }

  function next() { goTo(index + 1); }
  function prev() { goTo(index - 1); }

  function restart() {
    if (timer) clearInterval(timer);
    timer = setInterval(next, AUTO_MS);
  }

  nextBtn.addEventListener("click", function () { next(); restart(); });
  prevBtn.addEventListener("click", function () { prev(); restart(); });

  root.addEventListener("mouseenter", function () { if (timer) clearInterval(timer); });
  root.addEventListener("mouseleave", restart);

  // Basic swipe support
  var touchStartX = null;
  track.addEventListener("touchstart", function (e) { touchStartX = e.touches[0].clientX; }, { passive: true });
  track.addEventListener("touchend", function (e) {
    if (touchStartX === null) return;
    var dx = e.changedTouches[0].clientX - touchStartX;
    if (Math.abs(dx) > 40) { dx < 0 ? next() : prev(); restart(); }
    touchStartX = null;
  });

  render();
  restart();
})();
