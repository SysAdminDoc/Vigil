# X7 + X8 — Client-Hints strip + anti-fingerprinting "Strict" toggle

**Status:** design doc; **BLOCKED-no-toolchain** for the C++ patches.
`initial_preferences` pieces shipped in `0.2.0`.

## X7 — Strip Client Hints (UA-CH)

### Goal

UA-CH (User-Agent Client Hints) survived the October 2025 Privacy Sandbox
cull. It's a fingerprinting vector. Vigil sends a minimal, stable, Chrome-
indistinguishable UA-CH set by default; users override per-site via flag.

### Approach

Two pieces:

**1. Pref-level (already shipped in v0.2 `initial_preferences`):**
- `enable_do_not_track: true` already set; serves as the request signal.

**2. C++ patch (still needed):** override Chromium's default `Accept-CH`
response handling to ignore the hints list, AND truncate the outbound
`sec-ch-ua*` headers to a constant minimum.

### Files to patch (per Chromium 145)

- `services/network/url_loader_factory.cc` &mdash; intercept the request
  headers, strip `sec-ch-ua-arch`, `sec-ch-ua-bitness`, `sec-ch-ua-full-version`,
  `sec-ch-ua-full-version-list`, `sec-ch-ua-model`, `sec-ch-ua-platform-version`.
  Retain only `sec-ch-ua`, `sec-ch-ua-mobile`, `sec-ch-ua-platform`.
- `content/browser/client_hints/client_hints.cc` &mdash; clear the persistent
  `Accept-CH` cache; never persist a server's `Accept-CH` declaration.

### Verification

- Visit `https://browserleaks.com/client-hints` and confirm the
  high-entropy hints are missing.
- Inspect `chrome://settings/cookies/detail?site=https://example.com` and
  confirm no client-hint storage.

## X8 — Anti-fingerprinting "Strict" toggle

### Goal

A *single* user-facing toggle in `chrome://settings/privacy` that, when
enabled, applies a curated subset of Cromite's anti-fingerprint protections:

- Canvas readback noise (per-eTLD+1, per-session seed)
- Audio context noise (same seeding)
- Font enumeration limit (no `@font-face` system-font list)
- `navigator.hardwareConcurrency` bucketed to {2, 4, 8}
- `screen.availTop` / `availLeft` hidden (returns 0)
- `WebGL` `UNMASKED_VENDOR_WEBGL` / `UNMASKED_RENDERER_WEBGL` returns Vigil-
  constant strings
- `navigator.deviceMemory` bucketed to {2, 4, 8} GB

Off by default. Documented breakage list shown next to the toggle.

### Why "Strict" and not Mullvad-style uniform-fingerprint

Mullvad/Tor's approach is "all users appear identical." That requires
disabling many APIs (no WebGL, no font choice, etc.) and Tor's site of last
resort. Vigil's audience is sysadmins; they need a functional browser. We
explicitly *don't* aim for unique-fingerprint elimination &mdash; we aim for
"obvious tracker scripts won't fingerprint this profile distinctly across
sessions."

### Files to patch (per Chromium 145)

- `third_party/blink/renderer/core/html/canvas/canvas_rendering_context_2d.cc`
  &mdash; intercept `toDataURL`, `getImageData`, hook in noise.
- `third_party/blink/renderer/modules/webaudio/audio_buffer.cc` &mdash;
  intercept the AudioBuffer copy path.
- `third_party/blink/renderer/modules/webgl/webgl_rendering_context_base.cc`
  &mdash; intercept `getParameter` for the masked params.
- `third_party/blink/renderer/core/css/font_face_set.cc` &mdash; limit the
  enumeration to a Vigil-baseline 50-font allowlist.
- `third_party/blink/renderer/core/frame/navigator_concurrent_hardware.cc`
  &mdash; bucket the return value.
- `third_party/blink/renderer/core/frame/screen.cc` &mdash; clamp
  `availTop`/`availLeft` to 0.

Cromite's patches at <https://github.com/uazo/cromite/blob/master/docs/FEATURES.md>
list source files and can be lifted (MPL-2.0 with attribution).

### Toggle plumbing

A new pref `vigil.fingerprint_strict_mode_enabled` (default false). The
patches above read this pref via `Profile::GetPrefs()`. Add UI in
`chrome://settings/privacy` via a small overlay to the privacy section.

### Verification

With the toggle ON:
- `https://browserleaks.com/canvas` shows different hashes per session.
- `https://amiunique.org/` reports `hardwareConcurrency` as 4 (or another
  bucket value).
- `navigator.deviceMemory` returns 4 (bucket).
- WebGL renderer string is `Vigil` rather than the GPU name.

With the toggle OFF, all values match upstream Chromium.

### Risks

- Curated subset is opinionated. Document the list in
  `docs/anti-fingerprinting.md` (write at v0.3) so users know exactly what
  changes. Without this, users will report broken pages and we will not be
  able to bisect.
- Some sites (Cloudflare turnstile, anti-fraud) bot-block clients with
  canvas-noise patterns. Document the impact and provide a per-site
  exception via `chrome://settings/content/anti-fingerprint`.
