"""Fails when merged output for a golden book changes; review the diff, then
run `uv run python -m libarrei.golden update` if the change is intended."""

import pytest

from libarrei.golden import GOLDEN_DIR, snapshot

BOOKS = sorted(p for p in GOLDEN_DIR.iterdir() if p.is_dir()) if GOLDEN_DIR.exists() else []


@pytest.mark.parametrize("folder", BOOKS, ids=lambda p: p.name)
def test_merged_output_matches_snapshot(folder):
    assert snapshot(folder) == (folder / "merged.txt").read_text()
