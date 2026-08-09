# Changelog

All notable changes to **Vigil Browser** are documented in this file. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project tracks Chromium's
stable version, so versions are written as `<vigil>-c<chromium>` &mdash; for example
`0.2.1-c145.0.7632.159`.

## [Unreleased] &mdash; v0.2.1

### Build & release pipeline (T4)

- **Chromium security-refresh gate.** Added a dependency-free, fail-closed
  release gate with a committed 14-day security-age and one-major-release lag
  policy. It reports the Chromium, ungoogled, and Vigil revisions from the
  repository plus the signed-off upstream metadata used for the release.
- **Pinned offline uBlock delivery.** uBlock Origin 1.72.2 is now described by a
  committed release URL and SHA-256 digest, resolved from the verified build
  cache first, and extracted only after ZIP path/size/version validation. The
  bundled extension policy no longer points at the Chrome Web Store.
- **Auditable GitHub workflows.** Replaced the old personal-fork/PAT Winget
  action and dead staged build action with immutable-SHA quality and manual
  release-validation workflows. They use least-privilege read access and
  upload reviewable receipts/artifacts without force-pushing external repos.
- **Unsigned release receipt and hash gate.** Packaging can emit a JSON receipt
  with SHA-256 hashes, source/toolchain/uBlock inputs, and explicit unsigned
  status. Strict release validation updates package-manager manifests only from
  present artifacts and fails on missing architectures or placeholder hashes.
- **Structured privacy-safe diagnostics.** Release gates and smoke tests now
  emit stable check IDs and failure codes, while `devutils/diagnostics.py`
  combines their reports into a support receipt containing release versions,
  toolchain IDs, and architecture evidence with URLs, absolute/profile paths,
  and keyed secrets redacted. Kiosk event messages use an explicit 512-character
  bound.
- **Explicit architecture contract.** Packaging now normalizes x64/x86/arm64
  names against Chromium’s legacy `FILES.cfg` tags and the GN target, rejecting
  mismatches before creating a portable archive or MSI.
- **MSI component ownership corrected.** The per-machine Start Menu component
  now uses an HKLM key path, and a silent lifecycle harness covers administrative
  extraction plus optional install/repair/uninstall validation.
- **Extension permission and messaging boundaries tightened.** NTP weather uses
  fixed API origins, RSS uses user-granted per-origin optional access with bounded
  requests, and the command palette uses on-demand `activeTab` injection with
  exact iframe source/origin checks. Static permission, sink, and syntax checks
  now run in CI.
- **Kiosk recovery hardened.** The launcher now accepts only one validated HTTPS
  URL or `about:blank`, leaves autoplay to managed policy, and passes no caller
  arguments through to Chromium. The watchdog uses a non-interpolated config,
  bounded exponential backoff, a circuit breaker, bounded event messages, and
  ownership-aware uninstall cleanup.
- **Release documentation reconciled.** README now names the authoritative
  version/toolchain sources and executable output contract; a documentation
  contract test checks version alignment, required workflows, and local links.
- **First-run egress contract.** NTP shortcut marks are local instead of
  fetching Google favicons, default widget paths remain network-free, and an
  offline privacy probe verifies suggestion, Safe Browsing, telemetry, and
  extension egress boundaries.
- **Owned-extension localization contract.** The NTP and command palette now
  ship an English locale baseline, local fallback lookup, localized manifest
  metadata, and static coverage for dynamic, accessibility, and service-worker
  strings without adding a translation network dependency.
- **Offline build recovery contract.** Added fail-closed cache/source preflight,
  unfinished-download detection, development-only SSL-bypass marking, and
  atomic/recoverable overlay, extension, package, archive, and MSI staging.
- **Local profile migration.** Added a versioned JSON export/import tool for
  selected NTP settings, shortcuts, notes, and HTTP(S) bookmarks with dry-run
  conflict reporting and explicit password, cookie, and history exclusion.
