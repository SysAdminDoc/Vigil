# Vigil Browser

![License](https://img.shields.io/badge/license-MIT-green) ![Platform](https://img.shields.io/badge/platform-Python-lightgrey)

<p align="center">
  <img src="branding/icons/vigil_256.png" alt="Vigil Browser" width="128">
</p>

A lean, privacy-respecting Chromium browser with sensible defaults -- like Brave, without the bloat. Built on [ungoogled-chromium](https://github.com/ungoogled-software/ungoogled-chromium-windows).

## What's Different From Upstream

### Pre-configured Defaults
- **Google as default search engine** with search suggestions enabled
- **Bookmark bar always visible**
- **uBlock Origin pre-installed** (downloaded from GitHub releases at build time)
- **Chrome Web Store access restored** for easy extension management
- **Privacy-focused defaults**: Do Not Track enabled, Safe Browsing disabled, autofill disabled, translation disabled, network prediction disabled
- **Skip first-run UI** and default browser prompts

### Architecture (Brave-Inspired)
- **`chromium_src/` overlay system** -- Drop-in file replacements that mirror the Chromium source tree. Preferred over patches for file-level changes since they don't break on rebase.
- **`initial_preferences`** -- Single JSON file controlling all first-run defaults (like Brave's `brave_profile_prefs.cc`)
- **`branding.json`** -- Central configuration for browser name, company, and URLs
- **`setup_extensions.py`** -- Automated extension bundler that downloads and packages uBlock Origin
- **`apply_overlays.py`** -- Applies chromium_src overlays, custom NTP, and branding at build time
- **Custom New Tab Page** -- Dark-themed NTP with clock, search bar, and configurable shortcuts

### File Structure
```
ungoogled-chromium-windows/
  branding.json              # Browser name, company, URLs
  initial_preferences        # First-run browser settings
  setup_extensions.py        # Downloads and bundles uBlock Origin
  apply_overlays.py          # Applies overlays + NTP + branding
  chromium_src/              # Brave-style file replacements
  ntp/
    newtab.html              # Custom dark New Tab Page
  patches/
    series                   # Patch order (includes CWS restore + Google search)
    ungoogled-chromium/windows/
      windows-restore-google-search-engine.patch
      windows-restore-webstore.patch
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
- ~100 GB free disk space
- ~16 GB RAM recommended

### Build Steps

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/SysAdminDoc/Vigil.git
cd ungoogled-chromium-windows

# Build (downloads sources, applies patches + overlays, compiles)
python build.py

# Package (bundles uBlock Origin, creates installer + zip)
python package.py
```

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
- `ungoogled-chromium_*_windows_*.zip` -- Portable zip (includes uBlock Origin + initial_preferences)

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

## CI/CD

The GitHub Actions workflow builds x64, x86, and arm64 binaries on every tag push or manual dispatch. Builds are split across multiple stages due to the 6-hour GitHub Actions timeout limit.

Trigger a manual build: Actions > CI > Run workflow

## Credits

- [ungoogled-chromium](https://github.com/Eloston/ungoogled-chromium) by Eloston
- [ungoogled-chromium-windows](https://github.com/ungoogled-software/ungoogled-chromium-windows) by the ungoogled-software team
- [uBlock Origin](https://github.com/gorhill/uBlock) by Raymond Hill

## License

[BSD-3-Clause](LICENSE)
