# Changelog

All notable changes to **Vigil Browser** are documented in this file. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project tracks Chromium's
stable version, so versions are written as `<vigil>-c<chromium>` &mdash; for example
`0.2.0-c145.0.7632.159`.

## [Unreleased] &mdash; v0.2.0

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
