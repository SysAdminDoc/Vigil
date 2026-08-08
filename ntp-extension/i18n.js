// English fallback and Chrome i18n bridge for the Vigil New Tab extension.
(function () {
  "use strict";

  const FALLBACKS = Object.freeze({
    pageTitle: "Vigil — New Tab",
    extensionName: "Vigil New Tab",
    extensionShortName: "Vigil NTP",
    extensionDescription: "Vigil's lean, dark new-tab page with optional local widgets. Network widgets are opt-in.",
    searchPlaceholder: "Search or type a URL",
    searchLabel: "Search",
    pinnedShortcuts: "Pinned shortcuts",
    optionalWidgets: "Optional widgets",
    settingsButtonTitle: "Vigil NTP settings",
    openSettings: "Open new-tab settings",
    settingsTitle: "Vigil New Tab",
    showClock: "Show clock",
    showClockDesc: "Display time on the new-tab page",
    time24: "24-hour time",
    time24Desc: "Use 24-hour format instead of 12-hour",
    showShortcuts: "Show shortcuts",
    showShortcutsDesc: "Display the quick-access shortcut grid",
    showSearch: "Show search bar",
    showSearchDesc: "Display the search input",
    widgetsHeading: "Widgets",
    notes: "Notes",
    notesDesc: "A local-only scratchpad",
    topSites: "Top sites",
    topSitesDesc: "Show your most visited sites",
    bookmarkFolder: "Bookmark folder",
    bookmarkFolderDesc: "Show links from one local folder",
    automaticBookmarkFolder: "First bookmark folder",
    weather: "Weather",
    weatherDesc: "Open-Meteo forecast for a city you choose",
    weatherCityPlaceholder: "City, e.g. Boston",
    weatherCityLabel: "Weather city",
    rss: "RSS quick-feed",
    rssDesc: "Up to three HTTPS feeds, one per line",
    rssFeedsPlaceholder: "https://example.com/feed.xml",
    rssFeedsLabel: "RSS feed URLs",
    shortcutsHeading: "Shortcuts",
    addShortcut: "+ Add shortcut",
    close: "Close",
    shortcutDuckDuckGo: "DuckDuckGo",
    shortcutYouTube: "YouTube",
    shortcutReddit: "Reddit",
    shortcutGitHub: "GitHub",
    shortcutWikipedia: "Wikipedia",
    shortcutMojeek: "Mojeek",
    newSite: "New site",
    folderFallback: "Folder",
    privateNotesPlaceholder: "Private notes stay in this browser profile",
    topSitesUnavailable: "Top sites are only available in the installed extension.",
    noTopSites: "No top sites yet.",
    chooseBookmarkFolder: "Choose a bookmark folder in NTP settings.",
    chooseCity: "Choose a city in NTP settings to load weather.",
    loadingWeather: "Loading weather…",
    weatherUnavailable: "Weather is unavailable right now.",
    addRss: "Add up to three HTTPS feeds in NTP settings.",
    loadingFeeds: "Loading feeds…",
    rssPermissionNotGranted: "RSS permission not granted",
    noRecentFeed: "No recent feed entries.",
    feedsUnavailable: "Feeds are unavailable or not permitted.",
    namePlaceholder: "Name",
    urlPlaceholder: "URL",
    removeShortcut: "Remove",
    savedRssPermissionMissing: "RSS access is not granted for the saved feeds.",
    addHttpsFeed: "Add at least one HTTPS feed before enabling RSS.",
    rssPermissionDenied: "RSS permission was not granted; no feed was contacted.",
    rssLimited: "RSS access is limited to the saved HTTPS feed origins.",
    savedFeedsUnchanged: "RSS permission was not granted; saved feeds were unchanged."
  });

  function substitute(message, substitutions) {
    const values = Array.isArray(substitutions) ? substitutions : [substitutions];
    return message.replace(/\$(\d+)/g, (match, index) => values[Number(index) - 1] ?? match);
  }

  function getMessage(key, substitutions) {
    try {
      const localized = globalThis.chrome?.i18n?.getMessage?.(key, substitutions);
      if (localized) return localized;
    } catch (error) {
      // The fallback is also used by the plain-file development path.
    }
    return substitute(FALLBACKS[key] || key, substitutions);
  }

  function localize(documentNode = globalThis.document) {
    if (!documentNode) return;
    documentNode.querySelectorAll("[data-i18n]").forEach((element) => {
      element.textContent = getMessage(element.dataset.i18n);
    });
    const attributes = {
      "data-i18n-aria-label": "aria-label",
      "data-i18n-placeholder": "placeholder",
      "data-i18n-title": "title"
    };
    Object.entries(attributes).forEach(([marker, attribute]) => {
      documentNode.querySelectorAll(`[${marker}]`).forEach((element) => {
        element.setAttribute(attribute, getMessage(element.getAttribute(marker)));
      });
    });
  }

  globalThis.vigilI18n = Object.freeze({getMessage, localize});
  localize();
})();
