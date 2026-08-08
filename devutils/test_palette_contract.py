from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def test_palette_exposes_combobox_and_listbox_semantics():
    html = read("palette-extension/palette.html")
    source = read("palette-extension/palette.js")

    for marker in (
        'role="dialog"',
        'aria-modal="true"',
        'role="combobox"',
        'aria-controls="results"',
        'aria-autocomplete="list"',
        'aria-expanded="false"',
        'aria-haspopup="listbox"',
        'role="listbox"',
        'role="status"',
        'aria-live="polite"',
    ):
        assert marker in html
    for marker in (
        "row.setAttribute('role', 'option')",
        "row.setAttribute('aria-selected', String(index === selectedIndex))",
        "queryInput.setAttribute('aria-activedescendant'",
        "queryInput.setAttribute('aria-expanded', 'true')",
        "queryInput.setAttribute('aria-expanded', 'false')",
        "queryInput.setAttribute('aria-busy', 'true')",
    ):
        assert marker in source


def test_palette_latest_query_wins_and_errors_are_retryable():
    source = read("palette-extension/palette.js")

    assert "let searchSequence = 0" in source
    assert "const sequence = ++searchSequence" in source
    assert source.count("if (sequence !== searchSequence) return;") == 1
    assert "if (sequence === searchSequence)" in source
    assert "clearTimeout(searchTimer)" in source
    assert "Palette data is unavailable. Press Enter to retry." in source
    assert "event.key === 'Enter' && searchError" in source
    assert "queryInput.removeAttribute('aria-busy')" in source


def test_palette_focus_bridge_and_browser_owned_fallback_are_bounded():
    content = read("palette-extension/content.js")
    palette = read("palette-extension/palette.js")
    background = read("palette-extension/background.js")

    for marker in (
        "let previousFocus = null",
        "document.activeElement",
        "restoreFocus()",
        "event.source !== frame.contentWindow",
        "event.origin !== extensionOrigin",
        "window.parent.postMessage",
        "parentOrigin",
        "event.source !== window.parent",
        "event.origin !== parentOrigin",
    ):
        assert marker in content or marker in palette
    for marker in (
        "if (tab.url && /^https?:/i.test(tab.url))",
        "chrome.scripting.executeScript",
        "openPaletteTab(tab.id)",
        "chrome.runtime.getURL(`palette.html${query}`)",
    ):
        assert marker in background
