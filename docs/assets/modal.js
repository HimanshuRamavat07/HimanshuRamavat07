(function () {
  function init() {
    var overlay = document.getElementById("automation-modal-overlay");
    if (!overlay) return;

    var modal = overlay.querySelector(".automation-modal");
    var closeBtn = overlay.querySelector(".automation-modal-close");
    var triggers = document.querySelectorAll("[data-open-automation-modal]");

    function open() {
      overlay.classList.add("is-open");
      document.body.style.overflow = "hidden";
      if (closeBtn) closeBtn.focus();
    }

    function close() {
      overlay.classList.remove("is-open");
      document.body.style.overflow = "";
    }

    triggers.forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        open();
      });
    });

    if (closeBtn) closeBtn.addEventListener("click", close);

    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) close();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && overlay.classList.contains("is-open")) {
        close();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
