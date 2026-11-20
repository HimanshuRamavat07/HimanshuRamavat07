(function () {
  function init() {
    var list = document.getElementById("archive-report-list");
    if (!list) return;

    var search = document.getElementById("archive-search");
    var year = document.getElementById("archive-year");
    var month = document.getElementById("archive-month");
    var topic = document.getElementById("archive-topic");
    var empty = document.getElementById("archive-empty");
    var rows = Array.prototype.slice.call(list.querySelectorAll(".archive-row"));
    function apply() {
      var q = (search && search.value ? search.value : "").trim().toLowerCase();
      var y = year ? year.value : "";
      var m = month ? month.value : "";
      var t = topic ? topic.value : "";
      var visible = 0;

      rows.forEach(function (row) {
        var hay = (
          (row.textContent || "") +
          " " +
          (row.getAttribute("data-topics") || "")
        ).toLowerCase();
        var ok = true;
        if (q && hay.indexOf(q) === -1) ok = false;
        if (y && row.getAttribute("data-year") !== y) ok = false;
        if (m && row.getAttribute("data-month") !== m) ok = false;
        if (t) {
          var topics = (row.getAttribute("data-topics") || "").split(",");
          if (topics.indexOf(t) === -1) ok = false;
        }
        row.hidden = !ok;
        if (ok) visible += 1;
      });

      if (empty) empty.hidden = visible > 0;
    }

    [search, year, month, topic].forEach(function (el) {
      if (!el) return;
      el.addEventListener("input", apply);
      el.addEventListener("change", apply);
    });

    document.querySelectorAll("[data-month-jump]").forEach(function (link) {
      link.addEventListener("click", function (e) {
        var key = link.getAttribute("data-month-jump");
        var target = document.getElementById("m-" + key);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
