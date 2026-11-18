from libarrei.match import EditionGroup
from libarrei.merge import clean_description, merge, merge_group, resolve
from libarrei.model import Candidate, Edition, Source, Work

GR, HC, OL = Source.GOODREADS, Source.HARDCOVER, Source.OPENLIBRARY


def cands(*pairs):
    return [Candidate(value=v, source=s, source_id="1") for s, v in pairs]


def test_structured_fields_prefer_hardcover():
    r = resolve("publisher", cands((OL, "Allen"), (GR, "Harper"), (HC, "HarperCollins")))
    assert r.source == HC and r.conflict
    assert [a.value for a in r.alternatives] == ["Harper", "Allen"]


def test_descriptions_prefer_goodreads_and_carry_a_licence():
    r = resolve("description", cands((HC, "Plain."), (GR, "<b>Rich</b> blurb.")))
    assert (r.value, r.source, r.licence) == ("Rich blurb.", GR, "publisher copyright")


def test_cosmetic_differences_are_not_conflicts():
    r = resolve("publisher", cands((HC, "HarperCollins"), (GR, "Harper Collins")))
    assert not r.conflict and r.alternatives == []


def test_compatible_dates_pick_the_most_precise():
    r = resolve("release_date", cands((HC, "1976"), (GR, "1976-08"), (OL, "1976-08-12")))
    assert r.value == "1976-08-12" and not r.conflict


def test_hardcover_first_of_january_counts_as_year_only():
    r = resolve("release_date", cands((HC, "2023-01-01"), (GR, "2023-03-14")))
    assert r.value == "2023-03-14" and not r.conflict


def test_different_dates_conflict():
    r = resolve("release_date", cands((HC, "1937-09-21"), (GR, "1966")))
    assert r.value == "1937-09-21" and r.conflict


def test_page_count_conflict_is_flagged():
    assert resolve("pages", cands((HC, 310), (OL, 320))).conflict


def test_genres_never_conflict():
    assert not resolve("genres", cands((GR, ["Fantasy"]), (HC, ["Fiction"]))).conflict


def test_clean_description_strips_html_and_promo():
    raw = "<p>A novel.</p><br>Brought to you by Penguin."
    assert clean_description(raw) == "A novel."


def test_merge_groups_editions_and_work_fields():
    hc, gr = Edition(), Edition()
    hc.add("isbn13", "9780547951966", HC, "2")
    hc.add("pages", 300, HC, "2")
    gr.add("isbn13", "9780547951966", GR, "1")
    gr.add("pages", 300, GR, "1")
    works = {HC: Work(editions=[hc]), GR: Work(editions=[gr])}
    works[HC].add("title", "The Hobbit", HC, "9")

    merged = merge(works)

    assert merged.fields["title"].value == "The Hobbit"
    [edition] = merged.editions
    assert edition.ids == {HC: ["2"], GR: ["1"]} and not edition.fields["pages"].conflict


def test_merged_edition_carries_duplicate_reasons():
    a, b = Edition(), Edition()
    a.add("asin", "B007978NPG", OL, "OL1M")
    b.add("asin", "B007978NPG", OL, "OL2M")
    [edition] = merge({OL: Work(editions=[a, b])}).editions
    assert edition.duplicates == [OL] and edition.duplicate_reasons == {OL: ["asin"]}


def test_merge_carries_hardcover_slugs():
    edition = Edition(slugs={HC: "the-hobbit"})
    edition.add("isbn13", "9780547951966", HC, "2")
    work = Work(editions=[edition], slugs={HC: "the-hobbit"})
    merged = merge({HC: work})
    assert merged.slugs == {HC: "the-hobbit"} and merged.editions[0].slugs == {HC: "the-hobbit"}
