# X20 — Auto-updater via Velopack

**Status:** design doc; **BLOCKED-no-toolchain** for the integration step
(Velopack ships as a Rust CLI + .NET runtime; needs a build host with
`dotnet` &ge; 8 to run the `vpk` packer).

## Goal

Make Vigil self-updating. Pick **Velopack** over Omaha 4:

| Criterion | Omaha 4 | Velopack |
|---|---|---|
| Cost to add to a Chromium fork | very high (C++ service, server infra) | low (single CLI step in CI) |
| Maintenance burden | high | low (small Rust crate) |
| Delta updates | yes | yes |
| GitHub Releases backend | adapter needed | first-class |
| Staged rollouts | yes | yes (added 2026) |
| Code-signing integration | possible but heavy | drops into the SignPath workflow |

Omaha 4 is what Google ships; for a solo-maintained fork it's overkill.

## Approach

1. **Pack at release time.** Add a CI job that, after smoke-test pass, runs
   `vpk pack` against the built `chrome.exe` directory. The pack step
   produces a `Releases` directory with full + delta packages plus a
   manifest.
2. **Host on GitHub Releases.** Velopack reads release artifacts directly
   from a `RELEASES` file; we publish that as a release asset.
3. **Embed the updater stub.** Velopack injects a small (~5 MB) updater
   `Update.exe` alongside `chrome.exe`. At launch, the Vigil shortcut points
   at Velopack's `update.exe` which transparently launches `chrome.exe` and
   silently checks for updates.

## Files (new)

- `installer/velopack/vpk.config.json` &mdash; Velopack pack config
- `installer/velopack/post-update.ps1` &mdash; runs after a successful
  delta apply (clears the old NTP-extension cache, etc.)

### `vpk.config.json` skeleton

```json
{
  "packId": "Vigil",
  "packVersion": "0.2.0",
  "packDir": "build/src/out/Default",
  "packTitle": "Vigil Browser",
  "packAuthors": "SysAdminDoc",
  "channel": "stable",
  "releaseUrl": "https://github.com/SysAdminDoc/Vigil/releases/latest/download/",
  "exclude": [
    "*.pdb",
    "mini_installer.exe",
    "setup.exe"
  ],
  "icon": "branding/icons/vigil_256.ico",
  "shortcuts": [
    {
      "exe": "chrome.exe",
      "name": "Vigil",
      "location": "StartMenu"
    }
  ]
}
```

## CI hook (build-matrix.yml addition)

```yaml
  pack:
    needs: smoke
    runs-on: windows-2022
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with: { dotnet-version: '8.0.x' }
      - run: dotnet tool install --global vpk
      - uses: actions/download-artifact@v4
        with: { name: vigil-x64-stage*, path: ./dist }
      - name: vpk pack
        run: vpk pack --config installer/velopack/vpk.config.json --output ./packed
      - uses: actions/upload-artifact@v4
        with: { name: vigil-velopack-x64, path: ./packed/* }
```

## Channels

Two channels at v0.3:
- `stable` (every tagged release)
- `canary` (built from `canary` branch nightly via cron-driven workflow,
  separate channel ID in `vpk.config.json`)

Users on stable do not see canary updates and vice versa.

## Verification

- Install Vigil v0.2 via the Velopack-packed installer.
- Launch; the updater pings the GitHub Release URL.
- Tag v0.2.1; CI rebuilds and uploads.
- Restart Vigil; it downloads the delta package and replaces itself.
- `chrome --version` reports 0.2.1.
- Old version is preserved under `app-0.2.0/` for rollback.

## Risks

- **Update.exe path collision** with Chromium's own updater. Vigil already
  removes most of upstream's updater (ungoogled-chromium does this), so
  conflict is unlikely; but verify the patches that strip Google Update
  also strip the `setup.exe`-driven updater registry handles.
- **MSI vs Velopack coexistence.** MSI installs leave their own
  uninstall registry entry. Velopack does too. Document the recommended
  deploy path: **either MSI (managed) OR Velopack (user-managed)**, not both
  on the same machine.
- **Bandwidth.** Delta packages are typically 5&ndash;15 MB vs the 110 MB
  full installer. GitHub Releases handles this fine. Bandwidth-budget
  noted in `docs/build-environment.md`.
