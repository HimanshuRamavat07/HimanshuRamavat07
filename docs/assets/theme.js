(function () {
  var KEY = "aidaily-theme";
  var root = document.documentElement;

  function apply(theme) {
    root.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(KEY, theme);
    } catch (_err) {
      /* ponytail: ignore private mode storage failures */
    }
  }

  function preferred() {
    try {
      var saved = localStorage.getItem(KEY);
      if (saved === "light" || saved === "dark") {
        return saved;
      }
    } catch (_err) {
      /* ponytail: ignore private mode storage failures */
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  apply(preferred());

  document.addEventListener("DOMContentLoaded", function () {
    var toggle = document.querySelector(".theme-toggle");
    if (!toggle) {
      return;
    }
    toggle.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      apply(next);
    });
  });
})();
