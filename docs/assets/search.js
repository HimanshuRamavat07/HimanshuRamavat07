(function () {
  var overlay, input, resultsList, emptyState, baseHref;

  function resolveIndexUrl() {
    var scripts = document.querySelectorAll("script[src*='search.js']");
    if (scripts.length) {
      var src = scripts[0].getAttribute("src");
      return src.replace("assets/search.js", "assets/search-index.json");
    }
    return (baseHref || "") + "assets/search-index.json";
  }

  function init() {
    overlay = document.getElementById("search-overlay");
    if (!overlay) return;

    baseHref = overlay.getAttribute("data-base-href") || "";
    input = overlay.querySelector(".search-input");
    resultsList = overlay.querySelector(".search-results");
    emptyState = overlay.querySelector(".search-empty");
    var closeBtn = overlay.querySelector(".search-close");
    var triggers = document.querySelectorAll("[data-open-search]");

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
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (overlay.classList.contains("is-open")) {
          close();
        } else {
          open();
        }
      }
      if (e.key === "Escape" && overlay.classList.contains("is-open")) {
        close();
      }
    });

    if (input) {
      input.addEventListener("input", function () {
        search(input.value.trim());
      });
    }
  }

  function ensureIndex() {
    if (window.__SEARCH_INDEX__ && window.__SEARCH_INDEX__.length) {
      return Promise.resolve(window.__SEARCH_INDEX__);
    }
    var url = resolveIndexUrl();
    return fetch(url)
      .then(function (res) {
        if (!res.ok) throw new Error("Fetch failed: " + res.status);
        return res.json();
      })
      .then(function (data) {
        window.__SEARCH_INDEX__ = data;
        return data;
      })
      .catch(function (err) {
        console.warn("Search index load failed:", err);
        return window.__SEARCH_INDEX__ || [];
      });
  }

  function open() {
    overlay.classList.add("is-open");
    document.body.style.overflow = "hidden";
    if (input) {
      input.value = "";
      setTimeout(function () { input.focus(); }, 50);
    }
    if (resultsList) resultsList.innerHTML = "";
    if (emptyState) emptyState.style.display = "none";
    ensureIndex();
  }

  function close() {
    overlay.classList.remove("is-open");
    document.body.style.overflow = "";
  }

  function search(query) {
    if (!resultsList) return;
    if (!query) {
      resultsList.innerHTML = "";
      if (emptyState) emptyState.style.display = "none";
      return;
    }

    ensureIndex().then(function (data) {
      if (!data || !data.length) {
        if (emptyState) {
          emptyState.style.display = "block";
          emptyState.textContent = "Search index loading or not available";
        }
        return;
      }

      var q = query.toLowerCase();
      var matches = data.filter(function (item) {
        var inTitle = item.title && item.title.toLowerCase().indexOf(q) !== -1;
        var inDesc = item.description && item.description.toLowerCase().indexOf(q) !== -1;
        var inSections = item.sections && item.sections.some(function (s) {
          return s.toLowerCase().indexOf(q) !== -1;
        });
        return inTitle || inDesc || inSections;
      });

      if (matches.length === 0) {
        resultsList.innerHTML = "";
        if (emptyState) {
          emptyState.style.display = "block";
          emptyState.textContent = 'No results for \u201c' + query + '\u201d';
        }
        return;
      }

      if (emptyState) emptyState.style.display = "none";

      resultsList.innerHTML = matches.slice(0, 15).map(function (item) {
        var desc = item.description || "";
        if (desc.length > 140) desc = desc.substring(0, 140) + "\u2026";
        var href = (baseHref || "") + item.url;
        return (
          '<li class="search-result-item">' +
            '<a href="' + escapeHtml(href) + '" class="search-result-link">' +
              '<span class="search-result-date">' + escapeHtml(item.date || "") + '</span>' +
              '<span class="search-result-title">' + highlight(item.title, q) + '</span>' +
              '<span class="search-result-desc">' + highlight(desc, q) + '</span>' +
            '</a>' +
          '</li>'
        );
      }).join("");
    });
  }

  function highlight(text, query) {
    if (!text) return "";
    var lower = text.toLowerCase();
    var idx = lower.indexOf(query);
    if (idx === -1) return escapeHtml(text);
    return (
      escapeHtml(text.substring(0, idx)) +
      '<mark class="search-highlight">' +
      escapeHtml(text.substring(idx, idx + query.length)) +
      '</mark>' +
      escapeHtml(text.substring(idx + query.length))
    );
  }

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
