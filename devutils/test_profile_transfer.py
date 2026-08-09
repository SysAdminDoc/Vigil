import json
import subprocess
import sys
from pathlib import Path

import pytest

from devutils.profile_transfer import (
    TransferError,
    build_export,
    merge_profile,
    validate_export,
)


ROOT = Path(__file__).resolve().parents[1]


def settings_snapshot():
    return {
        "vigil_ntp_settings": {
            "schemaVersion": 1,
            "showClock": True,
            "use24h": True,
            "showShortcuts": True,
            "showSearch": False,
            "shortcuts": [{"name": "Docs", "url": "https://docs.example.test/path"}],
            "widgets": {"notes": True, "topSites": False, "bookmarks": True},
            "widgetNotes": "clinic handoff",
            "bookmarkFolderId": "42",
            "weatherCity": "Buffalo",
            "rssFeeds": ["https://example.test/feed.xml"],
        }
    }


def bookmark_tree():
    return [
        {
            "id": "1",
            "title": "Bookmarks bar",
            "type": "folder",
            "children": [
                {
                    "id": "7",
                    "title": "Vigil",
                    "type": "folder",
                    "children": [
                        {
                            "id": "8",
                            "title": "Docs",
                            "type": "url",
                            "url": "https://docs.example.test/path",
                            "dateAdded": 123,
                        }
                    ],
                }
            ],
        }
    ]


def test_export_is_versioned_and_contains_only_selected_local_data():
    document = build_export(settings_snapshot(), bookmark_tree())

    assert document["schema"] == "vigil-profile"
    assert document["version"] == 1
    assert document["settings"]["shortcuts"] == [
        {"name": "Docs", "url": "https://docs.example.test/path"}
    ]
    assert document["settings"]["widgetNotes"] == "clinic handoff"
    assert "schemaVersion" not in document["settings"]
    bookmark = document["bookmarks"][0]["children"][0]["children"][0]
    assert bookmark == {
        "type": "url",
        "title": "Docs",
        "url": "https://docs.example.test/path",
    }
    assert '"id"' not in json.dumps(document)
    assert "dateAdded" not in json.dumps(document)


def test_round_trip_merge_reports_conflict_and_adds_new_bookmark():
    imported = build_export(settings_snapshot(), bookmark_tree())
    current = [
        {
            "id": "1",
            "title": "Bookmarks bar",
            "type": "folder",
            "children": [
                {
                    "title": "Existing",
                    "type": "url",
                    "url": "https://existing.example.test/",
                }
            ],
        }
    ]
    imported["bookmarks"][0]["children"].append({
        "type": "url",
        "title": "New",
        "url": "https://new.example.test/",
    })

    merged_settings, merged_bookmarks, report = merge_profile(
        {"showClock": False, "widgets": {"notes": False}},
        current,
        imported,
    )

    assert merged_settings["showClock"] is True
    assert merged_settings["widgets"]["notes"] is True
    assert report["bookmarks"]["conflicts"] == 0
    assert report["bookmarks"]["bookmarks_added"] == 2
    assert "https://new.example.test/" in json.dumps(merged_bookmarks)

    second_settings, second_bookmarks, second_report = merge_profile(
        merged_settings,
        merged_bookmarks,
        imported,
    )
    assert second_settings == merged_settings
    assert second_bookmarks == merged_bookmarks
    assert second_report["bookmarks"]["conflicts"] == 2


@pytest.mark.parametrize(
    "document",
    [
        {"schema": "vigil-profile", "version": 2, "settings": {}, "bookmarks": []},
        {
            "schema": "vigil-profile",
            "version": 1,
            "settings": {},
            "bookmarks": [],
            "passwords": [],
        },
        {
            "schema": "vigil-profile",
            "version": 1,
            "settings": {},
            "bookmarks": [
                {"type": "folder", "title": "Bad", "children": [
                    {"type": "url", "title": "Script", "url": "javascript:alert(1)"}
                ]}
            ],
        },
    ],
)
def test_malformed_or_unsafe_imports_are_rejected(document):
    with pytest.raises(TransferError):
        validate_export(document)


def test_cli_export_and_dry_run_import_are_local_and_machine_readable(tmp_path):
    settings_path = tmp_path / "settings.json"
    bookmarks_path = tmp_path / "bookmarks.json"
    export_path = tmp_path / "vigil-profile.json"
    settings_path.write_text(json.dumps(settings_snapshot()), encoding="utf-8")
    bookmarks_path.write_text(json.dumps(bookmark_tree()), encoding="utf-8")

    exported = subprocess.run(
        [
            sys.executable,
            "devutils/profile_transfer.py",
            "export",
            "--settings",
            str(settings_path),
            "--bookmarks",
            str(bookmarks_path),
            "--output",
            str(export_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert exported.returncode == 0, exported.stderr
    assert json.loads(exported.stdout)["network"] == "not used"

    dry_run = subprocess.run(
        [
            sys.executable,
            "devutils/profile_transfer.py",
            "import",
            "--input",
            str(export_path),
            "--current-bookmarks",
            str(bookmarks_path),
            "--dry-run",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert dry_run.returncode == 0, dry_run.stderr
    report = json.loads(dry_run.stdout)
    assert report["mode"] == "dry-run"
    assert report["bookmarks"]["conflicts"] == 1
    assert not list(tmp_path.glob("*.stage-*"))


def test_profile_transfer_has_no_network_client_or_endpoint():
    source = (ROOT / "devutils" / "profile_transfer.py").read_text(encoding="utf-8")

    assert "urllib.request" not in source
    assert "requests" not in source
    assert "socket" not in source
