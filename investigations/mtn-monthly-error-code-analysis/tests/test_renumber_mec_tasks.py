import pytest

from scripts.renumber_mec_tasks import renumber_text, sort_story_sections


def test_simultaneous_swap_and_slash_shorthand():
    mapping = {1: 2, 2: 1, 3: 3}
    assert renumber_text("MEC-1 then MEC-2, MEC-3/1 and MEC-1", mapping) == (
        "MEC-2 then MEC-1, MEC-3/2 and MEC-2"
    )


def test_comma_list_is_ambiguous_and_fails():
    with pytest.raises(ValueError):
        renumber_text("MEC-1, 2 tasks", {1: 2, 2: 1})


def test_slash_id_before_sentence_period():
    assert renumber_text("see MEC-1/2.", {1: 2, 2: 1}) == "see MEC-2/1."


def test_unknown_id_fails_loudly():
    with pytest.raises(KeyError):
        renumber_text("see MEC-9", {1: 2})


def test_sort_story_sections():
    text = "# Title\n\n## MEC-2 — b\n\nbody b\n\n---\n\n## MEC-1 — a\n\nbody a\n"
    out = sort_story_sections(text)
    assert out.index("## MEC-1 ") < out.index("## MEC-2 ")
    assert out.startswith("# Title")


def test_sort_rebuilds_separators_exactly():
    text = "# T\n\n## MEC-2 — b\n\nbody b\n\n---\n\n## MEC-1 — a\n\nbody a\n\n---\n"
    assert sort_story_sections(text) == "# T\n\n## MEC-1 — a\n\nbody a\n\n---\n\n## MEC-2 — b\n\nbody b\n"


def test_sort_without_headings_fails():
    with pytest.raises(ValueError):
        sort_story_sections("no headings")
