# X1 — Manifest V2 retention patch set

**Status:** design doc; **BLOCKED-no-toolchain** for implementation in this
environment. Requires a Chromium source checkout to land patches against.

## Goal

Chrome 138 was the last stable Chromium milestone supporting Manifest V2
extensions; Chrome 139 (June 2025 branch) removed the runtime and the
`ExtensionManifestV2Availability` enterprise policy. Vigil &mdash; whose entire
positioning is "the un-Chrome that lets uBlock Origin keep working" &mdash; must
carry a patch set that re-enables MV2 against every Chromium bump.

Prior art that ships MV2 retention today: **Brave**, **Thorium**
(M138.0.7204.300, Jan 2026 release), **Cromite**, **Supermium**.

## Scope

Re-enable Manifest V2 extension loading and runtime services. Specifically:

1. Restore the `MANIFEST_V2_DEPRECATION_*` feature flags as available and default-enabled.
2. Restore `chrome.webRequest.onBeforeRequest` blocking listener registration for MV2.
3. Restore `manifest_version: 2` as a valid value in `extensions/common/manifest_constants.cc`.
4. Re-enable the `chrome_url_overrides` field for MV2.
5. Re-enable `background.scripts` (the MV2 background page) parsing.
6. Restore the `extension::kManifestV2Availability` policy enum and its plumbing.

## Files to patch (per Chromium 145)

The MV2-removal happened in a series of CLs:
- `extensions/common/manifest.cc` &mdash; `kIsManifestV2Allowed` checks
- `extensions/common/features/feature.cc` &mdash; `MANIFEST_V2_DEPRECATION` feature gate
- `extensions/browser/extension_prefs.cc` &mdash; disable-reason
  `DISABLE_UNSUPPORTED_MANIFEST_VERSION`
- `chrome/browser/extensions/manifest_v2_experiment_manager.{h,cc}` &mdash; entire file
  may be deletable or short-circuited
- `chrome/browser/policy/configuration_policy_handler_list_factory.cc` &mdash;
  restore the `ExtensionManifestV2Availability` handler
- `extensions/browser/api/web_request/web_request_api.cc` &mdash; restore the
  blocking-listener path when manifest_version &le; 2

Reference patches:
- Thorium: <https://github.com/Alex313031/thorium/commit/HEAD?path=src/extensions>
  (find commits referencing `manifest_v2`)
- Brave: `src/brave/chromium_src/extensions/` overrides
- Cromite: `docs/FEATURES.md` documents the patches landed

## Implementation plan

1. **Inventory the upstream removal commits** for the targeted milestone:
   ```
   git log --oneline --all -- '*manifest_v2*' \
     '*manifest_v2_experiment*' \
     extensions/common/manifest.cc
   ```
2. **Cherry-pick the inverse** of each removal commit into the Vigil patch set
   under `patches/ungoogled-chromium/windows/mv2-keep-alive/<seq>.patch`.
3. **Add the patch series prefix** to `patches/series`. Convention: prefix with
   `mv2-keep-alive/` and order from leaves (constants) up to integrations.
4. **Add an enterprise policy** `VigilManifestV2Availability` in `admx/vigil.admx`
   mirroring Chrome's `ExtensionManifestV2Availability` semantics (values:
   `default`, `disabled`, `enabled`, `enabled_for_force_installed`).
5. **Document the per-milestone diff** in `docs/design/X1-mv2-retention.md`
   (this file), updating the file list whenever upstream shapes change.

## Verification

- `chrome --version` should succeed and the resulting `chrome.exe` should run.
- `chrome://extensions` should load uBlock Origin v1.x.x (MV2) without a
  "deprecated manifest version" warning.
- `chrome.webRequest.onBeforeRequest` with `["blocking"]` registers without
  throwing.
- The `smoke_test.py` step that checks bundled uBO version inspects the
  manifest's `manifest_version` field; assert it equals `2`.

## Risks

- **Per-milestone churn.** Each Chromium bump touches one or more of the
  patched files; expect 30&ndash;90 minutes of rebase work per bump.
- **Upstream complete-removal.** If Chromium eventually deletes the MV2 code
  paths entirely (rather than gating them behind feature flags), the patch
  size explodes. Mitigation: switch to network-layer adblock via `adblock-rust`
  before that happens. See [`L4`](../../ROADMAP.md) (Later tier).
- **CRX install path.** uBO is shipped via `setup_extensions.py`'s external
  extensions JSON, which already works; this patch set only re-enables the
  runtime path that the loaded extension exercises.

## Written MV2 Policy doc (publish at v0.3)

Body:

> Vigil retains Manifest V2 extension support for as long as the upstream
> Chromium source can be reasonably patched to keep it running. We commit to:
>
> 1. Tracking each Chromium stable bump within seven days.
> 2. Publishing a per-bump diff against this MV2 patch set in our release notes.
> 3. Triggering a public migration plan no later than 60 days before the
>    earliest forecast date at which the patch set becomes infeasible
>    (compile failures we cannot fix in &lt;1 day of focused work).
> 4. The migration plan defaults to: bundle uBlock Origin's `lite` MV3
>    variant as the user-visible blocker, and rely on `adblock-rust` at the
>    network layer for parity with current MV2 capabilities.

Tracking: ROADMAP `X1`, `L4` (engine-layer adblock).
