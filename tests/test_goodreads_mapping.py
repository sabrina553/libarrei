import json
from pathlib import Path

from libarrei.model import Source
from libarrei.sources.formats import normalise_format
from libarrei.sources.goodreads.mapping import edition_from_scrape, work_from_graphql

RAW = json.loads((Path(__file__).parent / "fixtures" / "goodreads_book.json").read_text())


def values(candidates):
    return [c.value for c in candidates]


def test_work_from_graphql():
    work = work_from_graphql(RAW)

    assert work.ids == {Source.GOODREADS: "97397727"}
    assert values(work.genres) == [["Fiction", "Historical Fiction"]]
    assert values(work.original_release_date) == ["2023-03-14"]
    assert work.series[0].value[0].position == "2"
    assert work.contributors[0].value[0].ids == {Source.GOODREADS: "347770"}


def test_edition_from_graphql():
    edition = work_from_graphql(RAW).editions[0]

    assert edition.ids == {Source.GOODREADS: "61771675"}
    assert values(edition.format) == ["ebook"]
    assert values(edition.asin) == ["B0B7R4Q5DJ"]
    assert edition.isbn13 == []


def test_edition_from_scrape():
    edition = edition_from_scrape({
        "title": "How to Cheat Your Own Death", "authors": ["Kristen Perrin"],
        "isbn13": "9798217047505", "book_type": "Audible Audio", "pages": None,
        "goodreads_id": "239433112",
    })

    assert values(edition.format) == ["audiobook"]
    assert edition.pages == []
    assert edition.contributors[0].value[0].name == "Kristen Perrin"


def test_unknown_format_is_kept_lowercased():
    assert normalise_format("Toinen Painos") == "toinen painos"
    assert normalise_format("Unknown Binding") is None


def test_publish_row_without_a_date_keeps_only_the_publisher():
    from libarrei.sources.goodreads.scraper import parse_publish_row

    assert parse_publish_row("Published by Adelphi") == (None, "Adelphi")
    assert parse_publish_row("Published April 28th 2026 by Dutton") == ("April 28th 2026", "Dutton")
    assert parse_publish_row("Published 2001") == ("2001", None)


def test_graphql_title_is_split_into_title_and_subtitle():
    raw = {**RAW, "title": "Dune: Deluxe Edition (Dune, #1)",
           "work": {**RAW["work"], "details": {**RAW["work"]["details"], "originalTitle": "Dune: A Novel"}}}
    work = work_from_graphql(raw)
    edition = work.editions[0]

    assert values(edition.title) == ["Dune"]
    assert values(edition.subtitle) == ["Deluxe Edition"]
    assert values(work.title) == ["Dune"]
    assert values(work.subtitle) == ["A Novel"]


def test_graphql_title_without_subtitle_leaves_subtitle_empty():
    edition = work_from_graphql(RAW).editions[0]

    assert values(edition.title) == ["Hello Beautiful"]
    assert edition.subtitle == []


def test_scraped_authors_keep_roles():
    from bs4 import BeautifulSoup

    from libarrei.sources.goodreads.scraper import parse_more_details

    html = """<div><div class="dataRow"><div class="dataTitle">Author:</div><div class="dataValue">
      <div class="authorName__container"><a class="authorName"><span>Matt Dinniman</span></a>
        <span class="greyText">(Goodreads Author)</span></div>
      <div class="authorName__container"><a class="authorName"><span>Jeff Hays</span></a>
        <span class="authorName greyText smallText role">(Narrator)</span></div>
    </div></div></div>"""
    _, authors = parse_more_details(BeautifulSoup(html, "html.parser").div)
    assert authors == [("Matt Dinniman", None), ("Jeff Hays", "Narrator")]

    edition = edition_from_scrape({"title": "Dungeon Crawler Carl", "authors": authors, "goodreads_id": "1"})
    people = edition.contributors[0].value
    assert [(p.name, p.role) for p in people] == [("Matt Dinniman", "author"), ("Jeff Hays", "narrator")]


def test_dates_before_year_one_are_dropped_not_fatal():
    from libarrei.sources.goodreads.mapping import date_from_millis

    assert date_from_millis(-87_400_000_000_000) is None
    assert date_from_millis(0) == "1970-01-01"
