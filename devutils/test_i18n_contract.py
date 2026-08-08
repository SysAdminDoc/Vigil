import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KEY_PATTERN = re.compile(r"data-i18n(?:-[a-z-]+)?=\"([^\"]+)\"")
JS_KEY_PATTERN = re.compile(r"\bt\(\s*['\"]([^'\"]+)")
MANIFEST_KEY_PATTERN = re.compile(r"__MSG_([A-Za-z0-9_]+)__")
FALLBACK_KEY_PATTERN = re.compile(r"^\s+([A-Za-z][A-Za-z0-9_]*):", re.MULTILINE)


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def manifest(extension):
    return json.loads(read(f"{extension}/manifest.json"))


def locale_messages(extension):
    return json.loads(read(f"{extension}/_locales/en/messages.json"))


def assert_extension_locale(extension, html_name, javascript_names):
    manifest_data = manifest(extension)
    messages = locale_messages(extension)
    helper = read(f"{extension}/i18n.js")
    html = read(f"{extension}/{html_name}")
    javascript = "\n".join(read(f"{extension}/{name}") for name in javascript_names)

    assert manifest_data["default_locale"] == "en"
    assert messages
    assert all(entry.get("message") for entry in messages.values())
    locale_keys = set(messages)
    fallback_keys = set(FALLBACK_KEY_PATTERN.findall(helper))
    assert locale_keys == fallback_keys
    referenced = set(KEY_PATTERN.findall(html))
    referenced.update(JS_KEY_PATTERN.findall(javascript))
    referenced.update(MANIFEST_KEY_PATTERN.findall(json.dumps(manifest_data)))
    assert referenced <= locale_keys, sorted(referenced - locale_keys)
    assert "fetch(" not in helper
    assert html.index('src="i18n.js"') < html.index(
        'src="newtab.js"' if extension == "ntp-extension" else 'src="palette.js"'
    )


def test_ntp_locale_has_fallbacks_for_static_and_dynamic_ui():
    assert_extension_locale("ntp-extension", "newtab.html", ["newtab.js"])


def test_palette_locale_has_fallbacks_for_page_and_service_worker_ui():
    assert_extension_locale(
        "palette-extension",
        "palette.html",
        ["background.js", "palette.js"],
    )
