// mia's corner - tiny bit of interaction, nothing clever
(function () {
  "use strict";

  // 1. mark the page we are on in the nav
  var here = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll("nav.main a").forEach(function (a) {
    if (a.getAttribute("href") === here) a.setAttribute("aria-current", "page");
  });

  // 2. the drink picker on the coffee page
  var pickBtn = document.getElementById("pick-drink");
  if (pickBtn) {
    var out = document.getElementById("pick-result");
    var names = (window.MIA_DRINKS || []);
    pickBtn.addEventListener("click", function () {
      if (!names.length) return;
      var pick = names[Math.floor(Math.random() * names.length)];
      out.textContent = "make a " + pick;
    });
  }

  // 3. footer year, so i never have to remember to change it
  var y = document.getElementById("year");
  if (y) y.textContent = new Date().getFullYear();
})();
