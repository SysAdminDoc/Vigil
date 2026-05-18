# Build Environment & Reproducibility Notes

Roadmap item `N10`. Partial-reproducibility groundwork for Vigil builds.

Full deterministic Chromium builds are an unsolved problem &mdash; Brave's
[reproducible-builds tracking issue](https://github.com/brave/brave-browser/issues/5830)
has been open since 2019. Vigil targets *partial* reproducibility: any two CI runs of
the same git ref should produce binaries that differ only in fields that are
provably non-semantic (build timestamps, PDB GUIDs, embedded paths).

This file records the inputs that matter so a third party can attempt to reproduce
our builds, and lists the known sources of nondeterminism we have not yet eliminated.

## Build inputs

A reproduction requires these to be byte-identical:

1. The Vigil git revision (the `tag` driving the workflow).
2. The ungoogled-chromium submodule pointer recorded in `.gitmodules`.
3. The upstream Chromium tarball SHA from `ungoogled-chromium/downloads.ini`.
4. The Vigil Windows downloads SHA list from [`downloads.ini`](../downloads.ini).
5. The Vigil patch set in [`patches/series`](../patches/series).
6. The Vigil overlay tree under [`chromium_src/`](../chromium_src/).
7. The branding map in [`branding.json`](../branding.json).
8. The initial preferences file [`initial_preferences`](../initial_preferences).
9. The build flags in [`flags.windows.gn`](../flags.windows.gn).
10. The toolchain pinned in [`docs/toolchain.md`](toolchain.md).

GitHub release artifacts will eventually carry SLSA build provenance via
[`actions/attest-build-provenance`](https://github.com/actions/attest-build-provenance);
see roadmap `N9`. That covers points 1&ndash;9 by recording the workflow input;
point 10 still needs a hand-verified toolchain attestation.

## Known sources of nondeterminism

These currently differ between two clean builds of the same ref. We document them so
nobody wastes time investigating known issues.

| Source | Where it lives | Severity | Plan |
|---|---|---|---|
| `__DATE__`/`__TIME__` macros | Various Chromium files | Low | upstream issue; Chromium already mostly purged, audit per bump |
| PDB GUIDs | `chrome.exe.pdb`, all `*.dll.pdb` | Cosmetic | accepted; PDBs are not in the user-facing zip |
| Linker timestamps | `chrome.exe`, `chrome.dll` PE headers | Low | upstream `/Brepro` flag, set when `is_official_build=true` |
| PGO profile ordering | `chrome.exe` text section | High | PGO instrumented runs are nondeterministic by nature; phase=2 (use) is deterministic given the same profile blob, but the blob itself differs per CI run |
| Build host paths embedded in debug info | DWARF/PDB | Low | `/PATHMAP:` or `-fdebug-prefix-map=` &mdash; not yet enabled |
| `mini_installer.exe` setup compression | Final installer | Cosmetic | 7-Zip stage; could pin compression level |

## Reproduction recipe (best effort, today)

This is the recipe we expect to converge in the v0.3 timeframe.

```pwsh
# 1. Match the toolchain (see docs/toolchain.md)
# 2. Clone Vigil at the target tag
git clone --recurse-submodules --branch <tag> https://github.com/SysAdminDoc/Vigil.git
cd Vigil

# 3. Run build.py with the same args CI uses for that arch
python build.py            # x64; for x86 add --x86; for arm64 add --arm

# 4. Run package.py
python package.py

# 5. Compare against the published release artifact
$theirs = 'build/<official-installer>.exe'
$ours   = 'build/<your-installer>.exe'
fc /b $theirs $ours | Select-Object -First 50
```

If you see differences only in regions corresponding to the table above, the build
is "morally reproducible." If you see differences in code regions, file an issue.

## Toolchain attestation

Until [`docs/toolchain.md`](toolchain.md) has been turned into a machine-readable
SBOM with hash attestations, reproducibility depends on running the same VS / clang
/ rustc *versions* but not the same *bits*. This is the largest open gap.

Tracking: roadmap `N10` (this doc), `N9` (artifact provenance).
