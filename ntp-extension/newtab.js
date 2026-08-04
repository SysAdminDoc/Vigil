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
    shortcuts: DEFAULT_SHORTCUTS,
    widgets: {
      notes: false,
      topSites: false,
      bookmarks: false,
      weather: false,
      rss: false
    },
    widgetNotes: "",
    bookmarkFolderId: "",
    weatherCity: "",
    rssFeeds: []
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
          const stored = res[STORAGE_KEY] || {};
          resolve(Object.assign({}, DEFAULTS, stored, {
            widgets: Object.assign({}, DEFAULTS.widgets, stored.widgets || {})
          }));
        });
      } else {
        try {
          const raw = localStorage.getItem(STORAGE_KEY);
          const stored = raw ? JSON.parse(raw) : {};
          resolve(Object.assign({}, DEFAULTS, stored, {
            widgets: Object.assign({}, DEFAULTS.widgets, stored.widgets || {})
          }));
        } catch (e) {
          resolve(Object.assign({}, DEFAULTS, {
            widgets: Object.assign({}, DEFAULTS.widgets)
          }));
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
  const widgetsEl = $("widgets");
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

  // ---- optional widgets (all disabled by default) ----
  function widgetCard(title, className) {
    const card = document.createElement("section");
    card.className = "widget-card " + className;
    const heading = document.createElement("h3");
    heading.textContent = title;
    card.appendChild(heading);
    return card;
  }

  function appendMessage(card, message) {
    const text = document.createElement("p");
    text.className = "widget-message";
    text.textContent = message;
    card.appendChild(text);
  }

  function isHttpsUrl(value) {
    try {
      return new URL(value).protocol === "https:";
    } catch (e) {
      return false;
    }
  }

  function chromeBookmarksTree() {
    return new Promise((resolve) => {
      if (!window.chrome || !chrome.bookmarks || !chrome.bookmarks.getTree) {
        resolve([]);
        return;
      }
      chrome.bookmarks.getTree(resolve);
    });
  }

  function collectBookmarkFolders(nodes, result, depth) {
    (nodes || []).forEach((node) => {
      if (!node.children) return;
      if (node.id !== "0") {
        result.push({id: node.id, title: "  ".repeat(depth) + (node.title || "Folder")});
      }
      collectBookmarkFolders(node.children, result, depth + 1);
    });
  }

  function loadBookmarkFolders(settings) {
    const select = $("widget-bookmark-folder");
    if (!select) return Promise.resolve();
    return chromeBookmarksTree().then((tree) => {
      const folders = [];
      collectBookmarkFolders(tree, folders, 0);
      select.innerHTML = "";
      const automatic = document.createElement("option");
      automatic.value = "";
      automatic.textContent = "First bookmark folder";
      select.appendChild(automatic);
      folders.forEach((folder) => {
        const option = document.createElement("option");
        option.value = folder.id;
        option.textContent = folder.title;
        select.appendChild(option);
      });
      select.value = settings.bookmarkFolderId || "";
      if (select.value !== settings.bookmarkFolderId) {
        settings.bookmarkFolderId = "";
        save(settings);
      }
    });
  }

  function bookmarkItems(settings) {
    return chromeBookmarksTree().then((tree) => {
      let folders = [];
      collectBookmarkFolders(tree, folders, 0);
      let folder = folders.find((candidate) => candidate.id === settings.bookmarkFolderId);
      if (!folder && tree.length) {
        const findFirst = (nodes) => {
          for (const node of nodes || []) {
            if (node.children && node.id !== "0") return node;
            const nested = findFirst(node.children);
            if (nested) return nested;
          }
          return null;
        };
        folder = findFirst(tree);
      }
      if (!folder || !chrome.bookmarks || !chrome.bookmarks.getSubTree) return [];
      return new Promise((resolve) => {
        chrome.bookmarks.getSubTree(folder.id, (nodes) => {
          resolve((nodes[0] && nodes[0].children || [])
            .filter((node) => node.url && isHttpsUrl(node.url)).slice(0, 8));
        });
      });
    });
  }

  function renderLinkList(card, items, emptyMessage) {
    if (!items.length) {
      appendMessage(card, emptyMessage);
      return;
    }
    const list = document.createElement("div");
    list.className = "widget-links";
    items.forEach((item) => {
      const link = document.createElement("a");
      link.href = item.url;
      link.textContent = item.title || item.name || item.url;
      link.title = item.url;
      list.appendChild(link);
    });
    card.appendChild(list);
  }

  function renderNotes(card, settings) {
    const notes = document.createElement("textarea");
    notes.className = "widget-notes";
    notes.placeholder = "Private notes stay in this browser profile";
    notes.value = settings.widgetNotes || "";
    notes.addEventListener("input", () => {
      settings.widgetNotes = notes.value;
      save(settings);
    });
    card.appendChild(notes);
  }

  function renderTopSites(card) {
    if (!window.chrome || !chrome.topSites || !chrome.topSites.get) {
      appendMessage(card, "Top sites are only available in the installed extension.");
      return;
    }
    chrome.topSites.get((sites) => {
      renderLinkList(card, (sites || []).slice(0, 6), "No top sites yet.");
    });
  }

  function renderBookmarks(card, settings) {
    bookmarkItems(settings).then((items) => {
      renderLinkList(card, items, "Choose a bookmark folder in NTP settings.");
    });
  }

  function renderWeather(card, settings) {
    const city = (settings.weatherCity || "").trim();
    if (!city) {
      appendMessage(card, "Choose a city in NTP settings to load weather.");
      return;
    }
    appendMessage(card, "Loading weather…");
    fetch("https://geocoding-api.open-meteo.com/v1/search?name=" +
      encodeURIComponent(city) + "&count=1&language=en&format=json")
      .then((response) => response.json())
      .then((locations) => {
        const location = locations.results && locations.results[0];
        if (!location) throw new Error("city not found");
        return fetch("https://api.open-meteo.com/v1/forecast?latitude=" +
          location.latitude + "&longitude=" + location.longitude +
          "&current=temperature_2m,weather_code&temperature_unit=fahrenheit")
          .then((response) => response.json())
          .then((weather) => ({location, weather}));
      })
      .then(({location, weather}) => {
        card.querySelector(".widget-message").remove();
        const value = weather.current && weather.current.temperature_2m;
        const unit = weather.current_units && weather.current_units.temperature_2m || "°F";
        const current = document.createElement("p");
        current.className = "widget-value";
        current.textContent = `${value}${unit}`;
        const place = document.createElement("p");
        place.className = "widget-message";
        place.textContent = `${location.name}, ${location.country || ""}`;
        card.append(current, place);
      })
      .catch(() => {
        const message = card.querySelector(".widget-message");
        if (message) message.textContent = "Weather is unavailable right now.";
      });
  }

  function parseFeed(text) {
    const documentNode = new DOMParser().parseFromString(text, "application/xml");
    if (documentNode.querySelector("parsererror")) return [];
    return Array.from(documentNode.querySelectorAll("item, entry")).slice(0, 3)
      .map((item) => {
        const title = item.querySelector("title")?.textContent?.trim();
        const linkNode = item.querySelector("link");
        const href = linkNode?.getAttribute("href") || linkNode?.textContent?.trim();
        return {title, url: href};
      })
      .filter((item) => item.title && isHttpsUrl(item.url));
  }

  function renderRss(card, settings) {
    const feeds = (settings.rssFeeds || []).filter(isHttpsUrl).slice(0, 3);
    if (!feeds.length) {
      appendMessage(card, "Add up to three HTTPS feeds in NTP settings.");
      return;
    }
    appendMessage(card, "Loading feeds…");
    Promise.all(feeds.map((url) => fetch(url).then((response) => response.text())))
      .then((documents) => documents.flatMap(parseFeed).slice(0, 3))
      .then((items) => {
        const message = card.querySelector(".widget-message");
        if (message) message.remove();
        renderLinkList(card, items, "No recent feed entries.");
      })
      .catch(() => {
        const message = card.querySelector(".widget-message");
        if (message) message.textContent = "Feeds are unavailable right now.";
      });
  }

  function renderWidgets(settings) {
    const enabled = settings.widgets || {};
    widgetsEl.innerHTML = "";
    if (!Object.values(enabled).some(Boolean)) {
      widgetsEl.style.display = "none";
      return;
    }
    widgetsEl.style.display = "grid";
    const add = (card) => widgetsEl.appendChild(card);
    if (enabled.notes) {
      const card = widgetCard("Notes", "widget-notes-card");
      renderNotes(card, settings);
      add(card);
    }
    if (enabled.topSites) {
      const card = widgetCard("Top sites", "widget-top-sites-card");
      renderTopSites(card);
      add(card);
    }
    if (enabled.bookmarks) {
      const card = widgetCard("Bookmarks", "widget-bookmarks-card");
      renderBookmarks(card, settings);
      add(card);
    }
    if (enabled.weather) {
      const card = widgetCard("Weather", "widget-weather-card");
      renderWeather(card, settings);
      add(card);
    }
    if (enabled.rss) {
      const card = widgetCard("RSS", "widget-rss-card");
      renderRss(card, settings);
      add(card);
    }
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
    $("opt-widget-notes").checked = settings.widgets.notes;
    $("opt-widget-top-sites").checked = settings.widgets.topSites;
    $("opt-widget-bookmarks").checked = settings.widgets.bookmarks;
    $("opt-widget-weather").checked = settings.widgets.weather;
    $("opt-widget-rss").checked = settings.widgets.rss;
    $("widget-weather-city").value = settings.weatherCity || "";
    $("widget-rss-feeds").value = (settings.rssFeeds || []).join("\n");
  }

  // ---- bootstrap ----
  load().then((settings) => {
    updateClock(settings);
    setInterval(() => updateClock(settings), 1000);
    renderShortcuts(settings);
    renderWidgets(settings);
    if (!settings.showSearch) searchWrapper.style.display = "none";

    $("settings-btn").addEventListener("click", () => {
      settingsPanel.classList.add("open");
      renderEditor(settings);
      syncToggles(settings);
      loadBookmarkFolders(settings);
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
    [
      ["opt-widget-notes", "notes"],
      ["opt-widget-top-sites", "topSites"],
      ["opt-widget-bookmarks", "bookmarks"],
      ["opt-widget-weather", "weather"],
      ["opt-widget-rss", "rss"]
    ].forEach(([id, key]) => {
      $(id).addEventListener("change", (e) => {
        settings.widgets[key] = e.target.checked;
        save(settings);
        renderWidgets(settings);
      });
    });
    $("widget-bookmark-folder").addEventListener("change", (e) => {
      settings.bookmarkFolderId = e.target.value;
      save(settings);
      renderWidgets(settings);
    });
    $("widget-weather-city").addEventListener("change", (e) => {
      settings.weatherCity = e.target.value.trim();
      save(settings);
      renderWidgets(settings);
    });
    $("widget-rss-feeds").addEventListener("change", (e) => {
      settings.rssFeeds = e.target.value.split(/\r?\n/)
        .map((url) => url.trim()).filter(isHttpsUrl).slice(0, 3);
      save(settings);
      syncToggles(settings);
      renderWidgets(settings);
    });
    $("add-shortcut").addEventListener("click", () => {
      settings.shortcuts.push({ name: "New site", url: "https://" });
      save(settings);
      renderEditor(settings);
      renderShortcuts(settings);
    });
  });
})();
