# X11 — MSI installer

**Status:** design doc; scaffolded WiX project layout. **BLOCKED-no-toolchain**
for the build step (WiX needs `wix.exe` v4+ and the `mini_installer.exe`
binary from a Chromium build).

## Goal

Ship a Vigil MSI installer alongside the Nullsoft `mini_installer.exe`.
Required for Group Policy and Intune Win32App deployment, which sysadmins
use universally and which won't accept the EXE installer for managed deploy
workflows.

## Approach

The Chromium build already produces `mini_installer.exe`. WiX wraps that
binary in an MSI that:

1. Detects whether Vigil is already installed (registry probe).
2. Extracts and runs `mini_installer.exe --do-not-launch-chrome` with
   appropriate elevation.
3. Records the install location and version for repair / uninstall.
4. Optionally writes the Vigil ADMX policies the admin configured into
   `HKLM\Software\Policies\Vigil` via `<RegistryValue>` entries.

## Files (new)

- `installer/msi/vigil.wxs` &mdash; the WiX source document
- `installer/msi/UI/VigilUI.wxs` &mdash; minimal dialog set (welcome, EULA,
  install dir, progress, complete)
- `installer/msi/build.ps1` &mdash; PowerShell wrapper invoking
  `wix build vigil.wxs -out vigil-<version>-<arch>.msi`

## WiX skeleton (vigil.wxs)

```xml
<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">
  <Package Name="Vigil Browser"
           Manufacturer="SysAdminDoc"
           Version="0.2.0"
           UpgradeCode="PUT-A-STABLE-GUID-HERE"
           InstallerVersion="500"
           Scope="perMachine">
    <SummaryInformation Description="Vigil Browser installer (MSI wrapper)"
                        Manufacturer="SysAdminDoc" />
    <MajorUpgrade DowngradeErrorMessage="A newer version of Vigil is already installed." />
    <MediaTemplate EmbedCab="yes" />

    <Feature Id="Main" Title="Vigil" Level="1">
      <Component Id="MiniInstaller" Directory="INSTALLFOLDER">
        <File Source="$(var.MiniInstallerPath)" Id="MiniInstallerExe" />
        <RegistryValue Root="HKLM" Key="Software\Vigil"
                       Name="InstallLocation" Type="string"
                       Value="[INSTALLFOLDER]" />
      </Component>
    </Feature>

    <CustomAction Id="RunMiniInstaller"
                  ExeCommand="&quot;[#MiniInstallerExe]&quot; --do-not-launch-chrome --system-level"
                  Execute="deferred" Impersonate="no" Return="check" />
    <InstallExecuteSequence>
      <Custom Action="RunMiniInstaller" Before="InstallFinalize">NOT Installed</Custom>
    </InstallExecuteSequence>

    <StandardDirectory Id="ProgramFiles64Folder">
      <Directory Id="INSTALLFOLDER" Name="Vigil" />
    </StandardDirectory>

    <ui:WixUI Id="WixUI_InstallDir" InstallDirectory="INSTALLFOLDER" />
  </Package>
</Wix>
```

## Build step in CI

Add to `.github/workflows/build-matrix.yml` after the smoke-test job:

```yaml
  msi:
    needs: smoke
    runs-on: windows-2022
    strategy:
      matrix: { arch: [x64, x86, arm64] }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: vigil-${{ matrix.arch }}-stage*
          path: ./dist
      - name: Install WiX
        run: dotnet tool install --global wix --version 4.*
      - name: Build MSI
        shell: pwsh
        run: |
          $miniInstaller = Get-ChildItem dist -Filter 'mini_installer.exe' | Select-Object -First 1
          wix build installer/msi/vigil.wxs `
            -d MiniInstallerPath=$($miniInstaller.FullName) `
            -arch ${{ matrix.arch }} `
            -out dist/vigil-0.2.0-${{ matrix.arch }}.msi
      - uses: actions/upload-artifact@v4
        with:
          name: vigil-msi-${{ matrix.arch }}
          path: dist/*.msi
```

## Verification

- `msiexec /i vigil-0.2.0-x64.msi /qn` installs silently.
- `msiexec /x {UPGRADE-CODE-GUID} /qn` uninstalls cleanly.
- Intune Win32App deployment accepts the MSI without warnings.
- After install, `chrome.exe --version` runs from `C:\Program Files\Vigil\`.

## Risks

- The `UpgradeCode` GUID must be stable across all Vigil releases or
  side-by-side installs break. Generate once, commit, never change.
- WiX 4 syntax differs from WiX 3; do **not** mix references.
- MSI install requires elevation; consider per-user installer as a follow-up.
