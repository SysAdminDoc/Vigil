#!/usr/bin/env python3
"""Export and import a versioned, local-only Vigil profile snapshot.

The tool accepts the JSON returned by ``chrome.storage.local.get()`` for the
NTP settings and ``chrome.bookmarks.getTree()`` for bookmarks. It intentionally
does not read Chromium profile databases or contact a service. Only the
selected Vigil settings, shortcuts, notes, and HTTP(S) bookmarks are carried
forward; passwords, cookies, and history are rejected.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


SCHEMA = "vigil-profile"
SCHEMA_VERSION = 1
SETTINGS_KEY = "vigil_ntp_settings"
MAX_SHORTCUTS = 12
MAX_SHORTCUT_NAME = 80
MAX_URL_LENGTH = 2048
MAX_NOTES_LENGTH = 10000
MAX_CITY_LENGTH = 100
MAX_BOOKMARK_TITLE = 512
MAX_BOOKMARK_NODES = 10000
MAX_BOOKMARK_DEPTH = 32
MAX_RSS_FEEDS = 3
MAX_RSS_FEED_LENGTH = 2048
FORBIDDEN_FIELDS = frozenset({"passwords", "cookies", "history"})
ROOT_IDS = frozenset({"1", "2", "3"})
SETTING_BOOLEAN_KEYS = (
    "showClock",
    "use24h",
    "showShortcuts",
    "showSearch",
)
WIDGET_BOOLEAN_KEYS = ("notes", "topSites", "bookmarks", "weather", "rss")


class TransferError(ValueError):
    """Raised when a snapshot cannot be safely imported or exported."""


def _read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TransferError(f"could not read {label}: {path}: {exc}") from exc


def _write_json_atomic(path: Path, value: Any) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.stage-", dir=path.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _reject_forbidden_fields(value: Any, location: str = "document") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_FIELDS:
                raise TransferError(
                    f"{location}.{key} is not importable; passwords, cookies, and history are excluded"
                )
            _reject_forbidden_fields(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_fields(child, f"{location}[{index}]")


def _text(value: Any, limit: int, *, trim: bool = True) -> str:
    if not isinstance(value, str):
        raise TransferError("expected a string value")
    return value.strip()[:limit] if trim else value[:limit]


def _web_url(value: Any, *, limit: int = MAX_URL_LENGTH) -> str:
    url = _text(value, limit)
    if not url:
        raise TransferError("bookmark and shortcut URLs cannot be empty")
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        username = parsed.username
        password = parsed.password
    except ValueError as exc:
        raise TransferError(f"invalid web URL: {url!r}") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        raise TransferError(f"only HTTP(S) URLs can be migrated: {url!r}")
    if username is not None or password is not None:
        raise TransferError("URLs with embedded credentials cannot be migrated")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, parsed.query, parsed.fragment))


def _settings_value(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TransferError("NTP settings must be a JSON object")
    if SETTINGS_KEY in value:
        value = value[SETTINGS_KEY]
    if not isinstance(value, dict):
        raise TransferError(f"{SETTINGS_KEY} must contain a JSON object")
    _reject_forbidden_fields(value, "settings")

    selected: dict[str, Any] = {}
    for key in SETTING_BOOLEAN_KEYS:
        if key in value:
            if not isinstance(value[key], bool):
                raise TransferError(f"settings.{key} must be boolean")
            selected[key] = value[key]

    if "shortcuts" in value:
        shortcuts = value["shortcuts"]
        if not isinstance(shortcuts, list):
            raise TransferError("settings.shortcuts must be an array")
        selected["shortcuts"] = []
        for index, shortcut in enumerate(shortcuts[:MAX_SHORTCUTS]):
            if not isinstance(shortcut, dict):
                raise TransferError(f"settings.shortcuts[{index}] must be an object")
            name = _text(shortcut.get("name", ""), MAX_SHORTCUT_NAME)
            selected["shortcuts"].append({
                "name": name,
                "url": _web_url(shortcut.get("url")),
            })

    if "widgets" in value:
        widgets = value["widgets"]
        if not isinstance(widgets, dict):
            raise TransferError("settings.widgets must be an object")
        selected["widgets"] = {}
        for key in WIDGET_BOOLEAN_KEYS:
            if key in widgets:
                if not isinstance(widgets[key], bool):
                    raise TransferError(f"settings.widgets.{key} must be boolean")
                selected["widgets"][key] = widgets[key]

    text_fields = (
        ("widgetNotes", MAX_NOTES_LENGTH, False),
        ("bookmarkFolderId", 128, True),
        ("weatherCity", MAX_CITY_LENGTH, True),
    )
    for key, limit, trim in text_fields:
        if key in value:
            selected[key] = _text(value[key], limit, trim=trim)

    if "rssFeeds" in value:
        feeds = value["rssFeeds"]
        if not isinstance(feeds, list):
            raise TransferError("settings.rssFeeds must be an array")
        selected["rssFeeds"] = []
        for feed in feeds[:MAX_RSS_FEEDS]:
            normalized = _web_url(feed, limit=MAX_RSS_FEED_LENGTH)
            if not normalized.startswith("https://"):
                raise TransferError("only HTTPS RSS feeds can be migrated")
            if normalized not in selected["rssFeeds"]:
                selected["rssFeeds"].append(normalized)

    return selected


def _bookmark_node(value: Any, *, depth: int, count: list[int], root: bool = False) -> dict[str, Any]:
    if depth > MAX_BOOKMARK_DEPTH:
        raise TransferError(f"bookmark tree exceeds {MAX_BOOKMARK_DEPTH} levels")
    if not isinstance(value, dict):
        raise TransferError("bookmark nodes must be objects")
    node_type = value.get("type")
    if node_type not in {"folder", "url"}:
        raise TransferError(f"unsupported bookmark node type: {node_type!r}")
    count[0] += 1
    if count[0] > MAX_BOOKMARK_NODES:
        raise TransferError(f"bookmark tree exceeds {MAX_BOOKMARK_NODES} nodes")
    title = _text(value.get("title", ""), MAX_BOOKMARK_TITLE, trim=False)
    if node_type == "url":
        return {"type": "url", "title": title, "url": _web_url(value.get("url"))}

    children = value.get("children")
    if not isinstance(children, list):
        raise TransferError("bookmark folders must contain a children array")
    result: dict[str, Any] = {
        "type": "folder",
        "title": title,
        "children": [
            _bookmark_node(child, depth=depth + 1, count=count)
            for child in children
        ],
    }
    if root:
        root_key = value.get("root_key", value.get("id"))
        if root_key is not None and str(root_key) in ROOT_IDS:
            result["root_key"] = str(root_key)
    return result


def _bookmark_tree(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise TransferError("bookmarks must be the array returned by chrome.bookmarks.getTree()")
    count = [0]
    return [
        _bookmark_node(node, depth=0, count=count, root=True)
        for node in value
    ]


def build_export(settings: Any, bookmarks: Any) -> dict[str, Any]:
    """Return a sanitized, versioned export document."""

    _reject_forbidden_fields(settings, "settings")
    _reject_forbidden_fields(bookmarks, "bookmarks")
    return {
        "schema": SCHEMA,
        "version": SCHEMA_VERSION,
        "settings": _settings_value(settings),
        "bookmarks": _bookmark_tree(bookmarks),
    }


def validate_export(value: Any) -> dict[str, Any]:
    """Validate and sanitize an import document without side effects."""

    if not isinstance(value, dict):
        raise TransferError("profile export must be a JSON object")
    _reject_forbidden_fields(value)
    allowed = {"schema", "version", "settings", "bookmarks"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise TransferError(f"unsupported profile export fields: {', '.join(unknown)}")
    if value.get("schema") != SCHEMA or value.get("version") != SCHEMA_VERSION:
        raise TransferError(f"unsupported profile export schema/version; expected {SCHEMA} v{SCHEMA_VERSION}")
    if "settings" not in value or "bookmarks" not in value:
        raise TransferError("profile export must include settings and bookmarks")
    return {
        "schema": SCHEMA,
        "version": SCHEMA_VERSION,
        "settings": _settings_value(value["settings"]),
        "bookmarks": _bookmark_tree(value["bookmarks"]),
    }


def _url_key(url: str) -> str:
    return url.lower()


def _iter_urls(nodes: list[dict[str, Any]]):
    for node in nodes:
        if node["type"] == "url":
            yield node
        else:
            yield from _iter_urls(node["children"])


def _find_folder(children: list[dict[str, Any]], title: str) -> dict[str, Any] | None:
    return next(
        (
            node for node in children
            if node["type"] == "folder" and node["title"] == title
        ),
        None,
    )


def _root_match(incoming: dict[str, Any], current: list[dict[str, Any]]) -> dict[str, Any] | None:
    root_key = incoming.get("root_key")
    if root_key is not None:
        match = next((node for node in current if node.get("root_key") == root_key), None)
        if match is not None:
            return match
    return next((node for node in current if node["title"] == incoming["title"]), None)


def _merge_bookmark_children(
    target: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
    existing_urls: set[str],
    conflicts: list[dict[str, str]],
    stats: dict[str, int],
    path: str,
) -> None:
    for node in incoming:
        node_path = f"{path}/{node['title']}" if path else node["title"]
        if node["type"] == "url":
            key = _url_key(node["url"])
            if key in existing_urls:
                stats["conflicts"] += 1
                if len(conflicts) < 100:
                    conflicts.append({"path": node_path, "url": node["url"]})
                continue
            target.append(copy.deepcopy(node))
            existing_urls.add(key)
            stats["bookmarks_added"] += 1
            continue

        folder = _find_folder(target, node["title"])
        if folder is None:
            folder = {"type": "folder", "title": node["title"], "children": []}
            target.append(folder)
            stats["folders_added"] += 1
        _merge_bookmark_children(
            folder["children"],
            node["children"],
            existing_urls,
            conflicts,
            stats,
            node_path,
        )


def merge_profile(
    current_settings: Any,
    current_bookmarks: Any,
    imported: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """Merge selected settings and non-duplicate bookmarks into local data."""

    current_settings = _settings_value(current_settings)
    current_bookmarks = _bookmark_tree(current_bookmarks)
    imported = validate_export(imported)

    merged_settings = copy.deepcopy(current_settings)
    overwritten = []
    for key, value in imported["settings"].items():
        if key == "widgets":
            existing_widgets = merged_settings.setdefault("widgets", {})
            for widget, enabled in value.items():
                if widget in existing_widgets and existing_widgets[widget] != enabled:
                    overwritten.append(f"widgets.{widget}")
                existing_widgets[widget] = enabled
            continue
        if key in merged_settings and merged_settings[key] != value:
            overwritten.append(key)
        merged_settings[key] = copy.deepcopy(value)

    existing_urls = {
        _url_key(node["url"])
        for node in _iter_urls(current_bookmarks)
    }
    conflicts: list[dict[str, str]] = []
    stats = {
        "bookmarks_added": 0,
        "conflicts": 0,
        "folders_added": 0,
        "roots_missing": 0,
    }
    for incoming_root in imported["bookmarks"]:
        target_root = _root_match(incoming_root, current_bookmarks)
        if target_root is None:
            stats["roots_missing"] += 1
            continue
        _merge_bookmark_children(
            target_root["children"],
            incoming_root["children"],
            existing_urls,
            conflicts,
            stats,
            incoming_root["title"],
        )

    report = {
        "settings": {
            "imported_keys": sorted(imported["settings"]),
            "overwritten_keys": sorted(set(overwritten)),
        },
        "bookmarks": {
            **stats,
            "conflict_details": conflicts,
            "conflicts_omitted": max(0, stats["conflicts"] - len(conflicts)),
        },
        "excluded_fields": sorted(FORBIDDEN_FIELDS),
        "network": "not used",
    }
    return merged_settings, current_bookmarks, report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    export = subparsers.add_parser("export", help="write a sanitized local profile export")
    export.add_argument("--settings", type=Path, required=True)
    export.add_argument("--bookmarks", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)

    import_parser = subparsers.add_parser("import", help="preview or apply a local profile export")
    import_parser.add_argument("--input", type=Path, required=True)
    import_parser.add_argument("--current-settings", type=Path)
    import_parser.add_argument("--current-bookmarks", type=Path)
    import_parser.add_argument("--settings-output", type=Path)
    import_parser.add_argument("--bookmarks-output", type=Path)
    import_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report conflicts without writing either output",
    )
    return parser


def _run_export(args: argparse.Namespace) -> dict[str, Any]:
    settings = _read_json(args.settings, "settings snapshot")
    bookmarks = _read_json(args.bookmarks, "bookmark snapshot")
    document = build_export(settings, bookmarks)
    _write_json_atomic(args.output, document)
    return {
        "schema": SCHEMA,
        "version": SCHEMA_VERSION,
        "mode": "export",
        "output": str(args.output.resolve()),
        "settings_keys": sorted(document["settings"]),
        "bookmark_roots": len(document["bookmarks"]),
        "excluded_fields": sorted(FORBIDDEN_FIELDS),
        "network": "not used",
    }


def _run_import(args: argparse.Namespace) -> dict[str, Any]:
    imported = validate_export(_read_json(args.input, "profile export"))
    current_settings = (
        _read_json(args.current_settings, "current settings snapshot")
        if args.current_settings else {}
    )
    current_bookmarks = (
        _read_json(args.current_bookmarks, "current bookmark snapshot")
        if args.current_bookmarks else []
    )
    merged_settings, merged_bookmarks, report = merge_profile(
        current_settings,
        current_bookmarks,
        imported,
    )
    if not args.dry_run:
        if not args.settings_output and not args.bookmarks_output:
            raise TransferError(
                "import requires --dry-run or at least one output path"
            )
        if args.settings_output:
            _write_json_atomic(args.settings_output, merged_settings)
        if args.bookmarks_output:
            _write_json_atomic(args.bookmarks_output, merged_bookmarks)
    report.update({
        "schema": SCHEMA,
        "version": SCHEMA_VERSION,
        "mode": "dry-run" if args.dry_run else "import",
        "input": str(args.input.resolve()),
    })
    return report


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = _run_export(args) if args.command == "export" else _run_import(args)
    except (OSError, TransferError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
