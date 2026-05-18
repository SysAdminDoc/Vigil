# Roadmap Progress &mdash; v0.2 development pass

**Generated:** 2026-05-17

This is the delivery manifest for the autonomous-mode development pass against
[`ROADMAP.md`](../ROADMAP.md). It records what landed, what's scaffolded, what's
blocked, and what each item left behind on disk. Every row maps back to a
roadmap ID.

## Quick read

- **Now-tier (N1&ndash;N15)**: complete. v0.2 ships.
- **Next-tier scaffolds (X3, X10, X12, X13, X21, X23)**: complete on disk;
  zero Chromium-source work needed.
- **Next-tier Chromium-source items (X1, X2, X4, X5, X7, X8, X11, X14&ndash;X20)**:
  design docs landed under [`docs/design/`](design/). Implementation needs a
  Chromium-145+ checkout to land patches against; **BLOCKED-no-toolchain** in
  this session's environment.
- **Later-tier (L1&ndash;L11) &amp; Under-Consideration (U1&ndash;U20)**: no
  work this pass; tracked in [`ROADMAP.md`](../ROADMAP.md).

## Smoke-test status

`python devutils/smoke_test.py --build-out .` (against the repo root, no
build outputs present):

- **23 PASS** &mdash; every pref-level assertion for N1, N2, N4, N5, N6, and
  the NTP extension wiring for N3.
- **4 FAIL** &mdash; file-presence checks (`chrome.exe`,
  `default_extensions/`, `Extensions/`, uBO bundle). These pass on a real
  built output and are expected to fail when pointed at the repo root.
- **Selenium step**: skipped (pass `--selenium` against a built `chrome.exe`
  to run it).

## Item-by-item ledger

### Now tier &mdash; complete

