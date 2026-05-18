# X4 — Sideload-without-developer-mode-warning

**Status:** design doc; **BLOCKED-no-toolchain**. Requires Chromium source.

## Goal

Allow signed CRX from a Vigil-trusted publisher key list to install via the
file system without showing the "Extensions in developer mode pose a
security risk" banner that fires on Chromium startup when any unpacked /
sideloaded extension is detected.

Carried in `patches/series` since `v0.1`; this design doc records the patch
intent so it survives Chromium bumps.

## Files to patch (per Chromium 145)

- `chrome/browser/ui/views/extensions/extension_message_bubble_view_factory.cc`
  &mdash; suppress `kExtensionsDevModeWarning` when the loaded extension's
  install location is `EXTERNAL_POLICY` or its public key matches the
  Vigil-trusted publisher list.
- `chrome/browser/extensions/extension_management.cc` &mdash; new method
  `IsVigilTrustedPublisher(const std::string& public_key_b64)` returning
  true for keys listed in a build-time-baked allowlist.
- `chrome/browser/extensions/external_provider_impl.cc` &mdash; treat
  `EXTERNAL_PREF` (`default_extensions/<id>.json`) entries as policy-managed
  (suppresses warning) when the manifest `key` is on the allowlist.

## Publisher allowlist

`chromium_src/chrome/browser/extensions/vigil_trusted_publishers.cc` ships a
small `std::array<const char* const, N>` of base64-encoded DER public-key
prefixes. v0.2 contents (only when this patch lands):

- uBlock Origin's CWS public key (the well-known one matching
  `cjpalhdlnbpafiamejdnhcphjbkeiagm`)
- Vigil NTP extension's public key (baked by `tools/install_ntp_extension.py`
  at first build)

Adding to the list is a code change; we deliberately don't expose runtime
extension of the list via UI (that would defeat the purpose).

## Verification

After applying the patch:
- Boot Vigil with bundled uBO and Vigil NTP staged. The dev-mode-warning
  bubble does **not** appear.
- Boot Vigil with an *additional* unpacked extension dragged into
  `chrome://extensions`. The bubble **does** appear (that one isn't on the
  trust list).
- `chrome://policy` shows the loaded extensions with `Source: External Pref`
  for the trusted ones.

## Risks

- **Security: forgery of the `key` field.** Anyone can put any base64 string
  in a manifest's `key`. Mitigation: we compare against the *whole* trusted
  key, not a prefix; brute-forcing a SHA-256 collision is infeasible.
- **Upstream removes `EXTERNAL_PREF`.** This is the install-location path
  that `setup_extensions.py` already uses; if upstream changes it we lose
  uBO bundling, which is much bigger than this patch. Track separately.
