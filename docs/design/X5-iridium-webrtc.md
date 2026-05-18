# X5 — Iridium WebRTC hardening backport

**Status:** design doc; **BLOCKED-no-toolchain**. Requires Chromium source.

## Goal

Backport three small, network-layer-only patches from
[Iridium Browser](https://github.com/iridium-browser/tracker/wiki/Differences-between-Iridium-and-Chromium)
that harden WebRTC against passive identity tracking. None of these are
Web-API spoofing &mdash; the safe kind of fingerprinting defense.

## Three patches

### 1. Per-connection WebRTC identity (vs. 30-day reuse)

Chromium currently reuses a single WebRTC identity across all calls for 30
days. Iridium replaces this with a per-connection identity, regenerated each
time `RTCPeerConnection` opens.

**Files:** `content/browser/webrtc/webrtc_internals.cc`,
`third_party/webrtc/pc/peer_connection.cc`, and the `IdentityService` plumbing
in `services/webrtc/`.

**Iridium reference:** the patch is in their consolidated
`0100_iridium-browser.diff` &mdash; grep for `identity_request`.

### 2. Fresh ECDHE keypair per connection

Chromium's WebRTC DTLS implementation caches the ECDHE keypair across
connections. Iridium regenerates per-connection. Tiny CPU cost, eliminates
the keypair as a tracking surface.

**Files:** `third_party/webrtc/pc/dtls_transport.cc` (or equivalent in the
current milestone).

### 3. RSA self-signed certificate keysize 2048 (was 1024)

Default DTLS-SRTP cert is RSA-1024; Iridium raises to 2048. A simple constant
change.

**Files:** `third_party/webrtc/rtc_base/openssl_certificate.cc` &mdash; the
`kDefaultRsaKeySize` constant.

## Implementation plan

1. Extract each Iridium patch from their consolidated diff.
2. Rebase against current Chromium milestone (the WebRTC source has moved
   files; targets above are approximate &mdash; verify with `git log -- '*webrtc*'`).
3. Land as three separate patches under
   `patches/ungoogled-chromium/windows/iridium-webrtc/<seq>.patch`.
4. Add to `patches/series` in the order shown.

## Verification

- Open a WebRTC test page like `webrtc.org/getting-started/peer-connections`
  twice in a row; capture the DTLS handshake with Wireshark (or
  `chrome://webrtc-internals`).
- Confirm the certificate fingerprint differs between the two captures (per-
  connection identity).
- Confirm `RSA 2048` in the cert (vs. `RSA 1024`).
- Run `chrome://webrtc-internals` and verify no regression in normal call
  setup time (&lt;100ms additional handshake overhead expected).

## Attribution

All three patches originate from
<https://github.com/iridium-browser/iridium-browser-windows> &mdash;
copyright the Iridium team, license inherited from BSD-3-Clause Chromium.
Vigil patches must carry the Iridium copyright header verbatim.

## Risks

- WebRTC source-tree churn is high. Expect to re-cut all three patches every
  4&ndash;6 Chromium milestones.
- Per-connection identity may break "remember this user" features in some
  enterprise WebRTC apps. Acceptable: Vigil's audience expects this.
- DTLS-SRTP 2048-bit cert generation adds ~50ms to the first call. Negligible.
