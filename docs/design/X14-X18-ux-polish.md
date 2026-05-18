# X14&ndash;X18 — UX polish: parity wins, no novelty tax

**Status:** design doc; mix of flag-only (cheap) and small-patch (medium)
items. Each section flags the cost.

These five features all exist as primitives in upstream Chromium today.
Vigil's job is to *expose* them via the themed settings overlay so a non-
power-user finds them.

---

## X14 — Vertical tabs

**Cost: trivial.** Chromium ships the side panel pin family already. Edge
and Brave both flipped a single feature flag.

**Action:**
1. Add to `flags.windows.gn` (already used to bake build flags): enable
   `kSidePanelPinning` and `kVerticalTabsExperiment` (per current milestone
   feature names; verify in `chrome/browser/ui/ui_features.cc`).
2. Add an entry to the Vigil-themed `chrome://settings/appearance` section:
   "Tab layout: Horizontal / Vertical" with the toggle wired to the pref
   `vertical_tabs_enabled` (already an upstream pref behind the flag).
3. Document at `docs/features/vertical-tabs.md` once shipped.

**Verification:** open Vigil, toggle Vertical Tabs in Settings, confirm
tabs render on the left and persist across sessions.

---

## X15 — Split view (2-pane)

**Cost: low.** Brave shipped this in 2026 against a Chromium primitive.
Zen does 2&times;2 but we explicitly ship 2-pane only (Brave-style).

**Action:**
1. Enable feature flag `kSideBySide` (verify name per milestone) in
   `flags.windows.gn`.
2. Add a toolbar button via small overlay
   `chromium_src/chrome/browser/ui/views/toolbar/toolbar_view.cc` (or its
   `.ts.html` equivalent for newer milestones).
3. Keyboard: `Ctrl+Shift+\\` opens current tab in split.

**Verification:** click the split toolbar button; second pane opens. Drag a
tab between panes; tab moves. Close one pane; remaining pane fills window.

---

## X16 — Tab hibernation / Sleeping Tabs

**Cost: low.** Chromium has `chrome.tabs.discard` and the underlying memory
saver mode shipped in M108.

**Action:**
1. Default `memory_saver_mode_enabled = true` in `initial_preferences`. Add
   to v0.2's prefs file as a follow-up &mdash; **note**: skipped from v0.2
   pending verification that the pref key is stable across Chromium 145.
2. Add a Vigil-themed page section at `chrome://settings/performance` with
   a per-domain exception list (the upstream UI exists; verify it survives
   our settings overlay).

**Verification:** open ~30 tabs; wait the configured idle interval; confirm
inactive tabs lose their renderer process (visible in `chrome://discards`).

---

## X17 — Reader mode

**Cost: medium.** Chromium ships the DOM Distiller behind the
`#enable-reader-mode` flag. Brave's SpeedReader is heavier but the upstream
distiller covers the basics.

**Action:**
1. Enable `kReaderMode` feature flag in `flags.windows.gn`.
2. Add a toolbar button via overlay (same pattern as X15).
3. Plumb a Markdown export via a small content-script-style postprocessor:
   take the distilled HTML, run through a turndown-style converter (we can
   bundle `turndown.js` in the NTP extension's resources to keep it
   first-party).
4. Keyboard: `Ctrl+Alt+R` toggles reader.

**Verification:** open a long-form article; click reader; confirm the
distilled view; click Export Markdown; confirm `.md` download.

---

## X18 — Command palette (Ctrl+Shift+P)

**Cost: medium-low.** Floorp 12.14.0 has one (Firefox-side); Vivaldi's
"Quick Commands" is the model. Chromium has no native command palette.

**Action:**
1. Implement as a bundled extension (`palette-extension/`) similar to
   `ntp-extension/`. The extension declares a keyboard shortcut command and
   opens an iframe over the current tab with a fuzzy-search list of:
   - All `chrome://` pages (whitelisted)
   - Current open tabs (via `chrome.tabs.query`)
   - Bookmarks (via `chrome.bookmarks.search`)
   - History items from the last 7 days
2. Force-install via `ExtensionInstallForcelist` (same mechanism as uBO).

**No upstream patch needed.** This is pure extension work; shippable
without Chromium source-tree access.

**Verification:** press Ctrl+Shift+P; the palette opens; type "set" and
hit Enter; `chrome://settings` opens.

---

## Sequencing

- X14, X15 ship together &mdash; they share the toolbar overlay file.
- X16 is a pref-and-settings-page change; small.
- X17 needs distinct toolbar work and the markdown converter bundle.
- X18 is a bundled extension &mdash; can be developed and shipped without
  rebuilding Chromium.

Recommended ship order: **X18 (extension) &rarr; X14 (flag) &rarr;
X16 (pref) &rarr; X15 (toolbar) &rarr; X17 (toolbar + converter)**.

This puts the no-source-tree-needed work first so it ships even if other
patches stall on a Chromium bump.
