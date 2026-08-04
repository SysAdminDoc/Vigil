from devutils.changelog import category_for, classify_commit, insert_release, render_release


def test_classify_conventional_commit_and_breaking_marker():
    commit = classify_commit("feat(search)!: replace the default provider")

    assert commit.subject == "replace the default provider"
    assert commit.kind == "feat"
    assert commit.breaking is True
    assert category_for(commit) == "Added"


def test_render_release_groups_commit_categories():
    section = render_release(
        "v0.2.0",
        "2026-08-03",
        [classify_commit("fix: preserve the NTP extension ID"), classify_commit("docs: update build notes")],
    )

    assert section.startswith("## [0.2.0] - 2026-08-03")
    assert "### Fixed" in section
    assert "### Documentation" in section


def test_insert_release_keeps_unreleased_at_the_top_and_rejects_duplicate():
    changelog = "# Changelog\n\n## [Unreleased]\n\n- pending\n\n## [0.1.0] - 2026-01-01\n"
    updated = insert_release(changelog, "## [0.2.0] - 2026-08-03\n\n### Added\n\n- item", "0.2.0")

    assert updated.index("[Unreleased]") < updated.index("[0.2.0]") < updated.index("[0.1.0]")
    try:
        insert_release(updated, "## [0.2.0] - 2026-08-03", "0.2.0")
    except ValueError as exc:
        assert "already contains" in str(exc)
    else:
        raise AssertionError("duplicate release was accepted")
