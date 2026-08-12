# Changelog

All notable changes to **Vigil Browser** are documented in this file. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project tracks Chromium's
stable version, so versions are written as `<vigil>-c<chromium>` &mdash; for example
`0.2.1-c145.0.7632.159`.

## [Unreleased] &mdash; v0.2.3

### Release synchronization

- Drained the actionable roadmap after verifying the implemented Windows build,
  privacy defaults, overlays, extensions, packaging, and release checks.
- Synchronized the about-page version, extension manifests, and package-manager
  metadata with the authoritative 0.2.3 release version.

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

## Roadmap archive — 2026-08-10 — ROADMAP.md

<details>
<summary>Original roadmap snapshot</summary>

```markdown
# Roadmap

**Version**: v0.2 draft &middot; **Updated**: 2026-05-17 &middot; **Supersedes**: v0.1 (2025-04-23)

Forward-looking plan for [Vigil Browser](README.md) &mdash; a lean, privacy-respecting Chromium fork built on
[ungoogled-chromium-windows](https://github.com/ungoogled-software/ungoogled-chromium-windows) with a
Brave-style `chromium_src/` overlay system, a dark new-tab page, and uBlock Origin pre-installed.

This roadmap is dense by design. Every claim about a competitor or upstream is footnoted to a URL in the
[Appendix](#appendix-sources). Items with no source are internal observations from this repo's tree.

---

## Charter & non-goals

**Charter.** Vigil ships the privacy-and-defaults browser that an IT admin would build for themselves
&mdash; preconfigured for a sysadmin/clinic/power-user audience, with no telemetry, no rewards, no crypto,
no in-browser LLM, no in-browser VPN service. The reference is "Brave Origin, but free" &mdash; Brave's own
$60 one-time paid bloat-removal tier confirms the audience exists.[^pg-origin][^pg-origin-discuss]

**Non-goals.** These are off-table by design (see [Rejected](#rejected--explicit-non-goals) for full reasoning):
crypto wallets, Web3 name resolution, BAT-style sponsored ads, integrated LLM chatbots,
integrated paid VPN service, integrated mail/calendar/feeds, gamer/RGB features, novelty
tab paradigms (Arc), referral-link rewriting,[^pg-brave] and telemetry-by-default.

**Audience signal.** The maintainer's sibling projects &mdash; **BetterNext** (a NextDNS companion)
and **VoyanceFirewall** (a clinic/enterprise Windows lock-down tool) &mdash; point at the same user:
the person who installs the browser on someone else's machine and wants the result to stay clean.
Wherever the roadmap mentions clinic/kiosk/admin features, that's the alignment.

---

## Status snapshot (Phase 0 audit)

What ships in `master` today:

- v0.1.0 &middot; Chromium 145.0.7632.159[^cl] &middot; Windows-only build pipeline.
- Brave-style `chromium_src/` overlay system targeting `chrome://settings`, `chrome://flags`, `chrome://history`,
  `chrome://bookmarks`, `chrome://downloads`, `chrome://extensions`, and the security-interstitial CSS,
  with a single dark "IT-admin" Vigil theme.
- `initial_preferences` JSON sets first-run defaults: bookmark bar on, Safe Browsing off, DNT on,
  autofill off, translate off, network prediction off, default search = Google with `suggest_url`.
- `setup_extensions.py` fetches the latest **uBlock Origin** Chromium build from
  `gorhill/uBlock`'s GitHub Releases and stages it under `Extensions/cjpalhdlnbpafiamejdnhcphjbkeiagm/<v>/`
  plus a `default_extensions/<id>.json` external-extensions pointer.
- Patches restore the **Chrome Web Store** and **Google search engine** (otherwise stripped by ungoogled).
- Custom dark new-tab HTML (`ntp/newtab.html`) with clock, search, configurable shortcuts, settings panel.
- Generated Vigil "shield + eye" icon set via Pillow (`branding/generate_icons.py`); branding text/icons
  applied from `branding.json` at build time via `apply_overlays.py`.
- CI: hand-chained 12-stage build for x64, 16-stage for x86, additional chain for arm64, all dodging the
  GitHub Actions 6-hour single-job limit.

What's stubbed, broken, or missing on inspection (drives the [Now](#now) tier):

