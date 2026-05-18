# X19 — NTP widgets v2

**Status:** design doc. Implementation lives in `ntp-extension/`; no
Chromium-source dependency.

## Goal

Extend the bundled Vigil NTP with optional widgets, keeping the entire
extension under 320 KB. Every widget is opt-in; the v0.2 NTP (clock + search
+ shortcuts) is the baseline-on default.

## Widgets to add

| Widget | Cost | Notes |
|---|---|---|
| **Weather** | small (~3 KB) | Open-Meteo, no API key, lat/long from `chrome.geolocation` only after user opt-in |
| **Top sites** | small (~2 KB) | `chrome.topSites` MV3 API; 6 tiles below shortcuts |
| **Bookmark folder** | small (~3 KB) | `chrome.bookmarks.getSubTree`; pick one folder, render its top 8 items |
| **RSS quick-feed** | medium (~12 KB) | 3 most-recent items from up to 3 feeds; parser ships in extension; refresh on tab open |
| **Notes** | small (~2 KB) | localStorage-backed plain-text scratch box; no sync |
| **Stock ticker** | rejected | unbounded API key requirements; out of scope |
| **Calendar** | rejected | drags in Mail/Calendar scope creep we explicitly rejected |

## Implementation outline

1. Extend `ntp-extension/manifest.json` permissions: add `topSites`,
   `bookmarks`, `geolocation` (optional).
2. Add `widgets/` subdir to the extension with one JS file per widget; each
   exports a `render(container, options)` and `destroy()` API.
3. Settings panel grows a "Widgets" section with one toggle per widget.
4. Layout grid: optional widgets stack below the search bar; visual budget
   is one screen, no scroll.

## Verification

- Disable all widgets &rarr; NTP renders identically to v0.2 (clock + search
  + shortcuts).
- Enable each widget individually &rarr; renders inside ~50 ms; no console
  errors.
- `du -sh ntp-extension` stays under 320 KB.

## Decision gates

- **Weather widget**: requires `geolocation` permission grant. Without it,
  fall back to IP-geoloc via `https://ipapi.co/json/`? **No** &mdash; that's
  a network call to a third party. Default to a user-entered city name.
- **RSS feeds**: storing feed URLs in `chrome.storage.local` is fine; URLs
  aren't sensitive. But fetched feed content could be. Render in a sandboxed
  iframe; never inject feed HTML into the NTP DOM.

## Ship order

v0.3: notes + top sites + bookmark folder (no network).
v0.4: weather + RSS quick-feed (gated permissions).
