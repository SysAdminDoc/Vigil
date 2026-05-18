# Architecture

How Vigil turns the upstream Chromium source into a Vigil installer. Read this once;
refer back when you wonder *which layer* a change belongs in.

## 30-second tour

```
                       upstream/Chromium tarball or git
                                     |
                                     v
        +---------------------------------------------------------+
        |                                                         |
        |  build.py                                               |
        |    1. fetch chromium  (clone OR tarball)                |
        |    2. prune binaries  (pruning.list)                    |
        |    3. apply ungoogled-chromium patches                  |
        |    4. apply Vigil/Windows patches    (patches/series)   |
        |    5. domain-substitute                                 |
        |    6. apply_overlays.py                                 |
        |         - copy chromium_src/* into source tree          |
        |         - install custom NTP                            |
        |         - swap icons + branding strings                 |
        |    7. gn gen + ninja chrome chromedriver mini_installer |
        |                                                         |
        +-------------------------+-------------------------------+
                                  |
                                  v
                          build/src/out/Default
                                  |
                                  v
        +---------------------------------------------------------+
        |  package.py                                             |
        |    1. copy mini_installer.exe -> versioned installer    |
        |    2. copy initial_preferences alongside chrome.exe     |
        |    3. setup_extensions.py                               |
        |         - download latest uBO from gorhill releases     |
        |         - stage under Extensions/<id>/<v>/              |
        |         - write default_extensions/<id>.json pointer    |
        |    4. zip everything into the portable archive          |
        +---------------------------------------------------------+
```

## The change layers, in order of preference

When you want Vigil to differ from upstream Chromium, pick the **highest-numbered
layer** that can express the change. Lower numbers cost more to maintain.

### 1. `initial_preferences` &mdash; free, infinite-lifetime

