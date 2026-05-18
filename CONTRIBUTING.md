# Contributing to Vigil

Thanks for wanting to contribute. Vigil is a small project run on a tight philosophy
(see [ROADMAP.md](ROADMAP.md) &mdash; Charter &amp; non-goals). Reading that first will save
both of us time.

## Quick rules

1. **Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) before opening a PR.** Knowing
   when to use an overlay vs. a patch vs. an `initial_preferences` change is the entire
   skill of maintaining this fork.
2. **Don't introduce telemetry.** No analytics, no auto-pings, no install-source
   referral codes. Build-time GitHub-Releases fetches (uBO, ungoogled patches) are not
   telemetry; they happen on the build host, not on the user's machine.
3. **Don't introduce features from the [Rejected list](ROADMAP.md#rejected--explicit-non-goals).**
   Crypto, AI chatbots, integrated VPN-as-a-service, etc. If you think a rejected item
   should be reconsidered, open an issue first with the argument; don't open a PR.
4. **No PR is "just a bump."** Bumping Chromium versions triggers patch and overlay
   re-validation. See "Bumping Chromium" below.
5. **Sign your commits.** GPG / SSH commit signing is enforced on `master`.

## Repo layout

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full map. Briefly:

| Path | What | When to edit |
|---|---|---|
| [`branding.json`](branding.json) | Browser name, company, URLs | Re-brand, never on PRs |
| [`branding/`](branding/) | Icons + icon generator | Adding/regenerating icons |
| [`initial_preferences`](initial_preferences) | First-run pref dictionary | Changing defaults |
| [`chromium_src/`](chromium_src/) | Brave-style file overlays | UI / `chrome://` page changes |
| [`patches/`](patches/) | Vigil-Windows-specific patch series | C++ behavior changes |
| [`patches/series`](patches/series) | Patch apply order | When adding/removing a patch |
| [`ntp-extension/`](ntp-extension/) | Bundled new-tab-page extension | NTP UI changes |
| [`setup_extensions.py`](setup_extensions.py) | Builds the bundled-uBO blob | Pre-installed extension changes |
| [`apply_overlays.py`](apply_overlays.py) | Glues `chromium_src/` into source tree | Overlay system itself |
| [`build.py`](build.py) / [`package.py`](package.py) | Build + package entrypoints | Build pipeline |
| [`.github/workflows/`](.github/workflows/) | CI | Pipeline plumbing |
| [`admx/`](admx/) | Group Policy templates for IT admins | Adding policies |
| [`kiosk/`](kiosk/) | Vigil-Kiosk variant | Kiosk-mode-specific |
| [`dist/`](dist/) | winget / Scoop / Chocolatey manifests | Release publishing |
| [`docs/`](docs/) | Long-form docs &amp; design notes | New design docs, build docs |

## Picking the right change layer

```
                  +--------------------------------------------+
                  |  Goal: change a Chromium default behavior  |
                  +-----------------+--------------------------+
                                    |
                +-------------------+------------------+
                |                                      |
       Is it a user pref or a               Is it a UI string or
       distribution-level default?           a chrome:// page?
                |                                      |
                v                                      v
       Edit initial_preferences               Drop a file in chromium_src/
       (validate with python -c              mirroring the upstream path
       'import json; json.load(open(...))')   (apply_overlays.py picks it up)
                |                                      |
                v                                      v
       Is it a runtime preference            Compile fails after a Chromium
       Chromium can override via              bump? Re-cut the overlay against
       chrome://settings?                     the new upstream file. Don't
       --> use chromium_src/ to lock          fight the compiler with a patch
           the UI toggle                      unless you must.

       Is it deeper than that --
       compiled C++ behavior, an
       __attribute__, a build flag,
       or upstream code we want gone?
                |
                v
       Write a quilt-format patch under
       patches/ungoogled-chromium/windows/
       and add it to patches/series.
       Brave/Cromite/Iridium are reference
       projects; copy from them with attribution.
```

Three rules of thumb:

1. **Overlay over patch.** Patches break on every Chromium rebase; overlays just fail
   to compile, which is a faster signal. Brave's
   [patching-chromium wiki](https://github.com/brave/brave-browser/wiki/Patching-Chromium)
   is the canonical statement of this.
2. **Pref over overlay.** If `initial_preferences` can express it, do it there. Prefs
   survive Chromium bumps cost-free.
3. **Patch only what an overlay genuinely cannot reach.** Examples: linker flags,
   patches that delete generated-code references, anything where you need to
   `#if defined(...)` around upstream code.

## Bumping Chromium

1. Update the upstream ungoogled-chromium submodule pointer (see
   [`.gitmodules`](.gitmodules)).
2. Verify `patches/series` still applies cleanly. If not, fix or drop patches
   one-by-one and document the change in the CHANGELOG under the new version.
3. Re-check every file under `chromium_src/` &mdash; the corresponding upstream file
   may have changed shape. Compile is the test.
4. Re-run the smoke test (`devutils/smoke_test.py`).
5. Update `revision.txt` and `branding.json` if applicable.
6. Tag as `v<vigil>-c<chromium>`. CI takes over.

## PR conventions

- One concern per PR. A Chromium bump and a feature change are two PRs.
- Title format: `<area>: <imperative phrase>` &mdash; e.g.
  `ntp: fix shortcut favicon overflow`, `build: bump Chromium 145 &rarr; 146`,
  `prefs: enable HTTPS-First Balanced`.
- Body must answer: **what changed, why it changed, what was tested.** "Tested" can
  be "smoke test passes" or "manual run for 5 minutes" &mdash; just say.
- Reference the roadmap item ID (`N1`, `X10`, etc.) where applicable.
- Commit message body is fine to be terse, but the PR description carries the
  reasoning that future maintainers will read.

## Local testing without a full Chromium build

You don't need a 100 GB Chromium tree to validate most contributions:

- **`initial_preferences` JSON**: `python -c "import json; json.load(open('initial_preferences'))"`
- **Patches**: `quilt push -a` against a stripped Chromium tarball.
- **Overlay layout**: `python apply_overlays.py` against a stub source tree; check that
  files land in the expected paths.
- **NTP extension**: `chrome --load-extension=./ntp-extension/` in your daily Chrome.
- **ADMX**: load `admx/vigil.admx` into the local Group Policy editor and verify the
  policy tree renders.
- **Smoke test**: `python devutils/smoke_test.py --installer build/<installer>.exe`.

A full build is only required to land patches/overlays that touch C++ or
generated-resource files. See [`docs/build-environment.md`](docs/build-environment.md)
for the build-host floor.

## Reporting security issues

Don't open a public issue. Email the maintainer at the address listed in
[`branding.json`](branding.json) (`support_url` &rarr; the GitHub issue form
*is* the right place for non-sensitive bugs; for security, follow the GitHub
"Report a security advisory" link on the repo).

## License

By contributing you agree your contributions are licensed under
[BSD-3-Clause](LICENSE), matching the rest of the project.