- **Opt-in Global Privacy Control.** Added an off-by-default settings toggle,
  `Sec-GPC: 1` header injection, Window/Worker DOM exposure, and a browser
  fixture covering enabled/disabled behavior. The signal is advisory and is not
  a legal-compliance guarantee.

### Defaults & first-run (T2, T5)

- **Default search engine: DuckDuckGo.** Replaces Google with `suggest_url` keystroke
  upload. Google, Brave Search, Startpage, Kagi, and Mojeek ship as built-in alternates
  the user can switch to in one click. Roadmap item `N1`.
- **HTTPS-First (Balanced) mode is ON.** `https_only_mode_enabled` and
  `https_first_balanced_mode_enabled` are both set true in `initial_preferences`,
  putting Vigil ahead of Chrome 154's October-2026 default-on schedule. Roadmap `N2`.
- **Safe Browsing is back on; telemetry uploads are off.** `safebrowsing.enabled=true`
  with `enhanced=false`, `scout_reporting_enabled=false`,
  `extended_reporting_enabled=false`. We were giving up phishing protection without a
  privacy benefit. Roadmap `N4`.
- **Default-deny content settings** for `usb_devices`, `serial_ports`, `hid_devices`,
  `bluetooth_devices`, `idle_detection`, `local_fonts`, `payment_handler`, `ar`, `vr`,
  `automatic_downloads`. Driven by CVE-2026-5276 (Edge WebUSB) and CVE-2026-4680
  (Chrome FedCM UAF). The matching managed-policy baseline is shipped in the
  portable archive for administrator deployments. Roadmap `N5`.
- **Privacy Sandbox APIs (Topics, Protected Audience, Attribution Reporting) off.**
  Retired by Google in October 2025; we disable the prefs anyway so the surface
  doesn't quietly come back on a Chromium bump. Roadmap `N6`.

### Project health (T10)

- **CHANGELOG format fixed.** Replaces the broken `%Y->-` placeholder with a
  Keep-a-Changelog structure. Roadmap `N11`.
- **`docs/ARCHITECTURE.md`** documents how `chromium_src/`, `patches/`,
  `initial_preferences`, `apply_overlays.py`, and `setup_extensions.py` interact.
  Roadmap `N13`.
- **`CONTRIBUTING.md`** with PR conventions, overlay-vs-patch decision tree, and
  how-to-bump-Chromium. Roadmap `N13`.
- **`docs/toolchain.md`** pins the exact clang / rustc / ninja / gn / Python / VS
  Build Tools / Windows SDK versions per Chromium milestone. Roadmap `N12`.
- **`docs/build-environment.md`** records the build-host env-var floor for partial
  reproducibility. Roadmap `N10`.
- **`devutils/smoke_test.py`** &mdash; deterministic local smoke test that verifies the
  packaged uBO, managed defaults, `initial_preferences`, default search, and NTP
  wiring without launching Chromium. Roadmap `N14`.

### Build & release pipeline (T4)

- **Fail-closed local packaging.** uBlock Origin and the bundled NTP must stage
  successfully before an artifact is created; the supported release path remains
  the local Windows build. Roadmap `N7`/`N9` are intentionally not represented as
  hosted CI in this repository.
- **winget manifest** at `dist/winget/SysAdminDoc.Vigil/<version>/` is prepared
  locally; publication to `microsoft/winget-pkgs` remains external. Roadmap `N15`.

### Next-tier scaffolds (T3, T6, T7)

- **Memory Saver default.** Chromium's existing performance page now starts
  tab hibernation enabled while retaining its aggressiveness and per-domain
  exception controls. Roadmap `X16`.
- **Vertical tabs.** Chromium's existing vertical-tab implementation is enabled
  by default, exposing its built-in tab-strip position toggle in Appearance
  settings. Roadmap `X14`.