- The custom NTP is *copied to* `chrome/browser/resources/new_tab_page_custom/` and `build_outputs/ntp/`,
  but **nothing rewrites `chrome://newtab` to serve it**, so the dark NTP in `ntp/newtab.html` likely never
  loads as the default new tab. See [`apply_overlays.py:47-68`](apply_overlays.py#L47-L68) &amp;
  [`package.py:106-112`](package.py#L106-L112).
- `default_search_provider_data` ships **Google with `suggest_url`** &mdash; contradicts the
  "privacy-focused defaults" line in the README, and is exactly the issue the audience left Chrome over.
- **Safe Browsing disabled** with no offline replacement; users lose phishing protection.
- **No code signing** &rArr; SmartScreen Defender warning on every install, hurting trust badly.
- **No auto-updater** &mdash; users must manually grab releases.
- **`CHANGELOG.md` is malformed** (literal `%Y->-` and merge-commit text on the version line).
- **No test suite, no `CONTRIBUTING.md`, no `ARCHITECTURE.md`** &mdash; bus-factor of one.
- The 28-stage CI chain is a known time-bomb: any single failed step requires manual restart.

---

## Themes

| ID | Theme | Posture |
|---|---|---|
| T1 | **Privacy hardening (curated, not novelty)** | Adopt patches that work; reject anything that breaks parity-fingerprinting |
| T2 | **Anti-bloat &amp; audit-defaults** | Vigil's wedge: ship Brave Origin's promise free |
| T3 | **IT-admin / clinic readiness** | ADMX, kiosk, policy-managed defaults, MSI installer |
| T4 | **Build &amp; distribution pipeline maturity** | Code-signed, attested, auto-updated, multi-channel |
| T5 | **First-run &amp; sensible defaults** | The defaults *are* the product |
| T6 | **Extension ecosystem (MV2 long-tail)** | Preserve Manifest V2 against upstream removal |
| T7 | **UX polish &mdash; parity wins, no novelty tax** | Verticals, workspaces, split, reader; *not* Arc-style invention |
| T8 | **Platform coverage** | Windows-first; Linux earned; macOS later |
| T9 | **Sibling-project integration** | BetterNext &amp; VoyanceFirewall as native panels, not extensions |
| T10 | **Project health** | Docs, tests, contributing, governance |

---

## Now &mdash; v0.2.0 (~6 weeks)

Things that are wrong or missing today and are cheap to fix. Each lands with a unit-test or smoke-test where applicable.

### Defaults &amp; first-run [T2, T5]

### Project health [T10]

---

## Next &mdash; v0.3 / v0.4 (one quarter)

### Manifest V2 long-tail [T6]

### Privacy hardening (curated) [T1]

### IT-admin readiness [T3]

### UX polish &mdash; parity, not novelty [T7]

### Distribution &amp; updates [T4]

---

## Rejected &mdash; explicit non-goals

Each line is the contradiction between a competitor feature and Vigil's philosophy. If a future
maintainer wants to revisit, they need to argue against the source linked here.

- **Crypto wallet, BAT-style sponsored ads, Web3 name resolution (`.brave` / `.eth` / `.bit`).**
  Brave's full implementation;[^brave-wallet][^brave-rewards][^brave-tld] Mises is the Web3
  fork.[^mises][^mises-core] Audience mismatch + recurring user complaints
  about the surface.[^brave-issue-disablerewards] Vigil's wedge is being the un-crypto privacy
  browser.
- **Integrated LLM chatbot ("Leo AI" equivalent).** Brave Leo,[^brave-leo] Edge Copilot,[^edge-copilot]
  Sidekick,[^sidekick] Dia (post-Arc).[^arc-dead] Each adds a CVE class (e.g. prompt injection
  in Leo[^brave-issue-leo-injection]), telemetry, and a maintenance burden Vigil cannot afford.
  Users who want this can install a Chrome extension.
- **Integrated paid VPN service.** Brave Firewall+VPN at $9.99/mo[^brave-vpn] is squarely a SaaS
  product. Vigil ships *integration* with already-deployed VPNs (Mullvad, Tailscale, ProtonVPN
  via the system stack), not its own.
- **Brave Talk / integrated video conferencing.** Jitsi exists.[^brave-features] Out of scope.
- **Integrated mail / calendar / RSS reader (Vivaldi pattern).**[^vivaldi-mail] Floorp couldn't
  sustain a feed reader; the maintenance cost is 2&times; the rest of the project.
- **Razer Chroma / RGB lighting / gamer features (Opera GX).**[^opera-gx] Audience mismatch.
- **Referral-link rewriting / install-source affiliate codes.**[^pg-brave] Vigil's
  install must be telemetry-free.
- **Telemetry on by default (Edge / Chrome behavior).** Audited via the [Brave deviations
  list][^brave-deviations] as the floor.
- **Novelty tab paradigms (Arc Spaces as a UI primitive).** Arc died.[^arc-dead] Vigil's
  vertical tabs / workspaces / split view ship as *features* on top of the standard chrome,
  not as a replacement chrome.
- **Closed-source UI layer (Vivaldi pattern).**[^vivaldi-closed] Vigil is MIT/BSD from the
  installer to the icon-PNG renderer in `branding/generate_icons.py`.
- **Web Environment Integrity / Privacy Sandbox Topics &amp; Protected Audience APIs.** Topics /
  Protected Audience / Attribution Reporting retired Oct 2025;[^psbx] disable in
  `initial_preferences` regardless of upstream state.
- **Backwards compatibility with Windows 7/8.** Supermium covers that audience.[^supermium]
  Vigil targets Win 10 22H2 minimum.

---

## Risk &amp; dependency map

| Risk | Trigger | Mitigation |
|---|---|---|
| **Upstream Chromium ships a patch that breaks an overlay** | Every 4-6 weeks (Chromium stable cadence) | `chromium_src/` is per-file replacement &mdash; the build *fails to compile* rather than silently misbehaves,[^brave-patching] which is detected by `N14` smoke test |
| **Manifest V2 enforcement tightens further** | Possible Chromium 150-155 window | `X1` (carry MV2 patch); fallback `L4` (adblock-rust at network layer means uBO is not the only line of defense) |
| **uBO MV3-only release (uBO Lite) becomes the only release** | gorhill/uBlock cadence | `L4`; documented user-facing notice |
| **SignPath OSS program declines Vigil** | Possible &mdash; clinic/political concerns | Fallback to Azure Trusted Signing at $9.99/mo[^azure-signing] &mdash; budget &lt;$120/yr |
| **GitHub Actions 6h job limit changes** | Unlikely but historical precedent | `N7` matrix means each stage is &lt;5h; reusable workflow means a runner switch is a one-line change |
| **GitHub Releases hosting limits hit** | At ~50 releases &times; 3 arch &times; 200MB | Add a CDN mirror (Cloudflare R2 free tier covers it); document |
| **Solo maintainer bus-factor** | Always | `N13` (docs); `N14` (tests); accept the risk &mdash; this is OSS |
| **Brave Origin captures the no-bloat audience first** | They have momentum[^pg-origin] | Stay free + open-source + on winget; Brave's $60 is the moat we beat |
| **Arc-style "browser death" cycle** | Industry, not technical | Refuse novelty (Rejected list); never depend on a service we don't host |

---

## Release rhythm

- **Cadence.** Track ungoogled-chromium-windows releases (currently every ~2-3 weeks within a
  major)[^ucw-releases]. Vigil version = `<chromium>-<ucw>-vigil.<n>`. Drop `0.x` prefix when
  v1.0 ships (target: after `N1-N15` + `X1` + `X10` + `X20` all land &mdash; the smallest set that
  defines the product).
- **Channels.** Stable (default) + Canary (`X22`). No "Beta" channel until a third contributor
  exists.
- **Source of truth.** GitHub Releases. winget &amp; scoop &amp; chocolatey pull from there. No
  third-party mirrors authoritatively distribute Vigil installers.

---

## Open questions for the maintainer

1. **Default search engine** (`N1`) &mdash; DuckDuckGo, Brave Search, Startpage, or Kagi as the
   first-run pick?
2. **DRM (Widevine)** &mdash; ship enabled (clinic training-video reality[^helium-drm]) or off
   like Helium?
3. **Telemetry posture document** &mdash; do uBO update pings to GitHub Releases count as
   telemetry that needs an opt-out?
4. **Brave Origin response** &mdash; do we publish a comparison table on the README?
5. **Sibling-project boundary** &mdash; does BetterNext become a Vigil-only extension shipped in
   the installer (`Y1`), stay a separate browser extension, or ship as both?

These are the v0.2 design-review prompts, not yet decisions.

---

## Appendix: Sources

The following list is the union of citations across this roadmap. Sources are grouped by
research direction. Every roadmap claim above maps to one of these URLs.

### Upstream &amp; competitor projects

[^cl]: Internal: see [`CHANGELOG.md`](CHANGELOG.md) (note: malformed; `N11`).
[^uc-issues]: ungoogled-chromium open issues &mdash; <https://github.com/ungoogled-software/ungoogled-chromium/issues>
[^ucw-releases]: ungoogled-chromium-windows releases &mdash; <https://github.com/ungoogled-software/ungoogled-chromium-windows/releases>
[^brave-patching]: Brave wiki: Patching Chromium / chromium_src overlays &mdash; <https://github.com/brave/brave-browser/wiki/Patching-Chromium>
[^brave-deviations]: Brave wiki: Deviations from Chromium &mdash; <https://github.com/brave/brave-browser/wiki/Deviations-from-Chromium-(features-we-disable-or-remove)>
[^brave-sync]: Brave Sync v2 docs &mdash; <https://github.com/brave/brave-browser/wiki/Brave-Sync-v2>
[^brave-go-sync]: Brave go-sync server &mdash; <https://github.com/brave/go-sync>
[^brave-vpn]: Brave Firewall + VPN &mdash; <https://brave.com/firewall-vpn/>
[^brave-wallet]: Brave Wallet &mdash; <https://brave.com/wallet/>
[^brave-tld]: Brave `.brave` TLD &mdash; <https://brave.com/blog/brave-tld/>
[^brave-rewards]: Brave Rewards &mdash; <https://brave.com/brave-rewards/>
[^brave-features]: Brave Privacy Features (incl. Brave Talk) &mdash; <https://brave.com/privacy-features/>
[^brave-leo]: Brave Leo AI &mdash; <https://brave.com/leo/>
[^brave-tor]: Brave: What is a Private Window with Tor &mdash; <https://support.brave.app/hc/en-us/articles/360018121491>
[^brave-latest]: Brave latest release notes (2026) &mdash; <https://brave.com/latest/>
[^brave-speedreader]: Brave SpeedReader blog &mdash; <https://brave.com/blog/speed-reader/>
[^brave-repro]: Brave reproducible-builds issue #5830 &mdash; <https://github.com/brave/brave-browser/issues/5830>
[^brave-issue-disablerewards]: Brave issue #43030 (Disable crypto by default) &mdash; <https://github.com/brave/brave-browser/issues/43030>
[^brave-issue-leo-injection]: Brave issue #55576 (Leo prompt injection) &mdash; <https://github.com/brave/brave-browser/issues>
[^adblock-rust]: brave/adblock-rust &mdash; <https://github.com/brave/adblock-rust>
[^adblock-rust-mem]: Brave adblock memory-reduction post &mdash; <https://brave.com/privacy-updates/36-adblock-memory-reduction/>
[^cromite]: Cromite repo &mdash; <https://github.com/uazo/cromite>
[^cromite-features]: Cromite FEATURES.md &mdash; <https://github.com/uazo/cromite/blob/master/docs/FEATURES.md>
[^iridium-diff]: Iridium differences-from-Chromium &mdash; <https://github.com/iridium-browser/tracker/wiki/Differences-between-Iridium-and-Chromium>
[^iridium-wiki]: Iridium customizations (DeepWiki) &mdash; <https://deepwiki.com/iridium-browser/iridium-browser-windows/6-iridium-customizations>
[^thorium-mv2]: Thorium MV2 retention &mdash; <https://github.com/Alex313031/thorium/releases>
[^supermium]: Supermium repo &mdash; <https://github.com/win32ss/supermium>
[^helium-drm]: Helium DRM caveat write-up &mdash; <https://browsers.to/helium>
[^zen-workspaces]: Zen Workspaces manual &mdash; <https://docs.zen-browser.app/user-manual/workspaces>
[^zen-split]: Zen Split-view manual &mdash; <https://docs.zen-browser.app/user-manual/split-view>
[^zen-features]: Zen Browser feature page &mdash; <https://zen-browser.app/>
[^floorp-cmd]: Floorp 12.14.0 command palette &mdash; <https://github.com/Floorp-Projects/Floorp/releases>
[^vivaldi-features]: Vivaldi feature surface &mdash; <https://vivaldi.com/features/>
[^vivaldi-stacks]: Vivaldi tab stacks &mdash; <https://help.vivaldi.com/desktop/tabs/tab-stacks/>
[^vivaldi-mail]: Vivaldi mail/calendar/feed bundle announcement &mdash; <https://vivaldi.com/blog/vivaldi-mail-calendar-feed-reader-are-here/>
[^vivaldi-closed]: Vivaldi closed-source UI explainer &mdash; <https://vivaldi.com/blog/technology/why-isnt-vivaldi-browser-open-source/>
[^opera-gx]: Opera GX features &mdash; <https://www.opera.com/gx/features>
[^arc-spaces]: Arc Spaces docs &mdash; <https://resources.arc.net/hc/en-us/articles/19228064149143>
[^arc-dead]: Arc browser discontinuation, ghacks &mdash; <https://www.ghacks.net/2025/05/27/arc-browser-has-been-discontinued-but-the-companys-building-a-new-browser-dia/>
[^mises]: Mises browser &mdash; <https://www.mises.site/>
[^mises-core]: Mises browser core &mdash; <https://github.com/mises-id/mises-browser-core>
[^sidekick]: Sidekick browser review &mdash; <https://browserprompt.com/tool-specific/sidekick-browser-review>

### Privacy / community signal

[^pg-browsers]: PrivacyGuides desktop browsers &mdash; <https://www.privacyguides.org/en/desktop-browsers/>
[^pg-brave]: PrivacyGuides Brave caveats &mdash; <https://www.privacyguides.org/en/desktop-browsers/#brave>
[^pg-origin]: PrivacyGuides news: Brave Launches Paid Bloat-Free Brave Origin &mdash; <https://www.privacyguides.org/news/2026/04/21/brave-launches-paid-bloat-free-brave-origin/>
[^pg-origin-discuss]: PrivacyGuides forum on Brave Origin &mdash; <https://discuss.privacyguides.net/t/brave-launches-paid-bloat-free-brave-origin/37300>
[^pg-search]: PrivacyGuides search engines &mdash; <https://www.privacyguides.org/en/search-engines/>
[^pg-dns]: PrivacyGuides DNS providers &mdash; <https://www.privacyguides.org/en/dns/>
[^nextdns-ext1]: NextDNS extension (community) &mdash; <https://github.com/JackStuart/NextDNS-Extension>
[^nextdns-ext2]: NextDNS browser-plugin request &mdash; <https://help.nextdns.io/t/p8hfsaw/browser-plugin-extension-for-easy-allow-and-block>
[^nextdns-ext3]: NXEnhanced (NextDNS) &mdash; <https://github.com/hjk789/NXEnhanced>
[^ubo-deploy]: uBlock Origin deploy guide &mdash; <https://github.com/gorhill/uBlock/wiki/Deploying-uBlock-Origin>

### Standards, specs &amp; CVEs

[^mv2-timeline]: Chrome Manifest V2 deprecation timeline &mdash; <https://developer.chrome.com/docs/extensions/develop/migrate/mv2-deprecation-timeline>
[^mv2-blog]: Chromium MV2 phase-out blog &mdash; <https://blog.chromium.org/2024/05/manifest-v2-phase-out-begins.html>
[^https-default]: Google security blog: HTTPS by default &mdash; <https://security.googleblog.com/2025/10/https-by-default.html>
[^https-flag]: chrome://flags HTTPS-Only Mode (via roundup) &mdash; <https://techpp.com/2026/04/07/best-chrome-flags/>
[^ech-status]: Chrome ECH chromestatus &mdash; <https://chromestatus.com/feature/6196703843581952>
[^psbx]: Privacy Sandbox status &mdash; <https://privacysandbox.google.com/overview/status>
[^psbx-news]: Google retires Topics/PAAPI (AdExchanger, Oct 2025) &mdash; <https://www.adexchanger.com/privacy/google-pulls-the-plug-on-topics-paapi-and-other-major-privacy-sandbox-apis-as-the-cma-says-cheerio/>
[^permpolicy]: Permissions-Policy on developer.chrome.com &mdash; <https://developer.chrome.com/docs/privacy-security/permissions-policy>
[^cve-edge-webusb]: CVE-2026-5276 Edge WebUSB &mdash; <https://windowsnews.ai/article/cve-2026-5276-microsoft-edge-webusb-vulnerability-requires-immediate-patching.409595>
[^cve-fedcm]: CVE-2026-4680 Chrome FedCM &mdash; <https://windowsnews.ai/article/chrome-fedcm-vulnerability-cve-2026-4680-critical-use-after-free-flaw-patched-in-version-14607680165.408068>
[^tabbed-pwa]: Tabbed application mode docs &mdash; <https://developer.chrome.com/docs/capabilities/tabbed-application-mode>
[^crx3]: CRX3 npm tool &mdash; <https://www.npmjs.com/package/crx3>

### Build, distribution, signing

[^chromium-detbuild]: Chromium deterministic builds doc &mdash; <https://chromium.googlesource.com/chromium/src/+/HEAD/docs/deterministic_builds.md>
[^slsa-attest]: actions/attest-build-provenance &mdash; <https://github.com/actions/attest-build-provenance>
[^slsa-attest-docs]: GitHub docs: artifact attestations &mdash; <https://docs.github.com/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds>
[^signpath]: SignPath Foundation &mdash; <https://signpath.org/>
[^signpath-oss]: SignPath OSS solutions &mdash; <https://signpath.io/solutions/open-source-community>
[^azure-signing]: Azure Trusted Signing pricing &mdash; <https://azure.microsoft.com/en-us/pricing/details/trusted-signing/>
[^azure-signing-faq]: Azure Artifact Signing FAQ &mdash; <https://learn.microsoft.com/en-us/azure/artifact-signing/faq>
[^velopack]: Velopack &mdash; <https://velopack.io/>
[^velopack-vs-squirrel]: Velopack docs: migrating from Squirrel &mdash; <https://docs.velopack.io/migrating/squirrel>
[^omaha-4]: Omaha 4 tutorial &mdash; <https://omaha-consulting.com/chromium-updater-omaha-4-tutorial>
[^omaha-protocol]: Omaha 4 protocol &mdash; <https://chromium.googlesource.com/chromium/src/+/f4b7e04ec3114a76e645dc49ff09adb90643821b/docs/updater/protocol_4.md>
[^winget-repo]: microsoft/winget-pkgs &mdash; <https://github.com/microsoft/winget-pkgs>
[^winget-pkgs]: winget repository guide &mdash; <https://learn.microsoft.com/en-us/windows/package-manager/package/repository>
[^scoop-manifest]: Scoop app-manifests wiki &mdash; <https://github.com/ScoopInstaller/Scoop/wiki/App-Manifests>
[^gha-arm64-private]: GitHub Actions ARM64 GA in private repos (Jan 2026) &mdash; <https://github.blog/changelog/2026-01-29-arm64-standard-runners-are-now-available-in-private-repositories/>

### IT-admin / enterprise

[^chrome-enterprise]: Chrome Enterprise policy list &mdash; <https://chromeenterprise.google/policies/>
[^edge-configure]: Microsoft Edge configure-for-enterprise docs &mdash; <https://learn.microsoft.com/en-us/deployedge/configure-microsoft-edge>
[^edge-intune-mam]: Edge Intune MAM overview &mdash; <https://learn.microsoft.com/en-us/intune/intune-service/apps/mamedge-overview>
[^edge-workspaces]: Edge Workspaces docs &mdash; <https://learn.microsoft.com/en-us/deployedge/microsoft-edge-workspaces>
[^edge-vt]: Edge vertical tabs &mdash; <https://www.microsoft.com/en-us/edge/features/vertical-tabs>
[^edge-sleep]: Edge sleeping tabs &mdash; <https://www.microsoft.com/en-us/edge/features/sleeping-tabs>
[^edge-copilot]: Edge Copilot disable guide &mdash; <https://www.datastudios.org/post/how-to-disable-microsoft-copilot-in-windows-edge-microsoft-365-apps-and-organizational-environmen>
[^chromium-kiosk]: Chromium kiosk public-session docs &mdash; <https://chromium.googlesource.com/chromium/src/+/main/docs/enterprise/kiosk_public_session.md>
[^chromium-extpolicy]: Chromium extension policy admin doc &mdash; <https://www.chromium.org/administrators/configuring-policy-for-extensions/>

### DNS providers list reference

[^adguard-dns-providers]: AdGuard DNS providers reference &mdash; <https://adguard-dns.io/kb/general/dns-providers/>

### Tooling references

[^wix]: WiX Toolset (MS-RL/MIT) &mdash; <https://wixtoolset.org/>
[^uc-macos]: ungoogled-chromium-macos &mdash; <https://github.com/ungoogled-software/ungoogled-chromium-macos>
[^uc-android]: ungoogled-chromium-android &mdash; <https://github.com/ungoogled-software/ungoogled-chromium-android>
[^playwright]: Playwright (Chromium-channel automation) &mdash; <https://playwright.dev/docs/browsers#google-chrome--microsoft-edge>
```

</details>
