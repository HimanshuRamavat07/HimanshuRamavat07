(function () {
  function init() {
    var bar = document.getElementById("read-progress");
    var tocLinks = document.querySelectorAll(".report-sidebar .toc a");
    var sections = [];

    tocLinks.forEach(function (link) {
      var id = link.getAttribute("href");
      if (id && id.charAt(0) === "#") {
        var section = document.getElementById(id.slice(1));
        if (section) {
          sections.push({ link: link, section: section });
        }
      }
    });

    function onScroll() {
      var scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
      if (bar) {
        bar.style.width = scrollHeight > 0 ? (window.scrollY / scrollHeight) * 100 + "%" : "0%";
      }

      var active = sections.length ? sections[0].link : null;
      sections.forEach(function (item) {
        if (item.section.getBoundingClientRect().top <= 120) {
          active = item.link;
        }
      });

      tocLinks.forEach(function (link) {
        link.classList.toggle("is-active", link === active);
      });
    }

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