- **Split view.** Chromium's two-pane split view is enabled with its toolbar
  button pinned by default and `Ctrl+Shift+\\` bound to create a split. Roadmap
  `X15`.
- **Reader Mode and Markdown export.** Chromium's desktop Read Anything
  distiller is enabled with its omnibox entry point; the reader toolbar can
  download the distilled article as Markdown. Roadmap `X17`.
- **WebRTC hardening retained.** Chromium 145 already generates DTLS
  identities per session factory, uses RSA-2048 defaults, creates fresh SSL
  sessions for DTLS streams, and applies ephemeral key-exchange groups. The
  build now fails closed if those upstream guarantees regress. Roadmap `X5`.
- **Optional NTP widgets.** The bundled new-tab page now supports opt-in local
  notes, top sites, and bookmark-folder links, plus city-based Open-Meteo
  weather and up to three HTTPS RSS feeds. All widget settings persist locally
  and the extension remains under the 320 KB budget. Roadmap `X19`.
- **Command palette extension.** `Ctrl+Shift+P` opens a keyboard-first palette
  over normal web pages (or a fallback extension tab on browser-owned pages),
  searching Vigil settings, open tabs, bookmarks, and seven-day history. Its
  combobox/listbox semantics, retryable errors, latest-query sequencing, and
  focus restoration are covered by static contract tests.
  Roadmap `X18`.
- **Sticky Secure DNS defaults.** The existing settings resolver picker now
  includes Quad9, NextDNS, Cloudflare, Mullvad, AdGuard, and Control D, starts
  new profiles on Quad9 with no automatic fallback, and retains hostname
  validation for custom endpoints. Roadmap `X6`.
- **WiX MSI packaging is now part of the local release path.** `package.py`
  harvests the same curated runtime files used by the portable archive into a
  per-machine MSI with a Start Menu shortcut, suitable for Group Policy and
  Intune deployment. Roadmap `X11`.
- **Client Hints are disabled by default.** Vigil enables ungoogled's
  `RemoveClientHints` feature to reduce UA-CH fingerprinting surface while
  retaining the existing flag for an explicit per-profile override. Roadmap
  `X7`.
- **Manifest V2 retention is now an enforced build contract.** Vigil documents
  its MV2 policy and verifies the pinned ungoogled-chromium retention patch,
  allowed-manifest behavior, and warning-only deprecation stage on every full
  or incremental build. A missing or ineffective patch fails the build before
  compilation starts. Roadmap `X1`.
- **`policies/vigil-extension-forcelist.json`** &mdash; documented
  `ExtensionInstallForcelist` template defaulting to bundled uBO; admins extend.
  Roadmap `X3`.
- **`admx/vigil.admx` + `admx/en-US/vigil.adml`** &mdash; Vigil ADMX template
  covering the Chrome-policy subset every IT admin actually configures
  (extension lists, URL block/allowlist, managed bookmarks, search-engine lock,
  proxy mode, etc.). Roadmap `X10`.
- **`kiosk/`** &mdash; Vigil-Kiosk launcher script, `branding-kiosk.json` variant,
  Windows-Task-Scheduler watchdog template. Roadmap `X12`.
- **`chromium_src/components/policy/resources/webui/vigil_policy_theme.css`** &mdash;
  chrome://policy themed through the Chromium 145 WebUI resource bundle. Roadmap `X13`.
- **`dist/scoop/vigil.json`** + **`dist/chocolatey/vigil.nuspec`** &mdash; package
  manifests for Scoop and Chocolatey publication. Roadmap `X21`.
- **`tools/vigil-portable.cmd`** &mdash; portable-mode launcher with a noninteractive
  `--init` sentinel setup path (Supermium-style). Roadmap `X23`.
- **`ntp-extension/`** &mdash; the dark Vigil NTP repackaged as a bundled extension
  with `chrome_url_overrides.newtab`, fixing the previously-broken
  `chrome://newtab` wiring. Its stable public key is committed, so packaging
  does not launch Chromium to generate an extension identity. Roadmap `N3`.

