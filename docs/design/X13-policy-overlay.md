# X13 — chrome://policy themed overlay

**Status:** scaffolded; needs one tiny patch to wire up.

## What ships in this commit

- `chromium_src/chrome/browser/resources/policy/vigil_policy_theme.css` &mdash; the
  Vigil dark theme for the policy page, matching the rest of the chrome://
  overlays (settings, flags, history, etc.).

## What still needs to land

The Chromium policy UI is built from a Polymer template at
`chrome/browser/resources/policy/policy_ui.html`. To activate the CSS above, the
template needs a one-line `<link>` reference. Because the upstream file is
regenerated frequently and varies between milestones, we add it as a small
Vigil-side patch rather than a full overlay.

### Patch sketch (drop into `patches/ungoogled-chromium/windows/`)

```patch
--- a/chrome/browser/resources/policy/policy_ui.html
+++ b/chrome/browser/resources/policy/policy_ui.html
@@ -<LINE>,<COUNT> +<LINE>,<COUNT> @@
     <link rel="stylesheet" href="chrome://resources/css/md_colors.css">
+    <link rel="stylesheet" href="chrome://resources/vigil_policy_theme.css">
     <link rel="stylesheet" href="policy_shared.css">
```

And add `chrome/browser/resources/policy/vigil_policy_theme.css` to the
appropriate `BUILD.gn` resource list so it ships as a resource pack entry.
The smallest path is `chrome/browser/resources/policy/BUILD.gn`:

```patch
   "policy_shared.css",
+  "vigil_policy_theme.css",
   "policy_ui.html",
```

Register the file path in `chrome://resources/` if needed (per Chromium's
WebUI conventions for cross-WebUI shared resources, which the
`chrome://resources/vigil_policy_theme.css` href above relies on).

Once both patches land, the theme activates on the next build. The CSS file
itself is already in place via the existing `chromium_src/` overlay system.

## Why this isn't a full overlay

The other Vigil overlays (`settings.html`, `flags.html`, `history.html`, ...)
work because each one is a relatively-stable shell file that the upstream
team rarely touches. `policy_ui.html` and its dependencies churn more often
because the policy page is generated from the Chromium-wide policy schema.
Maintaining a full overlay would create rebase pain on every Chromium bump.

The CSS-injection-via-patch approach is what Brave and Cromite use for the
same problem, and it keeps the per-bump diff to a single line.

## Verification

After applying the patch and rebuilding:

1. Launch the built `chrome.exe`.
2. Open `chrome://policy`.
3. Confirm the header bar is `#111827` (Vigil surface), section headers are
   the Vigil-accent blue uppercase 10-px-letterspacing style, and policy
   value cells render in Cascadia Code monospace.
4. Switch the OS theme to light; confirm light mode loses the dark surface
   but keeps the accent action-button styling.
