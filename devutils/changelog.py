#!/usr/bin/env python3
"""Generate Keep-a-Changelog release sections from conventional git commits."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


COMMIT_RE = re.compile(
    r"^(?P<kind>feat|fix|perf|refactor|docs|test|build|ci|chore)"
    r"(?:\([^)]*\))?(?P<breaking>!)?:\s*(?P<subject>.+)$",
    re.IGNORECASE,
)
CATEGORY_ORDER = ("Added", "Changed", "Fixed", "Documentation", "Tests")


@dataclass(frozen=True)
class Commit:
    subject: str
    kind: str
    breaking: bool = False


def classify_commit(subject: str) -> Commit:
    """Normalize one commit subject into a changelog category source."""
    match = COMMIT_RE.match(subject.strip())
    if not match:
        return Commit(subject.strip(), "changed")
    return Commit(
        match.group("subject").strip(),
        match.group("kind").lower(),
        bool(match.group("breaking")),
    )


def category_for(commit: Commit) -> str:
    """Map conventional commit kinds to Keep-a-Changelog headings."""
    if commit.kind == "feat":
        return "Added"
    if commit.kind == "fix":
        return "Fixed"
    if commit.kind == "docs":
        return "Documentation"
    if commit.kind == "test":
        return "Tests"
    return "Changed"


def git_commits(since: str | None = None) -> list[Commit]:
    """Read commit subjects from ``since..HEAD`` (or all reachable commits)."""
    revision = f"{since}..HEAD" if since else "HEAD"
    result = subprocess.run(
        ["git", "log", "--format=%s", revision],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [classify_commit(line) for line in result.stdout.splitlines() if line.strip()]


def render_release(version: str, release_date: str, commits: list[Commit]) -> str:
    """Render a release section without changing the source changelog."""
    grouped: dict[str, list[Commit]] = {category: [] for category in CATEGORY_ORDER}
    for commit in commits:
        grouped[category_for(commit)].append(commit)

    lines = [f"## [{version.lstrip('v')}] - {release_date}", ""]
    for category in CATEGORY_ORDER:
        entries = grouped[category]
        if not entries:
            continue
        lines.extend([f"### {category}", ""])
        for commit in entries:
            marker = " **BREAKING**" if commit.breaking else ""
            lines.append(f"- {commit.subject}{marker}")
        lines.append("")
    if len(lines) == 2:
        lines.extend(["### Changed", "", "- No conventional commits found.", ""])
    return "\n".join(lines)


def insert_release(changelog: str, section: str, version: str) -> str:
    """Insert a release below the Unreleased section and reject duplicates."""
    normalized = version.lstrip("v")
    if re.search(rf"^## \[{re.escape(normalized)}\](?:\s|$)", changelog, re.MULTILINE):
        raise ValueError(f"CHANGELOG.md already contains [{normalized}]")

    headers = list(re.finditer(r"^## \[", changelog, re.MULTILINE))
    insertion = headers[1].start() if len(headers) > 1 else len(changelog)
    prefix = changelog[:insertion].rstrip() + "\n\n"
    suffix = changelog[insertion:].lstrip("\n")
    return prefix + section.rstrip() + "\n\n" + suffix


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Release version, for example 0.2.0")
    parser.add_argument("--since", help="Git tag or revision to use as the range start")
    parser.add_argument(
        "--date",
        default=dt.date.today().isoformat(),
        help="Release date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--changelog",
        type=Path,
        default=Path("CHANGELOG.md"),
        help="Changelog path (default: CHANGELOG.md)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the generated section")
    args = parser.parse_args()

    commits = git_commits(args.since)
    section = render_release(args.version, args.date, commits)
    if args.dry_run:
        print(section)
        return 0

    current = args.changelog.read_text(encoding="utf-8")
    updated = insert_release(current, section, args.version)
    args.changelog.write_text(updated, encoding="utf-8")
    print(f"Inserted [{args.version.lstrip('v')}] into {args.changelog}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