A standard Chromium [initial-preferences file](https://www.chromium.org/administrators/configuring-other-preferences/)
placed next to `chrome.exe` at install time. It seeds a fresh profile's prefs on first
run. Surviving Chromium bumps is free as long as the pref keys still exist upstream.

Use for:

- Default search engine (`default_search_provider_data`)
- Privacy toggles (`enable_do_not_track`, `safebrowsing.enabled`, ...)
- HTTPS-First mode (`https_only_mode_enabled`, `https_first_balanced_mode_enabled`)
- Content-setting defaults (`profile.default_content_setting_values.*`)
- Privacy Sandbox API kill switch (`privacy_sandbox.apis_enabled_v2`)
- Skip-first-run distribution flags

**Don't use for:**

- UI strings or icons (those are compile-baked &mdash; use overlay or branding)
- Policy that an admin needs to lock (use ADMX)

### 2. `branding.json` &mdash; build-time string and icon swap

Read by [`apply_overlays.py`](../apply_overlays.py) at build time. Replaces the
`Chromium`/`The Chromium Authors` strings and product-logo PNGs in the source tree
before compilation.

Use for renaming the browser, changing the company, swapping the icon set.

### 3. `chromium_src/` overlays &mdash; the Brave pattern

This is the workhorse. Files under [`chromium_src/`](../chromium_src/) mirror the upstream
Chromium tree path-for-path; `apply_overlays.py` copies them into place after patches
apply, before `gn gen`. The original file is backed up to `*.orig` so the build can be
re-run cleanly.

Concretely:

```
chromium_src/chrome/browser/resources/settings/settings.html
   -> overwrites
build/src/chrome/browser/resources/settings/settings.html
```

Existing overlays in this repo all theme `chrome://` internal pages
(`settings`, `flags`, `history`, `bookmarks`, `downloads`, `extensions`,
`policy`, `neterror`) with the Vigil dark "IT admin" palette. See
[`chromium_src/README`](../chromium_src/README).

Use overlays for:

- `chrome://` page HTML / CSS / TypeScript (the bulk of our changes)
- Single-file C++ replacements where you're substituting an entire impl

**Don't use overlays for:**

- Cross-cutting C++ changes that need `#if VIGIL` style branches &mdash; that's a patch.
- Changing build flags &mdash; that's `flags.windows.gn` or a patch.

When a Chromium bump breaks an overlay, the build fails to compile against the new
upstream API. That's the intentional design: an overlay failing loud beats a patch
that silently no-ops.

### 4. `patches/` &mdash; quilt-format patches, last resort

[`patches/series`](../patches/series) lists patches in apply order. Each patch is
applied with `git/usr/bin/patch.exe` from inside the upstream Chromium tree, after
the ungoogled-chromium patch series and before overlays.

Use for:

- Compiled C++ behavior changes that touch >1 file or need preprocessor branches
- Build-system patches (`BUILD.gn`, `.gni`, generated-resource fixups)
- Restoring upstream behavior that ungoogled-chromium has stripped (already in
  this repo for the Chrome Web Store and Google search-engine entries)

Each patch is fragile across Chromium bumps. When adding one, prefer the smallest
possible diff, and document its upstream-equivalent or attribution in the patch
header. Brave, Cromite, and Iridium are the reference projects to lift from.

### 5. `setup_extensions.py` &mdash; bundled external extensions

Runs during `package.py`, after the binaries are built. Downloads the latest uBlock
Origin CRX zip from the gorhill/uBlock GitHub release, stages it under
`Extensions/<id>/<v>/`, and writes a `default_extensions/<id>.json` pointer that
Chromium's external-extensions mechanism picks up on first profile launch.

This is how Vigil "ships" uBO. The same mechanism can stage additional extensions in
the future (see ROADMAP `X3` for force-install policy + bundled set).

### 6. Bundled NTP extension &mdash; `ntp-extension/`

The dark Vigil new-tab page lives as a Chromium extension that declares
`chrome_url_overrides.newtab`. This is the pattern Brave and Cromite both use; it
avoids patching `chrome/browser/ui/views/new_tab_page/` and survives Chromium bumps
cleanly. See [`docs/design/N3-ntp-extension.md`](design/N3-ntp-extension.md).

### 7. ADMX policy templates &mdash; `admx/`

IT-admin-facing enterprise policy. Vigil's ADMX is a strict subset of Chrome's,
plus a handful of Vigil-only policies (kiosk mode, panic hotkey, etc.). Loaded into
local Group Policy via `gpedit.msc` or pushed via Intune Win32App. Distinct from
runtime prefs &mdash; ADMX policies *lock* prefs against the user.

## What lives where, by example

| You want to... | Layer | File |
|---|---|---|
| Change default search engine | 1 (pref) | `initial_preferences` |
| Disable Privacy Sandbox prompts | 1 (pref) | `initial_preferences` |
| Rename "Chromium" &rarr; "Vigil" everywhere | 2 (branding) | `branding.json` |
| Restyle `chrome://settings` | 3 (overlay) | `chromium_src/.../settings.html` |
| Restore Chrome Web Store after ungoogled stripped it | 4 (patch) | `patches/.../windows-restore-webstore.patch` |
| Pre-install uBlock Origin | 5 | `setup_extensions.py` |
| Change first-tab landing page | 6 | `ntp-extension/` |
| Lock IT-admin policy: extension allowlist | 7 | `admx/vigil.admx` + `policies/...` |

## Build output

After `build.py`:

```
build/src/out/Default/
   chrome.exe
   chromedriver.exe
   mini_installer.exe
   *.dll *.pak *.bin *.dat (Chromium binaries)
   args.gn (records target_cpu)
```

After `package.py`:

```
build/
   ungoogled-chromium_<chromium>-<ucw>.<vigil>_installer_<arch>.exe
   ungoogled-chromium_<chromium>-<ucw>.<vigil>_windows_<arch>.zip
build/src/out/Default/
   + initial_preferences       (copied from repo root)
   + Extensions/<id>/<v>/       (uBO staged)
   + default_extensions/<id>.json
   + ntp/                       (legacy; superseded by ntp-extension/)
```

## CI shape

Today: [`.github/workflows/main.yml`](../.github/workflows/main.yml) chains 12 build
stages for x64, 16 for x86, and an arm64 chain &mdash; each stage runs the same
`./.github/actions/stage` Node action, which resumes ninja within the 6-hour
GitHub-Actions job limit and uploads the partial source tree as an artifact.

Roadmap-`N7` work replaces this with a reusable workflow + matrix; the candidate
lives at [`.github/workflows/build-matrix.yml`](../.github/workflows/build-matrix.yml)
and runs alongside the chain until parity is verified.

## Files you should rarely touch

- [`domain_substitution.list`](../domain_substitution.list) and
  [`pruning.list`](../pruning.list) &mdash; these are tracking files for the
  ungoogled-chromium upstream. Edits drift away from upstream tooling and create
  merge work forever.
- [`ungoogled-chromium/`](../ungoogled-chromium/) submodule &mdash; never commit
  changes to the submodule from within this repo; contribute upstream and bump the
  pointer.
- [`devutils/`](../devutils/) &mdash; small helper scripts inherited from
  ungoogled-chromium-windows; check whether your script belongs upstream first.
