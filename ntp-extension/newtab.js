// Vigil NTP — vanilla JS, no deps. MV3-compliant (no inline scripts, no eval).
// Settings persist to chrome.storage.local when available, fallback to localStorage
// (so the same file can be opened directly with --load-extension or visited as
// a plain HTML page during development).

"use strict";

(function () {
  const DEFAULT_SHORTCUTS = [
    { name: "DuckDuckGo", url: "https://duckduckgo.com" },
    { name: "YouTube",    url: "https://www.youtube.com" },
    { name: "Reddit",     url: "https://www.reddit.com" },
    { name: "GitHub",     url: "https://github.com" },
    { name: "Wikipedia",  url: "https://www.wikipedia.org" },
    { name: "Mojeek",     url: "https://www.mojeek.com" }
  ];

  const DEFAULTS = {
    showClock: true,
    use24h: false,
    showShortcuts: true,
    showSearch: true,
    shortcuts: DEFAULT_SHORTCUTS
  };

  const STORAGE_KEY = "vigil_ntp_settings";

  // ---- storage abstraction (chrome.storage when packaged, localStorage when not) ----
  const useChromeStorage = typeof chrome !== "undefined"
                        && chrome.storage
                        && chrome.storage.local;

  function load() {
    return new Promise((resolve) => {
      if (useChromeStorage) {
        chrome.storage.local.get([STORAGE_KEY], (res) => {
          resolve(Object.assign({}, DEFAULTS, res[STORAGE_KEY] || {}));
        });
      } else {
        try {
          const raw = localStorage.getItem(STORAGE_KEY);
          resolve(Object.assign({}, DEFAULTS, raw ? JSON.parse(raw) : {}));
        } catch (e) {
          resolve(Object.assign({}, DEFAULTS));
        }
      }
    });
  }

  function save(s) {
    if (useChromeStorage) {
      chrome.storage.local.set({ [STORAGE_KEY]: s });
    } else {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)); } catch (e) { /* ignore */ }
    }
  }

  // ---- DOM helpers ----
  const $ = (id) => document.getElementById(id);
  const clockEl = $("clock");
  const dateEl = $("date");
  const searchWrapper = $("search-wrapper");
  const searchInput = $("search");
  const shortcutsEl = $("shortcuts");
  const settingsPanel = $("settings-panel");
  const editorEl = $("shortcut-editor");

  // ---- search ----
  const URL_LIKE = /^https?:\/\//i;
  const DOMAIN_LIKE = /^[a-z0-9]([a-z0-9-]*\.)+[a-z]{2,}/i;

  searchInput.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    const q = searchInput.value.trim();
    if (!q) return;
    if (URL_LIKE.test(q)) {
      window.location.href = q;
    } else if (DOMAIN_LIKE.test(q)) {
      window.location.href = "https://" + q;
    } else {
      // Match the user's default search engine, which is DuckDuckGo per N1.
      window.location.href = "https://duckduckgo.com/?q=" + encodeURIComponent(q);
    }
  });

  // ---- clock ----
  function updateClock(settings) {
    const now = new Date();
    if (!settings.showClock) {
      clockEl.style.display = "none";
      dateEl.style.display = "none";
      return;
    }
    clockEl.style.display = "";
    dateEl.style.display = "";
    if (settings.use24h) {
      clockEl.textContent = now.toLocaleTimeString([], {
        hour: "2-digit", minute: "2-digit", hour12: false });
    } else {
      clockEl.textContent = now.toLocaleTimeString([], {
        hour: "numeric", minute: "2-digit", hour12: true });
    }
    dateEl.textContent = now.toLocaleDateString([], {
      weekday: "long", month: "long", day: "numeric", year: "numeric" });
  }

  // ---- shortcuts ----
  function faviconUrl(url) {
    try {
      const u = new URL(url);
      return "https://www.google.com/s2/favicons?domain=" + u.hostname + "&sz=64";
    } catch (e) {
      return "";
    }
  }

  function renderShortcuts(settings) {
    shortcutsEl.innerHTML = "";
    if (!settings.showShortcuts) {
      shortcutsEl.style.display = "none";
      return;
    }
    shortcutsEl.style.display = "";
    settings.shortcuts.forEach((s) => {
      const a = document.createElement("a");
      a.className = "shortcut";
      a.href = s.url;
      const icon = document.createElement("div");
      icon.className = "shortcut-icon";
      const img = document.createElement("img");
      img.alt = "";
      img.src = faviconUrl(s.url);
      icon.appendChild(img);
      const label = document.createElement("div");
      label.className = "shortcut-label";
      label.textContent = s.name; // textContent escapes
      a.appendChild(icon);
      a.appendChild(label);
      shortcutsEl.appendChild(a);
    });
  }

  function renderEditor(settings) {
    editorEl.innerHTML = "";
    settings.shortcuts.forEach((s, i) => {
      const row = document.createElement("div");
      row.className = "shortcut-edit-row";

      const nameInput = document.createElement("input");
      nameInput.type = "text";
      nameInput.placeholder = "Name";
      nameInput.value = s.name;
      nameInput.addEventListener("input", () => {
        settings.shortcuts[i].name = nameInput.value;
        save(settings);
        renderShortcuts(settings);
      });

      const urlInput = document.createElement("input");
      urlInput.type = "text";
      urlInput.placeholder = "URL";
      urlInput.value = s.url;
      urlInput.addEventListener("input", () => {
        settings.shortcuts[i].url = urlInput.value;
        save(settings);
        renderShortcuts(settings);
      });

      const rm = document.createElement("button");
      rm.className = "btn-remove";
      rm.title = "Remove";
      rm.textContent = "×";
      rm.addEventListener("click", () => {
        settings.shortcuts.splice(i, 1);
        save(settings);
        renderEditor(settings);
        renderShortcuts(settings);
      });

      row.appendChild(nameInput);
      row.appendChild(urlInput);
      row.appendChild(rm);
      editorEl.appendChild(row);
    });
  }

  // ---- settings panel ----
  function syncToggles(settings) {
    $("opt-clock").checked = settings.showClock;
    $("opt-24h").checked = settings.use24h;
    $("opt-shortcuts").checked = settings.showShortcuts;
    $("opt-search").checked = settings.showSearch;
  }

  // ---- bootstrap ----
  load().then((settings) => {
    updateClock(settings);
    setInterval(() => updateClock(settings), 1000);
    renderShortcuts(settings);
    if (!settings.showSearch) searchWrapper.style.display = "none";

    $("settings-btn").addEventListener("click", () => {
      settingsPanel.classList.add("open");
      renderEditor(settings);
      syncToggles(settings);
    });
    $("close-settings").addEventListener("click", () => {
      settingsPanel.classList.remove("open");
    });
    settingsPanel.addEventListener("click", (e) => {
      if (e.target === settingsPanel) settingsPanel.classList.remove("open");
    });

    $("opt-clock").addEventListener("change", (e) => {
      settings.showClock = e.target.checked;
      save(settings);
      updateClock(settings);
    });
    $("opt-24h").addEventListener("change", (e) => {
      settings.use24h = e.target.checked;
      save(settings);
      updateClock(settings);
    });
    $("opt-shortcuts").addEventListener("change", (e) => {
      settings.showShortcuts = e.target.checked;
      save(settings);
      renderShortcuts(settings);
    });
    $("opt-search").addEventListener("change", (e) => {
      settings.showSearch = e.target.checked;
      save(settings);
      searchWrapper.style.display = settings.showSearch ? "" : "none";
    });
    $("add-shortcut").addEventListener("click", () => {
      settings.shortcuts.push({ name: "New site", url: "https://" });
      save(settings);
      renderEditor(settings);
      renderShortcuts(settings);
    });
  });
})();