- **`devutils/changelog.py`** generates dated Keep-a-Changelog release sections
  from conventional git commits and refuses duplicate release headings. Roadmap `N11`.

### Design docs &mdash; require Chromium source tree to land

These items are specified in `docs/design/` and reference upstream patch sources;
they cannot compile from this build environment until a full Chromium checkout
is available.

- `docs/design/X1-mv2-retention.md` &mdash; Manifest V2 retention patch plan
- `docs/design/X5-iridium-webrtc.md` &mdash; Iridium WebRTC hardening backport
- `docs/design/X8-anti-fingerprinting.md` &mdash; curated anti-fingerprint patch set
- `docs/design/X20-velopack.md` &mdash; auto-updater integration plan

## [0.1.0] &mdash; 2026-04-13

First Vigil-branded release. Forked from
[ungoogled-chromium-windows](https://github.com/ungoogled-software/ungoogled-chromium-windows)
at Chromium 145.0.7632.159.

### Added

- Vigil branding: `branding.json`, generated shield-and-eye icon set
  (`branding/generate_icons.py`, all sizes incl. `.ico`).
- Brave-style `chromium_src/` overlay system; `apply_overlays.py` applies overlays
  + custom NTP + icons + branding at build time.
- Dark Vigil NTP HTML at `ntp/newtab.html` &mdash; clock, search, configurable
  shortcuts, settings panel.
- Pre-bundled **uBlock Origin** via `setup_extensions.py`, downloaded from
  `gorhill/uBlock` GitHub releases.
- Patches restoring **Chrome Web Store** and **Google search engine** that
  ungoogled-chromium strips.
- Vigil dark theme overlays for every `chrome://` internal page we touch:
  `settings`, `flags`, `history`, `bookmarks`, `downloads`, `extensions`,
  plus `neterror` and the security-interstitial CSS.
- `initial_preferences` block setting first-run defaults: bookmark bar on, DNT on,
  autofill off, translate off, network prediction off, no sign-in prompt.
- README badges; `requirements.txt`; AGENTS.md pointer to CLAUDE.md.

### Notes (corrected from the original v0.1 changelog)

- Original CHANGELOG.md was malformed (`%Y->-` placeholder, merge-commit text on
  the version line). This entry replaces it &mdash; see [`N11`](ROADMAP.md) in the
  roadmap.

## Pre-fork &mdash; upstream ungoogled-chromium-windows history

Vigil inherits the upstream Chromium-bump cadence from
[ungoogled-software/ungoogled-chromium-windows](https://github.com/ungoogled-software/ungoogled-chromium-windows).
Recent upstream releases prior to the Vigil fork (selected):

- 2026-03-04 &mdash; Chromium 145.0.7632.159 (upstream PR #546)
- 2026-02-27 &mdash; Chromium 145.0.7632.116
- 2026-02-15 &mdash; Chromium 145.0.7632.75-1
- 2026-02-11 &mdash; Chromium 145.0.7632.45-1
- 2026-02-04 &mdash; Chromium 144.0.7559.132-1
- 2026-01-21 &mdash; Chromium 144.0.7559.96-1
- 2026-01-08 &mdash; Chromium 143.0.7499.192-1
- 2025-12-20 &mdash; Chromium 143.0.7499.169-1
- 2025-11-25 &mdash; CPU-thread-count CLI flag added (upstream)
- 2025-11-18 &mdash; Chromium 142.0.7444.175-1
- 2025-09-09 &mdash; Chromium 140.0.7339.80-1
- 2025-08-28 &mdash; Chromium 139.0.7258.154-1
- 2025-07-31 &mdash; Chromium 138.0.7204.183-1

For the full upstream history see
<https://github.com/ungoogled-software/ungoogled-chromium-windows/commits/master>.
