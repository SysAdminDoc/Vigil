// Vigil NTP — vanilla JS, no deps. MV3-compliant (no inline scripts, no eval).
// Settings persist to chrome.storage.local when available, fallback to localStorage
// (so the same file can be opened directly with --load-extension or visited as
// a plain HTML page during development).

"use strict";

(function () {
  const SETTINGS_SCHEMA_VERSION = 1;
  const MAX_SHORTCUTS = 12;
  const MAX_SHORTCUT_NAME = 80;
  const MAX_URL_LENGTH = 2048;
  const MAX_NOTES_LENGTH = 10000;
  const MAX_CITY_LENGTH = 100;
  const MAX_RSS_FEEDS = 3;
  const MAX_RSS_FEED_LENGTH = 2048;
  const FETCH_TIMEOUT_MS = 8000;
  const MAX_JSON_BYTES = 256 * 1024;
  const MAX_RSS_BYTES = 512 * 1024;
  const OPEN_METEO_ORIGINS = new Set([
    "https://geocoding-api.open-meteo.com",
    "https://api.open-meteo.com"
  ]);

  const t = (key, substitutions) => globalThis.vigilI18n?.getMessage(key, substitutions) || key;

  const DEFAULT_SHORTCUTS = [
    { name: t("shortcutDuckDuckGo"), url: "https://duckduckgo.com" },
    { name: t("shortcutYouTube"),    url: "https://www.youtube.com" },
    { name: t("shortcutReddit"),     url: "https://www.reddit.com" },
    { name: t("shortcutGitHub"),     url: "https://github.com" },
    { name: t("shortcutWikipedia"),  url: "https://www.wikipedia.org" },
    { name: t("shortcutMojeek"),     url: "https://www.mojeek.com" }
  ];

  const DEFAULTS = {
    schemaVersion: SETTINGS_SCHEMA_VERSION,
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
                        && Boolean(chrome.storage && chrome.storage.local);

  function cloneDefaults() {
    return {
      ...DEFAULTS,
      shortcuts: DEFAULT_SHORTCUTS.map((shortcut) => ({...shortcut})),
      widgets: {...DEFAULTS.widgets},
      rssFeeds: []
    };
  }

  function isRecord(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function textValue(value, maxLength, trim = true) {
    if (typeof value !== "string") return "";
    const text = trim ? value.trim() : value;
    return text.slice(0, maxLength);
  }

  function isWebUrl(value) {
    try {
      const parsed = new URL(value);
      return ["http:", "https:"].includes(parsed.protocol)
        && !parsed.username && !parsed.password;
    } catch (e) {
      return false;
    }
  }

  function isHttpsUrl(value) {
    return isWebUrl(value) && new URL(value).protocol === "https:";
  }

  function normalizeSettings(value) {
    const stored = isRecord(value) ? value : {};
    const storedVersion = Number(stored.schemaVersion || 0);
    const source = storedVersion > SETTINGS_SCHEMA_VERSION ? {} : stored;
    const shortcuts = Array.isArray(source.shortcuts)
      ? source.shortcuts.map((shortcut) => {
        if (!isRecord(shortcut)) return null;
        const url = textValue(shortcut.url, MAX_URL_LENGTH);
        if (!isWebUrl(url)) return null;
        return {
          name: textValue(shortcut.name, MAX_SHORTCUT_NAME) || url,
          url
        };
      }).filter(Boolean).slice(0, MAX_SHORTCUTS)
      : cloneDefaults().shortcuts;
    const rssFeeds = Array.isArray(source.rssFeeds)
      ? Array.from(new Set(source.rssFeeds
        .map((url) => textValue(url, MAX_RSS_FEED_LENGTH))
        .filter(isHttpsUrl))).slice(0, MAX_RSS_FEEDS)
      : [];
    return {
      schemaVersion: SETTINGS_SCHEMA_VERSION,
      showClock: Boolean(source.showClock ?? DEFAULTS.showClock),
      use24h: Boolean(source.use24h ?? DEFAULTS.use24h),
      showShortcuts: Boolean(source.showShortcuts ?? DEFAULTS.showShortcuts),
      showSearch: Boolean(source.showSearch ?? DEFAULTS.showSearch),
      shortcuts,
      widgets: {
        notes: Boolean(source.widgets?.notes),
        topSites: Boolean(source.widgets?.topSites),
        bookmarks: Boolean(source.widgets?.bookmarks),
        weather: Boolean(source.widgets?.weather),
        rss: Boolean(source.widgets?.rss) && rssFeeds.length > 0
      },
      widgetNotes: textValue(source.widgetNotes, MAX_NOTES_LENGTH, false),
      bookmarkFolderId: textValue(source.bookmarkFolderId, 128),
      weatherCity: textValue(source.weatherCity, MAX_CITY_LENGTH),
      rssFeeds
    };
  }

  function load() {
    return new Promise((resolve) => {
      if (useChromeStorage) {
        chrome.storage.local.get([STORAGE_KEY], (res) => {
          const stored = res[STORAGE_KEY] || {};
          resolve(normalizeSettings(stored));
        });
      } else {
        try {
          const raw = localStorage.getItem(STORAGE_KEY);
          const stored = raw ? JSON.parse(raw) : {};
          resolve(normalizeSettings(stored));
        } catch (e) {
          resolve(cloneDefaults());
        }
      }
    });
  }

  function save(s) {
    const normalized = normalizeSettings(s);
    Object.keys(s).forEach((key) => delete s[key]);
    Object.assign(s, normalized);
    if (useChromeStorage) {
      chrome.storage.local.set({ [STORAGE_KEY]: normalized });
    } else {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
      } catch (e) { /* ignore */ }
    }
    return normalized;
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
  function shortcutMark(shortcut) {
    const name = textValue(shortcut.name, MAX_SHORTCUT_NAME);
    if (name) return name.slice(0, 1).toUpperCase();
    try {
      return new URL(shortcut.url).hostname.slice(0, 1).toUpperCase() || "•";
    } catch (e) {
      return "•";
    }
  }

  function renderShortcuts(settings) {
    shortcutsEl.replaceChildren();
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
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = shortcutMark(s);
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
    return text;
  }

  async function readBoundedResponse(response, maxBytes, contentTypes) {
    if (!response.ok) throw new Error("request failed");
    const contentType = (response.headers.get("content-type") || "")
      .split(";", 1)[0].trim().toLowerCase();
    if (!contentTypes.includes(contentType)) throw new Error("unexpected content type");
    const declaredLength = Number(response.headers.get("content-length"));
    if (Number.isFinite(declaredLength) && declaredLength > maxBytes) {
      throw new Error("response too large");
    }
    if (!response.body || !response.body.getReader) {
      const text = await response.text();
      if (new TextEncoder().encode(text).byteLength > maxBytes) {
        throw new Error("response too large");
      }
      return text;
    }
    const reader = response.body.getReader();
    const chunks = [];
    let total = 0;
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maxBytes) {
        await reader.cancel();
        throw new Error("response too large");
      }
      chunks.push(value);
    }
    const bytes = new Uint8Array(total);
    let offset = 0;
    chunks.forEach((chunk) => {
      bytes.set(chunk, offset);
      offset += chunk.byteLength;
    });
    return new TextDecoder().decode(bytes);
  }

  async function fetchBounded(url, {allowedOrigins, contentTypes, maxBytes}) {
    const parsed = new URL(url);
    if (!allowedOrigins.has(parsed.origin)) throw new Error("origin not allowed");
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
    try {
      const response = await fetch(parsed.href, {
        signal: controller.signal,
        redirect: "error",
        credentials: "omit",
        cache: "no-store"
      });
      return await readBoundedResponse(response, maxBytes, contentTypes);
    } finally {
      clearTimeout(timeout);
    }
  }

  function rssPermissionOrigins(feeds) {
    return Array.from(new Set(feeds.map((feed) => `${new URL(feed).origin}/*`)));
  }

  function checkRssPermissions(feeds, request) {
    const origins = rssPermissionOrigins(feeds);
    if (!origins.length) return Promise.resolve(false);
    if (!window.chrome || !chrome.permissions || !chrome.permissions[request]) {
      return Promise.resolve(!useChromeStorage);
    }
    return new Promise((resolve) => {
      try {
        chrome.permissions[request]({origins}, (granted) => resolve(Boolean(granted)));
      } catch (e) {
        resolve(false);
      }
    });
  }

  function hasRssPermissions(feeds) {
    return checkRssPermissions(feeds, "contains");
  }

  function requestRssPermissions(feeds) {
    return checkRssPermissions(feeds, "request");
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
        result.push({id: node.id, title: "  ".repeat(depth) + (node.title || t("folderFallback"))});
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
      select.replaceChildren();
      const automatic = document.createElement("option");
      automatic.value = "";
      automatic.textContent = t("automaticBookmarkFolder");
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
    const safeItems = items.filter((item) => item && isWebUrl(item.url));
    if (!safeItems.length) {
      appendMessage(card, emptyMessage);
      return;
    }
    const list = document.createElement("div");
    list.className = "widget-links";
    safeItems.forEach((item) => {
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
    notes.placeholder = t("privateNotesPlaceholder");
    notes.value = settings.widgetNotes || "";
    notes.addEventListener("input", () => {
      settings.widgetNotes = notes.value;
      save(settings);
    });
    card.appendChild(notes);
  }

  function renderTopSites(card) {
    if (!window.chrome || !chrome.topSites || !chrome.topSites.get) {
      appendMessage(card, t("topSitesUnavailable"));
      return;
    }
    chrome.topSites.get((sites) => {
      renderLinkList(card, (sites || []).slice(0, 6), t("noTopSites"));
    });
  }

  function renderBookmarks(card, settings) {
    bookmarkItems(settings).then((items) => {
      renderLinkList(card, items, t("chooseBookmarkFolder"));
    });
  }

  function renderWeather(card, settings) {
    const city = (settings.weatherCity || "").trim();
    if (!city) {
      appendMessage(card, t("chooseCity"));
      return;
    }
    appendMessage(card, t("loadingWeather"));
    const geocodeUrl = new URL("https://geocoding-api.open-meteo.com/v1/search");
    geocodeUrl.search = new URLSearchParams({
      name: city,
      count: "1",
      language: "en",
      format: "json"
    });
    fetchBounded(geocodeUrl.href, {
      allowedOrigins: OPEN_METEO_ORIGINS,
      contentTypes: ["application/json"],
      maxBytes: MAX_JSON_BYTES
    })
      .then((text) => JSON.parse(text))
      .then((locations) => {
        const location = locations.results && locations.results[0];
        if (!location) throw new Error("city not found");
        const latitude = Number(location.latitude);
        const longitude = Number(location.longitude);
        if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
          throw new Error("invalid coordinates");
        }
        const forecastUrl = new URL("https://api.open-meteo.com/v1/forecast");
        forecastUrl.search = new URLSearchParams({
          latitude: String(latitude),
          longitude: String(longitude),
          current: "temperature_2m,weather_code",
          temperature_unit: "fahrenheit"
        });
        return fetchBounded(forecastUrl.href, {
          allowedOrigins: OPEN_METEO_ORIGINS,
          contentTypes: ["application/json"],
          maxBytes: MAX_JSON_BYTES
        })
          .then((text) => ({location, weather: JSON.parse(text)}));
      })
      .then(({location, weather}) => {
        card.querySelector(".widget-message")?.remove();
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
        if (message) message.textContent = t("weatherUnavailable");
      });
  }

  function parseFeed(text) {
    const documentNode = new DOMParser().parseFromString(text, "application/xml");
    if (documentNode.querySelector("parsererror")) return [];
    return Array.from(documentNode.querySelectorAll("item, entry")).slice(0, 3)
      .map((item) => {
        const rawTitle = item.querySelector("title")?.textContent;
        const title = textValue(rawTitle, MAX_SHORTCUT_NAME);
        const linkNode = item.querySelector("link");
        const href = linkNode?.getAttribute("href") || linkNode?.textContent?.trim();
        return {title, url: textValue(href, MAX_RSS_FEED_LENGTH)};
      })
      .filter((item) => item.title && isHttpsUrl(item.url));
  }

  function renderRss(card, settings) {
    const feeds = (settings.rssFeeds || []).filter(isHttpsUrl).slice(0, 3);
    if (!feeds.length) {
      appendMessage(card, t("addRss"));
      return;
    }
    const allowedOrigins = new Set(feeds.map((feed) => new URL(feed).origin));
    appendMessage(card, t("loadingFeeds"));
    hasRssPermissions(feeds).then((granted) => {
      if (!granted) throw new Error(t("rssPermissionNotGranted"));
      return Promise.all(feeds.map((url) => fetchBounded(url, {
        allowedOrigins,
        contentTypes: [
          "application/atom+xml",
          "application/rss+xml",
          "application/xml",
          "text/plain",
          "text/xml"
        ],
        maxBytes: MAX_RSS_BYTES
      })));
    })
      .then((documents) => documents.flatMap(parseFeed).slice(0, 3))
      .then((items) => {
        const message = card.querySelector(".widget-message");
        if (message) message.remove();
        renderLinkList(card, items, t("noRecentFeed"));
      })
      .catch(() => {
        const message = card.querySelector(".widget-message");
        if (message) message.textContent = t("feedsUnavailable");
      });
  }

  function renderWidgets(settings) {
    const enabled = settings.widgets || {};
    widgetsEl.replaceChildren();
    if (!Object.values(enabled).some(Boolean)) {
      widgetsEl.style.display = "none";
      return;
    }
    widgetsEl.style.display = "grid";
    const add = (card) => widgetsEl.appendChild(card);
    if (enabled.notes) {
      const card = widgetCard(t("notes"), "widget-notes-card");
      renderNotes(card, settings);
      add(card);
    }
    if (enabled.topSites) {
      const card = widgetCard(t("topSites"), "widget-top-sites-card");
      renderTopSites(card);
      add(card);
    }
    if (enabled.bookmarks) {
      const card = widgetCard(t("bookmarkFolder"), "widget-bookmarks-card");
      renderBookmarks(card, settings);
      add(card);
    }
    if (enabled.weather) {
      const card = widgetCard(t("weather"), "widget-weather-card");
      renderWeather(card, settings);
      add(card);
    }
    if (enabled.rss) {
      const card = widgetCard(t("rss"), "widget-rss-card");
      renderRss(card, settings);
      add(card);
    }
  }

  function renderEditor(settings) {
    editorEl.replaceChildren();
    settings.shortcuts.forEach((s, i) => {
      const row = document.createElement("div");
      row.className = "shortcut-edit-row";

      const nameInput = document.createElement("input");
      nameInput.type = "text";
      nameInput.placeholder = t("namePlaceholder");
      nameInput.value = s.name;
      nameInput.addEventListener("input", () => {
        settings.shortcuts[i].name = nameInput.value;
        save(settings);
        renderShortcuts(settings);
      });

      const urlInput = document.createElement("input");
      urlInput.type = "text";
      urlInput.placeholder = t("urlPlaceholder");
      urlInput.value = s.url;
      urlInput.addEventListener("input", () => {
        settings.shortcuts[i].url = urlInput.value;
        save(settings);
        renderShortcuts(settings);
      });

      const rm = document.createElement("button");
      rm.className = "btn-remove";
      rm.title = t("removeShortcut");
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
  function setRssStatus(message) {
    const statusEl = $("widget-rss-status");
    if (statusEl) statusEl.textContent = message;
  }

  function parseRssFeeds(value) {
    return Array.from(new Set(String(value || "").split(/\r?\n/)
      .map((url) => textValue(url, MAX_RSS_FEED_LENGTH))
      .filter(isHttpsUrl))).slice(0, MAX_RSS_FEEDS);
  }

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
  load().then(async (settings) => {
    if (settings.widgets.rss && !(await hasRssPermissions(settings.rssFeeds))) {
      settings.widgets.rss = false;
      save(settings);
      setRssStatus(t("savedRssPermissionMissing"));
    }
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
      ["opt-widget-weather", "weather"]
    ].forEach(([id, key]) => {
      $(id).addEventListener("change", (e) => {
        settings.widgets[key] = e.target.checked;
        save(settings);
        renderWidgets(settings);
      });
    });
    $("opt-widget-rss").addEventListener("change", async (e) => {
      if (!e.target.checked) {
        settings.widgets.rss = false;
        save(settings);
        setRssStatus("");
        renderWidgets(settings);
        return;
      }
      const feeds = parseRssFeeds($("widget-rss-feeds").value);
      if (!feeds.length) {
        e.target.checked = false;
        settings.widgets.rss = false;
        save(settings);
        setRssStatus(t("addHttpsFeed"));
        renderWidgets(settings);
        return;
      }
      if (!(await requestRssPermissions(feeds))) {
        e.target.checked = false;
        settings.widgets.rss = false;
        save(settings);
        setRssStatus(t("rssPermissionDenied"));
        renderWidgets(settings);
        return;
      }
      settings.rssFeeds = feeds;
      settings.widgets.rss = true;
      save(settings);
      setRssStatus(t("rssLimited"));
      renderWidgets(settings);
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
      const feeds = parseRssFeeds(e.target.value);
      if (!settings.widgets.rss) {
        settings.rssFeeds = feeds;
        save(settings);
        syncToggles(settings);
        return;
      }
      requestRssPermissions(feeds).then((granted) => {
        if (!granted) {
          syncToggles(settings);
          setRssStatus(t("savedFeedsUnchanged"));
          return;
        }
        settings.rssFeeds = feeds;
        save(settings);
        syncToggles(settings);
        setRssStatus(t("rssLimited"));
        renderWidgets(settings);
      });
    });
    $("add-shortcut").addEventListener("click", () => {
      if (settings.shortcuts.length >= MAX_SHORTCUTS) return;
      settings.shortcuts.push({ name: t("newSite"), url: "https://example.com" });
      save(settings);
      renderEditor(settings);
      renderShortcuts(settings);
    });
  });
})();
