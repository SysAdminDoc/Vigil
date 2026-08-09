# Vigil Browser

![License](https://img.shields.io/badge/license-MIT-green) ![Platform](https://img.shields.io/badge/platform-Python-lightgrey) ![Version](https://img.shields.io/badge/version-0.2.2-blue)

<p align="center">
  <img src="branding/icons/vigil_256.png" alt="Vigil Browser" width="128">
</p>

A lean, privacy-respecting Chromium browser with sensible defaults -- like Brave, without the bloat. Built on [ungoogled-chromium](https://github.com/ungoogled-software/ungoogled-chromium-windows).

## What's Different From Upstream

### Pre-configured Defaults
- **DuckDuckGo as default search engine** with Brave Search, Startpage, Kagi,
  Mojeek, and Google available as built-in alternates
- **Bookmark bar always visible**
- **uBlock Origin pre-installed** from a pinned, SHA-256-verified GitHub release
  archive. The build cache supports offline packaging; no Chrome Web Store update
  URL is required for the bundled copy.
- **Chrome Web Store access restored** for easy extension management
- **Privacy-focused defaults**: Do Not Track enabled, Safe Browsing protection on
  with reporting disabled, autofill disabled, translation disabled, network prediction disabled
- **Skip first-run UI** and default browser prompts
- **Client Hints removed by default.** The ungoogled `RemoveClientHints`
  feature suppresses UA-CH and related client-hint headers/metadata. The
  existing `chrome://flags/#remove-client-hints` entry remains available for
  administrators who need to change the default per profile.
- **Secure DNS starts on Quad9 with no fallback.** The built-in settings
  picker offers Quad9, NextDNS, Cloudflare, Mullvad, AdGuard, and Control D,
  plus a validated custom endpoint. A failed resolver does not silently fall
  back to plaintext DNS; administrators can change the resolver in Settings.
- **Command palette on `Ctrl+Shift+P`.** The bundled palette searches Vigil
  settings, open tabs, bookmarks, and the last seven days of history. It opens
  as an overlay on normal web pages using on-demand `activeTab` injection; it
  has no automatic all-site content script. Browser-owned pages use a standalone
  extension tab where content scripts are unavailable.
- **Optional NTP widgets.** Enable local notes, top sites, bookmark-folder
  links, city weather, or up to three HTTPS RSS feeds from the new-tab settings
  panel. They are disabled by default; notes stay local and network widgets
  only fetch after you enable and configure them. Shortcut icons are local
  initial-letter marks, so a fresh NTP never fetches remote favicons. Weather is
  restricted to the two Open-Meteo APIs; RSS requests require per-origin
  optional permission and enforce HTTPS, timeouts, redirect rejection,
  content-type checks, and body limits.
- **Memory Saver is enabled by default.** Chromium's built-in performance
  settings still expose the aggressiveness and per-domain exception controls;
  Vigil starts with inactive tabs eligible for hibernation after the upstream
  120-minute threshold.
- **Vertical tabs are available from Settings.** The built-in tab-strip position
  toggle is enabled in Appearance, with Chromium's existing tab restore and
  tab-search behavior preserved.
- **Split view is ready from the toolbar or keyboard.** Vigil starts Chromium's
  two-pane split view with its toolbar button pinned; `Ctrl+Shift+\\` creates a
  split from the active tab. Multi-pane layouts remain out of scope.
- **Reader Mode includes Markdown export.** Chromium's built-in Read Anything
  distiller is available from its desktop entry points, and the reader toolbar
  downloads the distilled article as `vigil-reading-mode.md`.

### Manifest V2 Policy

Vigil retains Chromium's Manifest V2 extension support for the long tail of
privacy and administrator extensions. The pinned ungoogled-chromium patch
`core/ungoogled-chromium/extensions-manifestv2.patch` keeps MV2 extensions
allowed and leaves the deprecation manager warning-only. `build.py` verifies
both the patch-series entry and the patched source behavior on every build,
including incremental builds, so a Chromium or submodule bump fails closed if
retention disappears. Manifest V3 remains supported normally; Vigil does not
weaken extension installation or publisher-trust checks as part of this policy.

### First-run network contract

A fresh profile makes no NTP network request before a user explicitly enables a
network widget. Notes, top sites, bookmarks, weather, and RSS start disabled;
the page uses local shortcut marks and the disabled-widget path performs no
fetch. Weather has two fixed API origins, while RSS requires a separate
permission grant for the exact HTTPS feed origins saved by the user.

Search suggestions are intentionally enabled. Typing a query is the explicit
user action that permits a suggestion request, and the only configured endpoint
is DuckDuckGo's `https://duckduckgo.com/ac/` service. Safe Browsing remains
enabled, its reporting uploads remain disabled, and no telemetry endpoint is
configured. The offline `devutils/privacy_probe.py` checks this source-level
fresh-profile contract without launching Chromium or contacting a service.

### Opt-in Global Privacy Control

`chrome://settings` exposes an opt-in Global Privacy Control toggle. It is off
by default. When enabled, profile HTTP(S) requests send `Sec-GPC: 1`, and
`navigator.globalPrivacyControl` is true in windows and workers. The signal is
only a request to honor the user's privacy preference: sites may ignore it, and
it is not a legal-compliance guarantee. Preference changes apply without a
restart. See the [W3C GPC specification](https://www.w3.org/TR/gpc/) and
[MDN's Sec-GPC reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Sec-GPC).

### Extension permission boundaries

The bundled NTP declares only its fixed weather origins. RSS is opt-in and uses
Chrome optional host permissions for the exact HTTPS feed
origins saved by the user; it never fetches a feed while RSS is disabled or
permission is absent. The command palette declares `activeTab` and `scripting`
instead of an all-site content script, injects only after its keyboard command,
and validates the iframe bridge with exact source and origin checks. These
contracts are covered by `devutils/test_extension_boundaries.py` and the CI
JavaScript syntax check.

The permission audit is intentionally explicit: NTP `storage` holds its local
settings, `topSites` supplies the local top-sites widget, and `bookmarks` reads
the selected local folder. Palette `bookmarks`, `history`, and `tabs` provide
its search sources; `activeTab` grants the user-invoked overlay access and
`scripting` loads that overlay only after the command. No extension requests
identity, cookies, web requests, native messaging, or file access.

### Owned-extension localization

The NTP and command palette ship an English `_locales/en/messages.json` baseline
with a local English fallback for plain-file development and future translated
packs. Static labels, accessibility attributes, manifest names, service-worker
results, and runtime error states all use the offline i18n lookup; no translation
service or runtime network request is involved.

### Architecture (Brave-Inspired)
- **`chromium_src/` overlay system** -- Drop-in file replacements that mirror the Chromium source tree. Preferred over patches for file-level changes since they don't break on rebase.
- **`initial_preferences`** -- Single JSON file controlling all first-run defaults (like Brave's `brave_profile_prefs.cc`)
- **`branding.json`** -- Central configuration for browser name, company, and URLs
- **`setup_extensions.py`** -- Automated extension bundler that downloads and packages uBlock Origin
- **`palette-extension/`** -- Bundled MV3 command palette and keyboard shortcut
- **`apply_overlays.py`** -- Applies chromium_src overlays, custom NTP, and branding at build time
- **Custom New Tab Page** -- Dark-themed NTP with clock, search bar, and configurable shortcuts

### File Structure
```
Vigil/
  branding.json              # Browser name, company, URLs
  initial_preferences        # First-run browser settings
  setup_extensions.py        # Downloads and bundles uBlock Origin
  apply_overlays.py          # Applies overlays + NTP + branding
  chromium_src/              # Brave-style file replacements
  ntp/
    newtab.html              # Custom dark New Tab Page
  patches/
    series                   # Patch order (CWS/search compatibility)
    ungoogled-chromium/windows/
      windows-restore-google-search-engine.patch
      ...
```

## Downloads

Check the [Releases](../../releases) page for pre-built binaries (x64, x86, arm64).

## Building

### Prerequisites

Google only supports [Windows 10 x64 or newer](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/windows_build_instructions.md#system-requirements).

**IMPORTANT**: Only set up what's listed below. Do NOT install `depot_tools` -- this fork has a custom build process that avoids Google's pre-built binaries.

#### Visual Studio

[Follow the "Visual Studio" section of the official Windows build instructions](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/windows_build_instructions.md#visual-studio).

#### Other Requirements

- Python 3.12+
- 7-Zip or WinRAR (for extracting build dependencies)
- WiX Toolset 5 (for the MSI installer)
- ~100 GB free disk space
- ~16 GB RAM recommended

### Build Steps

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/SysAdminDoc/Vigil.git
cd Vigil

# Build (downloads sources, applies patches + overlays, compiles)
python build.py

# Package (bundles pinned uBlock Origin, creates installer + zip)
python package.py

# Package without network access after seeding build/download_cache/
python package.py --offline

# Validate a seeded incremental cache before any build mutation
python devutils/build_preflight.py
python build.py --ci --offline --preflight

# Inspect the local profile migration tool
python devutils/profile_transfer.py --help

# Create a privacy-safe support receipt from release and smoke reports
python devutils/diagnostics.py --receipt build/release-receipt.json \
  --smoke-report build/smoke-report.json \
  --output build/support-receipt.json
```

Offline builds are fail-closed. An incremental preflight checks the existing
source tree and the exact SHA-256-pinned uBlock archive; a fresh `--tarball`
build additionally enumerates every ungoogled-Chromium download and rejects
missing or unfinished `.partial` files before extraction. Build and package
staging uses sibling temporary paths with recoverable promotion, so an
interrupted run can be resumed after the preflight passes. Compare incremental
and fresh-tarball outputs only after both use the same `toolchain.json`, source
revision, architecture, and deterministic timestamp inputs. The SSL bypass
flag is development-only, requires `VIGIL_DEV_ALLOW_INSECURE_DOWNLOADS=1`, and
strict release receipts reject artifacts produced with it.

### Release source of truth

`dist/scoop/vigil.json` is the authoritative Vigil version consumed by
`package.py`; `toolchain.json` is authoritative for the Chromium and pinned
toolchain identifiers (currently Chromium `145.0.7632.159`). The README badge, extension manifests, changelog
heading, and package-manager metadata are checked against those sources. The
build/package commands above and the output names in the Output section are
the supported release contract.

#### Build Options

| Flag | Description |
|------|-------------|
| `--x86` | Build 32-bit binaries |
| `--arm` | Build ARM64 binaries |
| `-j N` | Use N CPU threads for compilation |
| `--ci` | CI mode (incremental, with timeout) |
| `--tarball` | Use source tarball instead of git clone |

### Output

Build artifacts are placed in `build/`:
- `ungoogled-chromium_*_installer_*.exe` -- Windows installer
- `vigil_*_installer_*.msi` -- Group Policy / Intune-friendly MSI installer

The MSI is authored as per-machine and uses a machine-owned registry key path
for component health, so repair/upgrade/uninstall do not depend on whichever
user happens to build or install it. Validate an artifact without changing the
host with `python devutils/msi_lifecycle.py --msi build/vigil_*.msi`; an
elevated disposable validation host may add `--system-lifecycle` to exercise
silent install, repair, and uninstall.
- `ungoogled-chromium_*_windows_*.zip` -- Portable zip (includes uBlock Origin, initial_preferences, and managed policy baselines)

## Customization

### Changing the Browser Name

Edit `branding.json`:
```json
{
  "browser_name": "MyBrowser",
  "company_name": "MyCompany",
  "homepage_url": "https://example.com"
}
```

### Adding More Pre-installed Extensions

Edit `setup_extensions.py` to add additional extensions, or add JSON files to a `default_extensions/` directory following Chromium's [external extensions format](https://developer.chrome.com/docs/extensions/how-to/distribute/install-extensions#preferences).

### Adding File Overlays

Place files in `chromium_src/` mirroring the Chromium source tree structure:
```
chromium_src/chrome/browser/some_file.cc
-> replaces build/src/chrome/browser/some_file.cc
```

### Modifying Default Settings

Edit `initial_preferences` -- this is a standard Chromium [initial preferences file](https://www.chromium.org/administrators/configuring-other-preferences/).

### Local profile migration

`devutils/profile_transfer.py` provides an account-free, versioned local
migration path for the NTP settings snapshot returned by
`chrome.storage.local.get()` and the bookmark tree returned by
`chrome.bookmarks.getTree()`. It carries selected display settings, shortcuts,
notes, and HTTP(S) bookmarks; passwords, cookies, and history are rejected and
never written to an export. Preview an import before writing new snapshots:

```bash
python devutils/profile_transfer.py export \
  --settings settings-snapshot.json \
  --bookmarks bookmarks-tree.json \
  --output vigil-profile.json
python devutils/profile_transfer.py import \
  --input vigil-profile.json \
  --current-settings settings-snapshot.json \
  --current-bookmarks bookmarks-tree.json \
  --dry-run
python devutils/profile_transfer.py import \
  --input vigil-profile.json \
  --current-settings settings-snapshot.json \
  --current-bookmarks bookmarks-tree.json \
  --settings-output migrated-settings.json \
  --bookmarks-output migrated-bookmarks.json
```

The import report lists settings overwritten, duplicate bookmark URLs, missing
bookmark roots, and added folders/items. It only reads and writes local JSON;
it does not open Chromium databases or contact a network service.

## Build verification

The supported release path is a local Windows build. Use `python build.py --ci -j N`
for an incremental compile followed by packaging; it runs the same deterministic smoke checks against the resulting output without reusing a browser session.
Pass `--offline` to the CI build after the pinned extension archive is present in
`build/download_cache/`.

The repository checks can be run without a browser session:

```bash
python -m pytest -q
python -m ruff check .
python devutils/build_preflight.py
python devutils/profile_transfer.py --help
python devutils/privacy_probe.py
python devutils/smoke_test.py --build-out build/src/out/Default
node --check ntp-extension/newtab.js
node --check palette-extension/background.js
node --check palette-extension/content.js
node --check palette-extension/palette.js
```

### Kiosk mode

The kiosk launcher accepts one absolute HTTPS URL (or `about:blank`) and reads
`VigilKioskUrl` from the machine policy when no argument is supplied. It does
not accept extra Chromium arguments:

```powershell
.\kiosk\vigil-kiosk.cmd https://clinic.example.org/portal
pwsh -File .\kiosk\install-watchdog.ps1 -KioskUrl https://clinic.example.org/portal
pwsh -File .\kiosk\install-watchdog.ps1 -Uninstall
```

Deploy `policies/vigil-kiosk.json` with the managed policy baseline to keep
autoplay policy-controlled; the launcher never overrides autoplay on its
command line. The watchdog logs bounded exit-code messages only, backs off up
to 60 seconds, and stops after five failures in 15 minutes. Uninstall removes
the task, owned wrapper/config/state files, and an event-log source or policy
value only when the installer still owns it and it has not been changed.

Packaging can also emit `build/release-receipt.json` with the actual artifact
hashes and source/toolchain inputs:

```bash
python package.py --receipt
```

After the packaged smoke test, `devutils/diagnostics.py` combines that report
with the release receipt into `build/support-receipt.json`. The support receipt
has stable check IDs and failure codes, records versions/toolchain IDs and
architectures, and redacts URLs, absolute/profile paths, and keyed secrets so it
can be attached to an admin support ticket without exporting browsing data:

```bash
python devutils/diagnostics.py \
  --receipt build/release-receipt.json \
  --smoke-report build/smoke-report.json \
  --output build/support-receipt.json
```

Release validation adds `--strict-manifests --update-manifests`; it fails when
any advertised package-manager artifact is missing or still has a placeholder
hash, or when one of the declared x64/x86/arm64 release architectures is
missing both its installer and portable archive. Receipts state explicitly
that artifacts are unsigned.

### Release refresh gate

Release jobs must run the dependency-free refresh gate before publishing. It
consumes a reviewable upstream metadata JSON rather than silently querying the
network during a build:

```bash
python devutils/release_gate.py \
  --metadata path/to/upstream-release.json \
  --format json \
  --output build/release-gate.json
```

`release_policy.json` currently requires the Chromium line to be no more than
one major release behind upstream and the latest stable/security refresh to be
no more than 14 days old. Missing, future, stale, or insecure metadata fails
closed. For an emergency security patch, record the upstream advisory or
commit, apply the smallest reviewed patch, run the normal build checks, refresh
the metadata, and pass the gate; there is no stale-release override.

The repository’s GitHub workflows are intentionally limited to read-only
quality checks, manual release validation, and reviewable artifact uploads.
They do not clone personal forks, force-push package repositories, or require
a publication PAT. External package-manager submissions remain a maintainer
review step using the generated release receipt and hashes.

## Credits

- [ungoogled-chromium](https://github.com/Eloston/ungoogled-chromium) by Eloston
- [ungoogled-chromium-windows](https://github.com/ungoogled-software/ungoogled-chromium-windows) by the ungoogled-software team
- [uBlock Origin](https://github.com/gorhill/uBlock) by Raymond Hill

## License

[BSD-3-Clause](LICENSE)
