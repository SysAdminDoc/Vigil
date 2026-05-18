# Toolchain

Pinned toolchain versions for Vigil Chromium builds. Roadmap item `N12`.

This file pins what the build host must have installed. Bump it in lockstep with each
Chromium milestone Vigil tracks. The lines marked **inherited** are determined by the
upstream Chromium revision; we just record them.

## Currently targeted

| Tool | Version | Source / why |
|---|---|---|
| **Chromium milestone** | `145.0.7632.159` | [`branding.json`](../branding.json) `version_suffix` + [`revision.txt`](../revision.txt) |
| **Python** | `3.12.x` | `.github/workflows/main.yml`; ungoogled tooling requires &ge;3.11 since [drop-py-3.8-3.10](https://github.com/ungoogled-software/ungoogled-chromium-windows/commit/a657b8f) |
| **Pillow** | latest pinned in [`requirements.txt`](../requirements.txt) | icon generator |
| **Visual Studio Build Tools** | 2022 17.x | [Chromium Windows build deps](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/windows_build_instructions.md#visual-studio) |
| **Windows SDK** | per Chromium milestone (inherited) | included by VS Build Tools install |
| **clang** | per Chromium milestone (inherited) | bundled in `third_party/rust-toolchain-*` once `build.py` runs |
| **rustc** | per Chromium milestone (inherited) | bundled, version recorded in `third_party/rust-toolchain/INSTALLED_VERSION` |
| **GN** | per Chromium milestone (inherited) | bootstrapped from source by `build.py` |
| **Ninja** | per Chromium milestone (inherited) | shipped under `third_party/ninja` |
| **7-Zip OR WinRAR** | latest stable | tarball extraction; either is fine |
| **Node.js** | 20 LTS | GitHub-Actions stage Node action |
| **Free disk** | ~120 GB | source tree + build outputs + cache |
| **RAM** | 16 GB minimum, 32 GB recommended | linker working set on x64 |
| **GitHub Actions runner** | `windows-2022` | matches our build matrix; do not switch to `windows-latest` without verifying clang |

## Future change-control

When a Chromium milestone bumps:

1. Update the **Chromium milestone** row.
2. Run `python ungoogled-chromium/utils/clone.py -o build/src` on a throwaway host
   and capture: `rustc --version`, `clang --version`, `ninja --version`, `gn --version`.
3. Record those in the inherited rows above.
4. If Python's minimum has bumped upstream, update the workflow's
   `actions/setup-python` version.
5. Verify by reading
   [Chromium's `docs/windows_build_instructions.md`](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/windows_build_instructions.md)
   for the target milestone; if VS / Windows-SDK floors have moved, update.

## Verifying your local toolchain

Before opening a build PR:

```pwsh
python --version                # 3.12.x
python -m pip show Pillow       # Name: Pillow ...
where 7z                        # or where winrar.exe
node --version                  # v20.x
# Visual Studio 2022 with Desktop Development with C++ workload installed
```

If any of those drift below the floor above, your build will fail in a
non-obvious place (most often during `bootstrap.py` or `rustc.exe` invocation).