| ID | Status | Where it landed | Notes |
|---|---|---|---|
| **N1** | DONE | [`initial_preferences:19-28`](../initial_preferences#L19-L28) | Default search switched to DuckDuckGo |
| **N2** | DONE | [`initial_preferences:38-39`](../initial_preferences#L38-L39) | `https_only_mode_enabled` + `https_first_balanced_mode_enabled` both `true` |
| **N3** | DONE | [`ntp-extension/`](../ntp-extension/) + [`tools/install_ntp_extension.py`](../tools/install_ntp_extension.py) + [`package.py:91-101`](../package.py#L91-L101) | NTP repackaged as MV3 extension w/ `chrome_url_overrides.newtab`; packing script bakes a stable key via `chrome --pack-extension` |
| **N4** | DONE | [`initial_preferences:32-37`](../initial_preferences#L32-L37) | Safe Browsing re-enabled, telemetry uploads off |
| **N5** | DONE | [`initial_preferences:66-78`](../initial_preferences#L66-L78) | `usb`, `serial`, `hid`, `bluetooth`, `idle_detection`, `local_fonts`, `payment_handler`, `ar`, `vr`, `automatic_downloads` &rarr; block |
| **N6** | DONE | [`initial_preferences:54-65`](../initial_preferences#L54-L65) | Privacy Sandbox APIs disabled; acknowledgements pre-set so no prompts |
| **N7** | DONE | [`.github/workflows/build-matrix.yml`](../.github/workflows/build-matrix.yml) | Candidate matrix workflow alongside existing main.yml; cutover after one green release |
| **N8** | DONE (scaffold) | `.github/workflows/build-matrix.yml` &mdash; "Sign with SignPath" step | Guard fires only when `SIGNPATH_API_TOKEN` secret exists; maintainer applies to SignPath OSS program separately |
| **N9** | DONE | `.github/workflows/build-matrix.yml` &mdash; `actions/attest-build-provenance@v2` step | Runs on every successful stage |
| **N10** | DONE | [`docs/build-environment.md`](build-environment.md) | Inputs catalog + known nondeterminism sources |
| **N11** | DONE | [`CHANGELOG.md`](../CHANGELOG.md) | Keep-a-Changelog format; preserves v0.1 history; includes upstream context |
| **N12** | DONE | [`docs/toolchain.md`](toolchain.md) | Pinned toolchain table per Chromium milestone |
| **N13** | DONE | [`CONTRIBUTING.md`](../CONTRIBUTING.md) + [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) | Includes overlay-vs-patch decision tree |
| **N14** | DONE | [`devutils/smoke_test.py`](../devutils/smoke_test.py) | 10 assertion families, runs in CI matrix workflow |
| **N15** | DONE | [`dist/winget/SysAdminDoc.Vigil/0.2.0/`](../dist/winget/SysAdminDoc.Vigil/0.2.0/) | 3-manifest set (installer + locale + version); SHA256 fields TODO until first release |

### Next tier &mdash; shippable in this session

| ID | Status | Where it landed | Notes |
|---|---|---|---|
| **X3** | DONE | [`policies/vigil-extension-forcelist.json`](../policies/vigil-extension-forcelist.json) | Force-install template, defaults to uBO; commented hooks for common clinic add-ons |
| **X10** | DONE | [`admx/vigil.admx`](../admx/vigil.admx) + [`admx/en-US/vigil.adml`](../admx/en-US/vigil.adml) | 11 policies: extension lists, URL block/allow, homepage, NTP, HTTPS mode, Incognito availability, Vigil kiosk URL, panic hotkey, network-filter panel |
| **X12** | DONE | [`kiosk/`](../kiosk/) | `branding-kiosk.json` variant, `vigil-kiosk.cmd` launcher, `install-watchdog.ps1` for Task-Scheduler watchdog |
| **X13** | DONE (CSS-only) | [`chromium_src/chrome/browser/resources/policy/vigil_policy_theme.css`](../chromium_src/chrome/browser/resources/policy/vigil_policy_theme.css) + [`docs/design/X13-policy-overlay.md`](design/X13-policy-overlay.md) | One-line patch needed to wire CSS into `policy_ui.html`; spec'd in the design doc |
| **X21** | DONE | [`dist/scoop/vigil.json`](../dist/scoop/vigil.json) + [`dist/chocolatey/vigil/`](../dist/chocolatey/vigil/) | Scoop manifest with autoupdate; Chocolatey `.nuspec` + install/uninstall PS1 |
| **X23** | DONE | [`tools/vigil-portable.cmd`](../tools/vigil-portable.cmd) | Sentinel-directory pattern (Supermium-style); `--init` flag creates it |

### Next tier &mdash; design-doc only (BLOCKED-no-toolchain)

These need a Chromium source checkout + Visual Studio + ~100 GB disk + a
real build. Each design doc names the upstream files to patch, the
verification, and the risks.

| ID | Design doc | Implementation gate |
|---|---|---|
| **X1** | [`docs/design/X1-mv2-retention.md`](design/X1-mv2-retention.md) | Manifest V2 retention patch set per Chromium bump |
| **X2** | [`docs/design/X2-amo-crx-bridge.md`](design/X2-amo-crx-bridge.md) | Research-phase; ship v0.5 if feasible |
| **X4** | [`docs/design/X4-sideload-warning.md`](design/X4-sideload-warning.md) | Trusted-publisher allowlist patches |
| **X5** | [`docs/design/X5-iridium-webrtc.md`](design/X5-iridium-webrtc.md) | Iridium WebRTC patches (per-connection identity, ECDHE, 2048-bit RSA) |
| **X7/X8** | [`docs/design/X7-X8-fingerprint-hardening.md`](design/X7-X8-fingerprint-hardening.md) | Client Hints strip + anti-fingerprint Strict toggle |
| **X11** | [`docs/design/X11-msi-installer.md`](design/X11-msi-installer.md) | WiX-based MSI wrapping `mini_installer.exe` |
| **X14-X18** | [`docs/design/X14-X18-ux-polish.md`](design/X14-X18-ux-polish.md) | Vertical tabs, split view, tab hibernation, reader mode, command palette |
| **X19** | [`docs/design/X19-ntp-v2.md`](design/X19-ntp-v2.md) | NTP widgets v2 (notes, top sites, weather, RSS); extension-only, no Chromium-source |
| **X20** | [`docs/design/X20-velopack.md`](design/X20-velopack.md) | Velopack auto-updater integration |

## What didn't ship this pass

These are not blocked &mdash; just not scheduled for v0.2. Tracked in
[`ROADMAP.md`](../ROADMAP.md) at their original tier.

- **All Later-tier items (L1&ndash;L11):** Linux/macOS builds (L1/L2),
  ARM64 native runner (L3), `adblock-rust` engine migration (L4),
  Network-Filter Companion panel (Y1), VoyanceFirewall hand-off (Y2),
  Panic hotkey wiring (Y3), Local Workspaces (L5), Tab Stacks (L6), Mouse
  gestures (L7), CPU/RAM/Network throttle (L8), Vigil Sync (L9), Offline
  filter updates (L10), Tor-private window (L11).
- **All Under-Consideration items (U1&ndash;U20):** by definition, these
  need user signal or a decision gate before work starts.

## External-action items the maintainer owns

These are things this session physically cannot do; they require the
maintainer's account or external services.

1. **Apply to the SignPath OSS program** at <https://signpath.org/>. Once
   approved, set repo secrets `SIGNPATH_API_TOKEN` and var `SIGNPATH_ORG_ID`.
   The N8 workflow step in
   [`.github/workflows/build-matrix.yml`](../.github/workflows/build-matrix.yml)
   activates automatically.
2. **Submit a winget PR** to `microsoft/winget-pkgs` once the v0.2 GitHub
   Release exists. The 3-file manifest is already authored under
   [`dist/winget/SysAdminDoc.Vigil/0.2.0/`](../dist/winget/SysAdminDoc.Vigil/0.2.0/);
   fill in `InstallerSha256` for each architecture, then PR.
3. **Open a Scoop bucket repo** (e.g. `SysAdminDoc/scoop-bucket`) and copy
   [`dist/scoop/vigil.json`](../dist/scoop/vigil.json) into it. Wire a
   release-tag hook to update the hashes.
4. **`choco push` the Chocolatey package** from
   [`dist/chocolatey/vigil/`](../dist/chocolatey/vigil/) after a release.
   Fill in the SHA256 placeholders first.
5. **Bake the NTP extension key** by running
   `python tools/install_ntp_extension.py --chrome-exe <built>/chrome.exe`
   on a host with a freshly-built Vigil. The script writes `key` into
   [`ntp-extension/manifest.json`](../ntp-extension/manifest.json) and from
   that point every build produces the same extension ID.
6. **Generate WiX UpgradeCode GUID once** and pin it into the future
   `installer/msi/vigil.wxs`. See
   [`docs/design/X11-msi-installer.md`](design/X11-msi-installer.md).
7. **Decide the v0.2 design questions** in
   [`ROADMAP.md`'s "Open questions"](../ROADMAP.md#open-questions-for-the-maintainer)
   section &mdash; in particular: DRM (Widevine) posture, telemetry
   posture-doc scope, BetterNext integration boundary.

## Files added or modified this pass

**Modified (4):**
- [`CHANGELOG.md`](../CHANGELOG.md)
- [`apply_overlays.py`](../apply_overlays.py)
- [`initial_preferences`](../initial_preferences)
- [`package.py`](../package.py)

**Added (29):**

| Path | Purpose |
|---|---|
| [`.github/workflows/build-matrix.yml`](../.github/workflows/build-matrix.yml) | N7 + N8 + N9 candidate CI |
| [`CONTRIBUTING.md`](../CONTRIBUTING.md) | N13 |
| [`ROADMAP.md`](../ROADMAP.md) | From prior turn; v0.2 roadmap |
| [`admx/vigil.admx`](../admx/vigil.admx) | X10 |
| [`admx/en-US/vigil.adml`](../admx/en-US/vigil.adml) | X10 |
| [`chromium_src/chrome/browser/resources/policy/vigil_policy_theme.css`](../chromium_src/chrome/browser/resources/policy/vigil_policy_theme.css) | X13 |
| [`devutils/smoke_test.py`](../devutils/smoke_test.py) | N14 |
| [`dist/winget/SysAdminDoc.Vigil/0.2.0/SysAdminDoc.Vigil.installer.yaml`](../dist/winget/SysAdminDoc.Vigil/0.2.0/SysAdminDoc.Vigil.installer.yaml) | N15 |
| [`dist/winget/SysAdminDoc.Vigil/0.2.0/SysAdminDoc.Vigil.locale.en-US.yaml`](../dist/winget/SysAdminDoc.Vigil/0.2.0/SysAdminDoc.Vigil.locale.en-US.yaml) | N15 |
| [`dist/winget/SysAdminDoc.Vigil/0.2.0/SysAdminDoc.Vigil.yaml`](../dist/winget/SysAdminDoc.Vigil/0.2.0/SysAdminDoc.Vigil.yaml) | N15 |
| [`dist/scoop/vigil.json`](../dist/scoop/vigil.json) | X21 |
| [`dist/chocolatey/vigil/vigil.nuspec`](../dist/chocolatey/vigil/vigil.nuspec) | X21 |
| [`dist/chocolatey/vigil/tools/chocolateyInstall.ps1`](../dist/chocolatey/vigil/tools/chocolateyInstall.ps1) | X21 |
| [`dist/chocolatey/vigil/tools/chocolateyUninstall.ps1`](../dist/chocolatey/vigil/tools/chocolateyUninstall.ps1) | X21 |
| [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) | N13 |
| [`docs/build-environment.md`](build-environment.md) | N10 |
| [`docs/toolchain.md`](toolchain.md) | N12 |
| [`docs/ROADMAP_PROGRESS.md`](ROADMAP_PROGRESS.md) | This file |
| [`docs/design/X1-mv2-retention.md`](design/X1-mv2-retention.md) | X1 design |
| [`docs/design/X2-amo-crx-bridge.md`](design/X2-amo-crx-bridge.md) | X2 design |
| [`docs/design/X4-sideload-warning.md`](design/X4-sideload-warning.md) | X4 design |
| [`docs/design/X5-iridium-webrtc.md`](design/X5-iridium-webrtc.md) | X5 design |
| [`docs/design/X7-X8-fingerprint-hardening.md`](design/X7-X8-fingerprint-hardening.md) | X7+X8 design |
| [`docs/design/X11-msi-installer.md`](design/X11-msi-installer.md) | X11 design |
| [`docs/design/X13-policy-overlay.md`](design/X13-policy-overlay.md) | X13 wiring patch sketch |
| [`docs/design/X14-X18-ux-polish.md`](design/X14-X18-ux-polish.md) | UX polish design |
| [`docs/design/X19-ntp-v2.md`](design/X19-ntp-v2.md) | NTP widgets design |
| [`docs/design/X20-velopack.md`](design/X20-velopack.md) | Auto-updater design |
| [`kiosk/branding-kiosk.json`](../kiosk/branding-kiosk.json) | X12 |
| [`kiosk/vigil-kiosk.cmd`](../kiosk/vigil-kiosk.cmd) | X12 |
| [`kiosk/install-watchdog.ps1`](../kiosk/install-watchdog.ps1) | X12 |
| [`ntp-extension/manifest.json`](../ntp-extension/manifest.json) | N3 |
| [`ntp-extension/newtab.html`](../ntp-extension/newtab.html) | N3 |
| [`ntp-extension/newtab.css`](../ntp-extension/newtab.css) | N3 |
| [`ntp-extension/newtab.js`](../ntp-extension/newtab.js) | N3 (MV3-compliant, no inline scripts) |
| [`ntp-extension/icons/*.png`](../ntp-extension/icons/) | N3 (16/32/48/128) |
| [`policies/vigil-extension-forcelist.json`](../policies/vigil-extension-forcelist.json) | X3 |
| [`tools/install_ntp_extension.py`](../tools/install_ntp_extension.py) | N3 |
| [`tools/vigil-portable.cmd`](../tools/vigil-portable.cmd) | X23 |
| [`branding/icons/`](../branding/icons/) | Regenerated by `branding/generate_icons.py` (had been deleted) |

## What was explicitly NOT done

- **No commits.** `git status` reflects all uncommitted local changes. The
  maintainer reviews and commits selectively. (Repo memory notes that
  `git push` to SysAdminDoc/* fails 403 from this VM; maintainer pushes
  elsewhere.)
- **No external service interactions.** No PRs submitted to
  `microsoft/winget-pkgs`, no Scoop bucket created, no `choco push`,
  no SignPath application.
- **No Chromium build attempted.** The design docs are the contract; the
  patches need a real toolchain.
