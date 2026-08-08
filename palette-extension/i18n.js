// English fallback and Chrome i18n bridge for the Vigil Command Palette.
(function () {
  "use strict";

  const FALLBACKS = Object.freeze({
    extensionName: "Vigil Command Palette",
    extensionShortName: "Vigil Palette",
    extensionDescription: "A keyboard-first launcher for Vigil settings, tabs, bookmarks, and recent history.",
    openPaletteCommand: "Open the Vigil command palette",
    pageTitle: "Vigil Command Palette",
    eyebrow: "VIGIL COMMAND PALETTE",
    heading: "What do you want to open?",
    queryPlaceholder: "Search settings, tabs, bookmarks, or history",
    queryLabel: "Search commands",
    resultsLabel: "Palette results",
    navigateHint: "navigate",
    openHint: "open",
    closeHint: "close",
    kindPage: "page",
    kindTab: "tab",
    kindBookmark: "bookmark",
    kindHistory: "history",
    noMatches: "No matching commands or saved pages.",
    oneResult: "1 result",
    manyResults: "$1 results",
    searching: "Searching…",
    searchUnavailable: "Palette data is unavailable. Press Enter to retry.",
    openTargetError: "Could not open that target.",
    openTargetRetry: "Could not open that target. Retry.",
    invalidTarget: "Invalid target",
    unsupportedTarget: "Unsupported target",
    bookmarkSubtitle: "Bookmark",
    openTabSubtitle: "Open tab",
    historySubtitle: "History · last 7 days",
    commandSettings: "Settings",
    commandExtensions: "Extensions",
    commandDownloads: "Downloads",
    commandBookmarks: "Bookmarks",
    commandHistory: "History",
    commandFlags: "Flags",
    commandPolicy: "Policy",
    commandDiscards: "Discards",
    commandNetworkInternals: "Network internals",
    commandWebRtcInternals: "WebRTC internals",
    commandVersion: "Version",
    urlSettings: "chrome://settings",
    urlExtensions: "chrome://extensions",
    urlDownloads: "chrome://downloads",
    urlBookmarks: "chrome://bookmarks",
    urlHistory: "chrome://history",
    urlFlags: "chrome://flags",
    urlPolicy: "chrome://policy",
    urlDiscards: "chrome://discards",
    urlNetworkInternals: "chrome://net-internals",
    urlWebRtcInternals: "chrome://webrtc-internals",
    urlVersion: "chrome://version"
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
