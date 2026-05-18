# X2 — AMO &rarr; CRX bridge

**Status:** design doc. **RESEARCH-phase.** Ship in v0.5 if feasible; reject
otherwise. No Chromium-source dependency at the bridge level &mdash; pure
tooling.

## Goal

Let users install a Firefox AMO extension (`.xpi`) inside Vigil without
operating in Chromium developer mode. The user-facing experience:

1. User clicks a `.xpi` link in Vigil.
2. Vigil intercepts the mime-type (`application/x-xpinstall`) and offers to
   convert.
3. Vigil unpacks the XPI, rewrites the `manifest.json` to the Chromium dialect
   where viable, re-packs as a CRX3 signed with a per-install Vigil key, and
   force-installs via the existing `ExtensionInstallForcelist` policy.

## Why this is hard

- CRX3 requires a Google-CWS-signed `.crx` for off-store install since Chrome
  75. Force-installed extensions via enterprise policy bypass the warning,
  which is the loophole we exploit.
- Many Firefox extensions use WebExtension APIs that have no Chromium
  counterpart (`browser.tabs.executeScript` MV2 nuance, `browser.menus`,
  etc.). The bridge is a *best-effort* tool, not a guarantee.
- Manifest dialect differences: `browser_specific_settings`, `applications`,
  `browser_action`/`page_action` (MV2) vs `action` (MV3), `host_permissions`
  scope, etc.

## Scope

**In scope (v0.5):**
- A `tools/xpi_to_crx.py` CLI that performs the conversion offline.
- Manifest rewrite rules for the common Firefox-only fields.
- CRX3 packaging using the existing `chromium_src/`-built `chrome.exe
  --pack-extension`.
- A Vigil mime-type handler that pipes XPI clicks through the converter.

**Out of scope:**
- Full WebExtension API shim layer. Extensions that depend on Firefox-only
  APIs will install but may not function. Document this in the UI.
- Automatic update via AMO's update channel. v0.5 conversions are one-shot.
  Auto-update via AMO would require re-signing on every update, which forces
  us to host the conversion service. Out of scope.

## Implementation plan

1. **`tools/xpi_to_crx.py`** (offline CLI):
   - Unzip the XPI to a temp dir.
   - Load `manifest.json`; map Firefox-only fields to Chromium equivalents
     using a deterministic rule table. Drop fields that can't be mapped and
     emit a warning list.
   - Re-pack with `chrome.exe --pack-extension=<dir>`; this generates a key
     pair on first run and a `.crx` on each invocation.
   - Output the `.crx` path and a JSON of warnings.
2. **Vigil mime-type handler**: a small overlay
   (`chromium_src/chrome/browser/download/...`) that intercepts
   `application/x-xpinstall` content-type downloads and pipes them to the
   converter (or prompts the user).
3. **Install UX**: a Vigil-themed page at `chrome://vigil-amo-install` that
   shows the warnings, lets the user proceed, and triggers
   `ExtensionInstallForcelist` registry write + reload of policy.

## Risks &amp; decision gates

- **Maintenance cost of the manifest rule table.** Mozilla and Google change
  the WebExtension API surface several times a year. Budget &le; 8 hours per
  Vigil release.
- **User confusion** when a converted extension installs but doesn't function.
  Mitigation: explicit warning page that names the Firefox-only APIs it uses,
  pulled from the manifest.
- **Legal**: each AMO extension's license governs redistribution. The bridge
  does the conversion on the user's machine, so we never redistribute. Note
  in the docs.

## Decision

Implement only if Mozilla does not ship a first-party Firefox-on-Chromium
solution by v0.5 (they will not), AND at least one user with an AMO-only
extension files a request. Don't speculate on the demand.
