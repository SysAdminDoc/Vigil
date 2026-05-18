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

- **`N1` &middot; Fix the search-engine contradiction.** Swap `default_search_provider_data` from Google to a
  privacy-respecting default. Recommended primary: DuckDuckGo (HTML form &amp; suggest endpoint); ship Brave Search,
  Startpage, Kagi, Mojeek and Google as one-click alternates. Rationale: matches the README line and removes
  the implicit handshake that the current `suggest_url` performs on every keystroke. (See
  [`initial_preferences:19-30`](initial_preferences#L19-L30).) Source: PrivacyGuides DNS/Search list.[^pg-search]
- **`N2` &middot; HTTPS-First (Balanced) ON by default.** Set `HttpsOnlyMode` &amp; the
  `chrome://flags/#https-only-mode-setting` flag so Vigil ships
  HTTPS-First *now*, ahead of Chrome 154's October 2026 default-on plan.[^https-default][^https-flag]
  Marketing copy writes itself.
- **`N3` &middot; Wire the custom NTP correctly.** Today `ntp/newtab.html` is installed but not registered
  as `chrome://newtab`. Either (a) override the NTP via a small `chromium_src/` patch to
  `chrome/browser/ui/views/new_tab_page/`, or (b) ship it as a bundled extension that claims
  `chrome_url_overrides.newtab` (the Brave/Cromite approach). Option (b) is the smaller blast radius and is
  the recommended first path.
- **`N4` &middot; Restore replacement for disabled Safe Browsing.** Either (a) ship a local hosts-file
  blocklist via `--host-rules-file` baked into the `initial_preferences` distribution block, or
  (b) keep Safe Browsing *enabled* but disable the upload-side telemetry only. Current "off entirely"
  position is a usability regression with no privacy benefit because uBO already covers most of it.
  Source: PrivacyGuides browser criteria.[^pg-browsers]
- **`N5` &middot; Permissions-Policy default-deny for high-risk surfaces.** Set Permissions-Policy at the
  enterprise-policy level for `usb=()`, `serial=()`, `hid=()`, `bluetooth=()`, `idle-detection=()`,
  `local-fonts=()`, `payment=()`. CVE-2026-5276 (Edge WebUSB)[^cve-edge-webusb] and CVE-2026-4680
  (Chrome FedCM UAF)[^cve-fedcm] make this hardening, not paranoia. Override via a
  `vigil://device-access` settings page in a later release. Reference: Permissions-Policy spec.[^permpolicy]
- **`N6` &middot; Drop the Privacy Sandbox retired-surface flags.** Topics, Protected Audience API, and
  Attribution Reporting were retired by Google in October 2025[^psbx][^psbx-news]; even if upstream
  Chromium still exposes the flags, Vigil should disable them in `initial_preferences` and remove their
  entries from the Vigil settings overlay.

### Build &amp; release pipeline [T4]

- **`N7` &middot; CI refactor &mdash; reusable workflow + matrix.** The current 28-stage hand-chained
  workflow ([`.github/workflows/main.yml`](.github/workflows/main.yml)) is brittle. Split into one
  reusable workflow accepting `(arch, stage)`, called by a matrix `(arch &times; stage)` with
  `needs:` only on the prior stage of the *same* arch. Move arm64 onto the GitHub-hosted ARM64 runner
  (GA in private repos as of Jan 2026[^gha-arm64-private]) to halve arm build time.
- **`N8` &middot; Code-sign Windows binaries via SignPath Foundation.** SignPath has a free OSS program
  that issues an HSM-backed cert to "SignPath Foundation" and signs releases via approved GitHub
  Actions.[^signpath][^signpath-oss] Fallback: Azure Trusted (Artifact) Signing, $9.99/mo for 5k sigs.[^azure-signing][^azure-signing-faq]
  This single change removes the SmartScreen warning that is currently the #1 trust issue.
- **`N9` &middot; SLSA build provenance attestations.** Add `actions/attest-build-provenance` to every
  artifact-emitting job. Free for public repos, single step.[^slsa-attest][^slsa-attest-docs]
- **`N10` &middot; Reproducible-build groundwork.** Set `enable_resource_allowlist_generation=false` only
  in instrumented PGO builds (per Chromium's own deterministic-build doc),[^chromium-detbuild] document
  the env-var diff between build hosts in a new `docs/build-environment.md`. Brave's reproducible-builds
  issue is still open after 7 years[^brave-repro] &mdash; partial determinism is the realistic target.
- **`N11` &middot; Fix `CHANGELOG.md`.** Replace the literal `%Y->-` placeholder; adopt the
  Keep-a-Changelog format and write a tag-driven generator in `devutils/changelog.py`.
- **`N12` &middot; Pin and document toolchain versions.** `flags.windows.gn` should record clang,
  rustc, ninja, gn revisions per release; expose at `chrome://version` via overlay.

### Project health [T10]

- **`N13` &middot; Write `CONTRIBUTING.md` and `ARCHITECTURE.md`.** ARCHITECTURE = how the
  `chromium_src/` overlay, patches, and `initial_preferences` interact (Brave's docs are an excellent
  model[^brave-patching]); CONTRIBUTING = how to add an overlay, how to add a patch, how to bump
  Chromium. Both unblock external PRs.
- **`N14` &middot; Add a smoke test in CI.** Boot the built installer in a Windows VM, navigate to a
  test page, confirm: bundled uBO loaded, `initial_preferences` applied, new-tab page = Vigil NTP,
  search-engine default = `N1` choice. Use [Playwright][^playwright] or Selenium with the already-built
  `chromedriver` output.
- **`N15` &middot; Publish a winget manifest.** `Vigil.Browser` in `microsoft/winget-pkgs`, auto-PR
  on every release tag via a small action (the upstream project ships
  [`.github/actions/winget/`](.github/actions/winget/) infra to crib from).[^winget-repo][^winget-pkgs]

---

## Next &mdash; v0.3 / v0.4 (one quarter)

### Manifest V2 long-tail [T6]

- **`X1` &middot; Carry an MV2-retention patch set against each Chromium bump.** Chrome 138 was the last
  MV2-supporting stable; 139 removed it including the `ExtensionManifestV2Availability`
  policy.[^mv2-timeline][^mv2-blog] Brave, Thorium, Cromite, and Supermium all carry MV2-keep-alive
  patches.[^thorium-mv2][^supermium] This is *the* feature that justifies a Chromium fork to a sysadmin
  audience in 2026. Publish a written "MV2 Policy" doc as part of v0.3.
- **`X2` &middot; AMO &rarr; CRX bridge (research, not commit).** Investigate a Vigil-side converter that
  ingests a Firefox `.xpi` and re-packs as CRX3 via `crx3` npm tool, then surfaces in a Vigil-branded
  installer page. CRX3 requires Web-Store-signed keys for off-store install since Chrome 75[^crx3] &mdash;
  the practical implementation is a developer-mode allowlist plus the conversion tool. Mark `RESEARCH`
  in v0.3, ship in v0.5 if feasible.
- **`X3` &middot; Force-install `Vigil-recommended` extension set.** Use the existing external-extensions
  JSON mechanism plus a Vigil-only `ExtensionInstallForcelist` template (defaults to just uBO,
  documented). Reference: uBO deploy guide,[^ubo-deploy] Chromium extension-policy admin doc.[^chromium-extpolicy]
- **`X4` &middot; Sideload-without-developer-mode-warning toggle.** Patch the warning banner so signed
  CRX from an admin-trusted publisher key list installs cleanly. (Already in roadmap v0.1; keep.)

### Privacy hardening (curated) [T1]

- **`X5` &middot; Backport Iridium's WebRTC patches.** Per-connection identity (no 30-day reuse),
  fresh ECDHE keypair per connection, RSA self-signed-cert keysize 2048. Small, network-layer,
  no Web-API spoofing &mdash; the safe kind.[^iridium-diff][^iridium-wiki]
- **`X6` &middot; DoH first-run picker (sticky, no fallback).** Pre-populate Quad9, NextDNS, Cloudflare,
  Mullvad, AdGuard, ControlD as named entries; offer "custom" with hostname validation.
  Reference: PrivacyGuides DNS list,[^pg-dns] AdGuard DNS provider list.[^adguard-dns-providers]
  Pair with `BetterNext` integration in `Y1`.
- **`X7` &middot; Strip Client Hints (UA-CH).** UA-CH was retained from the Privacy Sandbox cull,[^psbx]
  but is a fingerprinting vector. Default `accept_ch_browser_policy=disabled` or equivalent;
  offer per-site override via a flag.
- **`X8` &middot; Anti-fingerprinting "Strict" toggle (off by default).** A curated, opinionated subset
  of Cromite's protections (canvas, audio, font-list clamp, `navigator.hardwareConcurrency`
  bucketed to {2,4,8}, screen.avail* hidden)[^cromite-features] &mdash; *not* full Brave farbling.
  Documented breakage list. Off by default per the Mullvad caveat that customization defeats
  fingerprint uniformity.[^pg-browsers]
- **`X9` &middot; Encrypted Client Hello (ECH) audit.** ECH is on by default upstream;[^ech-status]
  Vigil should never expose a "disable ECH" toggle (some corporate filters demand it). Document.

### IT-admin readiness [T3]

- **`X10` &middot; Ship a Vigil ADMX template (`vigil.admx` + `vigil.adml`).** A documented subset of
  Chrome's ~400 enterprise policies:[^chrome-enterprise] `URLBlocklist`, `URLAllowlist`,
  `ExtensionInstallForcelist`, `ExtensionInstallBlocklist`, `HomepageLocation`, `NewTabPageLocation`,
  `IncognitoModeAvailability`, `ProxyMode`, `ManagedBookmarks`, `DefaultSearchProviderEnabled`,
  `AlwaysOpenPdfExternally`, `AutofillAddressEnabled`, `ScreenCaptureAllowed`,
  `ClipboardAllowedForUrls`, `DownloadDirectory`, `ManagedConfigurationPerOrigin`. Mirror Microsoft Edge's
  ADMX pattern.[^edge-configure] This is the single biggest IT-admin adoption blocker.
- **`X11` &middot; Ship an MSI installer alongside the EXE.** Required for Group Policy / Intune
  Win32App deployment.[^edge-intune-mam] Use the [WiX Toolset][^wix] to wrap the existing
  `mini_installer` outputs.
- **`X12` &middot; Vigil-Kiosk variant.** A separately-branded build that boots straight into a
  pinned URL, hides chrome, auto-restarts on crash, integrates with Windows Task Scheduler watchdog.
  Reference: Chromium kiosk-public-session doc.[^chromium-kiosk] Clinic alignment with
  VoyanceFirewall.
- **`X13` &middot; `chrome://policy` Vigil-themed override.** Currently the overlay set themes
  `flags`, `settings`, etc.; add `policy` &mdash; the page sysadmins check first.

### UX polish &mdash; parity, not novelty [T7]

- **`X14` &middot; Vertical tabs.** Edge ships,[^edge-vt] Zen built its identity on it,[^zen-workspaces]
  Brave just relit `#brave-scrollable-tab-strip` and ships a toolbar toggle.[^brave-latest]
  Chromium has the `#side-panel-pinned-2` family; expose a built-in toggle in Vigil's
  themed settings page.
- **`X15` &middot; Split view (2-pane).** Brave shipped 2026 split-view, Zen does 2&times;2.[^zen-split]
  Vigil ships 2-pane only; multi-pane deferred.
- **`X16` &middot; Tab hibernation (a.k.a. Sleeping Tabs).** Chromium has the discard primitive;
  Edge[^edge-sleep] exposes it. Surface in Vigil's settings overlay with per-domain exception list.
- **`X17` &middot; Reader Mode (proper).** Chromium ships a "Distill page" prototype; Brave's
  SpeedReader is MPL-2.0 and well-documented[^brave-speedreader] but heavy. Phase 1: expose the
  upstream distiller as a one-click toolbar button + Markdown export.
- **`X18` &middot; Command palette (Ctrl+Shift+P).** Floorp 12.14.0 shipped one;[^floorp-cmd]
  Vivaldi's "Quick Commands" is the model.[^vivaldi-features] Wraps existing chrome actions; no
  new commands needed.
- **`X19` &middot; NTP widgets ship `v2`.** Today: clock, search, shortcuts, settings. Add:
  weather (Open-Meteo, no API key), top-sites (existing Chromium MV API), bookmark folder,
  RSS quick-feed (3 items), notes (localStorage). All optional, all in the existing
  settings panel. Keep `<320 KB total`.

### Distribution &amp; updates [T4]

- **`X20` &middot; Auto-updater via Velopack.** Cross-platform Rust updater with delta packages,
  GitHub-Releases backend, staged rollouts (added 2026).[^velopack][^velopack-vs-squirrel] Avoid
  Omaha 4 &mdash; too heavy for a solo-maintained fork.[^omaha-4][^omaha-protocol]
- **`X21` &middot; Scoop + Chocolatey manifests.** Auto-publish on tag.[^scoop-manifest]
- **`X22` &middot; Two release channels.** `vigil-stable` follows upstream stable; `vigil-canary`
  follows upstream `beta`/`canary` once a week. Both via the same matrix workflow from `N7`.
- **`X23` &middot; Portable build (no installer).** Sentinel file `portable_data/` next to
  `chrome.exe` triggers `--user-data-dir=.\portable_data`; already a Supermium pattern.[^supermium]

---

## Later &mdash; v0.5+ (after v0.4 ships)

### Platform coverage [T8]

- **`L1` &middot; Linux build (AppImage + deb + rpm + Flatpak).** Use the same `chromium_src/`
  overlay set; package the `ungoogled-chromium` Linux scripts. Validate by mirroring
  Cromite's release matrix.[^cromite] Defer macOS until L1 is stable for two releases.
- **`L2` &middot; macOS build.** Inherit from upstream
  [`ungoogled-chromium-macos`][^uc-macos]; reuse Vigil overlays. Code-sign separately
  (Apple Developer ID, ~$99/yr).
- **`L3` &middot; ARM64 native runner for builds.** Move arm64 stages to the GA ARM64 GitHub-hosted
  runner.[^gha-arm64-private]

### Adblock at the engine layer [T1]

- **`L4` &middot; Migrate from bundled uBO to `adblock-rust` consumed as a crate.** Brave's
  network-layer engine; MPL-2.0; supports ABP + uBO syntax + cosmetic + scriptlet +
  resource-replacement; 2026 FlatBuffers refactor cut memory ~75% / ~45 MB per
  platform;[^adblock-rust][^adblock-rust-mem] Firefox 149 silently shipped it Mar 2026. Two-phase:
  consume as a bundled extension *first* (gasanache wrapper pattern), then absorb into the binary
  in v0.7+. Bundled uBO remains the default until parity is verified.

### Sibling-project integration [T9]

- **`Y1` &middot; "Network Filter Companion" panel.** Detects NextDNS / Pi-hole / AdGuard Home /
  Mullvad DNS in the active network stack and surfaces a live block-stats &amp; allow/deny side
  panel. This is the natural home for **BetterNext**'s feature surface, brought in-tree as a
  bundled extension or a `chrome://network-filter` overlay. Existing community NextDNS browser
  extensions are weak,[^nextdns-ext1][^nextdns-ext2][^nextdns-ext3] confirming the gap.
- **`Y2` &middot; VoyanceFirewall hand-off.** A "Locked-Down Profile" wizard (1-click) that
  loads a documented Vigil ADMX subset for clinic/kiosk and writes a sentinel for
  VoyanceFirewall to detect and supplement at the network layer.
- **`Y3` &middot; "Panic" hotkey.** Opera GX has it;[^opera-gx] clinic audience needs it
  (patient walks up to a kiosk). `Ctrl+Alt+Shift+P`: close all windows, clear session,
  return to lock screen.

### Power-user UX [T7]

- **`L5` &middot; Local Workspaces (no M365 lock-in).** Match Edge's Workspaces feature without
  requiring an Entra ID + OneDrive for Business license.[^edge-workspaces] Storage = a JSON file
  in the profile, with optional WebDAV/SMB share endpoint for shared-team usage.
- **`L6` &middot; Tab Stacks &amp; Tab Islands.** Vivaldi's three stacking styles;[^vivaldi-stacks]
  Opera's Tab Islands.[^opera-gx] Cheap UI win, all primitives already in Chromium.
- **`L7` &middot; Mouse gestures &amp; rocker gestures.** Floorp 12.x has them native, Vivaldi has
  them as Command Chains.[^vivaldi-features] Ship a small built-in implementation; reject the
  bundled-extension route.
- **`L8` &middot; CPU/RAM/Network throttle (Opera GX "GX Control" equivalent).** Per-tab caps
  for kiosk/clinic where the browser must not starve the host.[^opera-gx]

### Self-host &amp; resilience

- **`L9` &middot; Vigil Sync (BIP39 seed, AES, self-hostable).** Brave's `go-sync` server is
  AGPL/MPL[^brave-sync][^brave-go-sync] and uses 32-byte BIP39 seeds with AES-128-CTR + HMAC;
  fork it as `vigil-sync`, host nothing, document running it on a NAS / Synology / Raspberry Pi.
  Decision required: do we want to host *anything*. Default answer: no.
- **`L10` &middot; Offline filter updates.** Bundle a 24h-fresh EasyList + EasyPrivacy +
  uBO-cosmetics + PeterLowe in the installer so a freshly-installed Vigil works air-gapped
  for the first month. Auto-update afterwards.

### Tor &amp; advanced privacy

- **`L11` &middot; "Private window with Tor connectivity" (Brave parity).** Brave's onion-routed
  private mode &mdash; *not* Tor Browser parity, with the warning Brave ships.[^brave-tor]
  Decision required: maintenance cost of carrying Tor patches vs. value.

---

## Under Consideration &mdash; needs user-research or validation

- **`U1` &middot; Tampermonkey-compatible user-script loader, no extension.** Eliminates a
  popular sideload need.
- **`U2` &middot; Android build via upstream
  [`ungoogled-chromium-android`][^uc-android].** Real cost of carrying a mobile pipeline solo is unknown;
  Cromite proves it's possible but it's a second-class effort.[^cromite]
- **`U3` &middot; Per-site default-search override.** "On `accounting.example` always use DuckDuckGo;
  on `wikipedia.org` use Mojeek." Niche but matches the IT-admin audience.
- **`U4` &middot; "Glance" hover-preview tabs.** Zen feature;[^zen-features] users either love
  it or never touch it.
- **`U5` &middot; Reading-mode Markdown export.** Pairs with `X17`; trivial if reader-mode ships;
  decided in v0.5 once `X17` lands.
- **`U6` &middot; Boost-style per-site CSS overrides.** Arc's defining feature;[^arc-spaces]
  Arc is dead.[^arc-dead] Useful, niche, kinda spooky from a security standpoint &mdash; would
  need a separate "user styles" enable-toggle.
- **`U7` &middot; Aero-glass titlebar option for legacy Windows.** Supermium ships it.[^supermium]
  Vigil's audience overlaps; check installation telemetry (which we don't have, so &mdash; ask).
- **`U8` &middot; Built-in PWA installer + Tabbed PWA support.** Tabbed-PWA is OT only and
  Chrome-OS-prioritized;[^tabbed-pwa] Vigil could be the Windows-first first mover. Decision
  gate: clinic single-app deployments asking for it.
- **`U9` &middot; SponsorBlock / ClearURLs / I Still Don't Care About Cookies as opt-in
  default extensions.** Was in v0.1 roadmap; demote to UC until user signal &mdash; Vigil's
  default-extension set should stay one item long.
- **`U10` &middot; CRX-from-AMO converter.** See `X2`. Defer to v0.5+ once research is done.
- **`U11` &middot; "Spoof WebGPU info" patch.** Open ungoogled-chromium enhancement request
  (#3670, Feb 2026).[^uc-issues] Track upstream.
- **`U12` &middot; UDP SOCKS5 for QUIC.** Open ungoogled-chromium enhancement request (#3696,
  Mar 2026).[^uc-issues]
- **`U13` &middot; Per-profile avatars.** Open ungoogled-chromium enhancement request (#3747,
  Apr 2026).[^uc-issues]
- **`U14` &middot; Multi-column bookmark dropdown.** Open ungoogled-chromium enhancement request
  (#3781, May 2026).[^uc-issues]
- **`U15` &middot; Accessibility audit.** Verify the Vigil dark theme overlays pass WCAG AA
  contrast on all `chrome://` pages we override; add `prefers-contrast: more` overrides where
  they fail. No source &mdash; this is internal review of our own settings overlay
  [`chromium_src/chrome/browser/resources/settings/settings.html`](chromium_src/chrome/browser/resources/settings/settings.html).
- **`U16` &middot; Telemetry: explicit no-telemetry posture document.** Vigil has no telemetry today
  by virtue of inheritance from ungoogled-chromium. State it. Define what *would* count as telemetry
  (e.g. uBO update pings to GitHub Releases &mdash; we keep, document).
- **`U17` &middot; Internationalization.** Vigil currently inherits all of Chromium's locales.
  Our overlays of `settings.html`/`flags.html`/`history.html`/etc. only ship the English copy;
  audit whether `$i18n{}` placeholders are preserved through overlays.
- **`U18` &middot; First-run import wizard for Chrome / Edge / Brave.** Today
  `initial_preferences` *disables* import on first run (`import_bookmarks: false`,
  `import_history: false`, `import_search_engine: false` &mdash; see
  [`initial_preferences:11-17`](initial_preferences#L11-L17)). That is the right default for
  privacy, but it strands the migrating user. Add a *post*-first-run "Import from another
  browser" wizard in the Vigil-themed settings page, with a clear "what gets imported"
  list and per-category toggles. Reuses Chromium's `chrome://settings/importData`.
- **`U19` &middot; Per-tab network inspector and tracker log.** A human-readable side-panel
  log of blocked requests, source extension, and rule that fired &mdash; surfaced from uBO's
  logger API. Was in v0.1 roadmap; demote to UC pending user signal.
- **`U20` &middot; Site-specific profile launcher.** "This domain always opens in a clean
  session." Pairs with `L6` (tab stacks); decision in v0.5.

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
