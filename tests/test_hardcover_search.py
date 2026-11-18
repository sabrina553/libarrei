from libarrei.sources.hardcover.client import hits_from_search, rank_hits, title_similarity


def hit(id, title, authors, users):
    return {"document": {"id": str(id), "title": title, "author_names": authors, "users_count": users}}


def test_exact_niche_title_beats_popular_partial_match():
    hits = [hit(1, "Crossings: How Road Ecology Is Shaping the Future", ["Ben Goldfarb"], 99),
            hit(2, "Salt Lakes: An Unnatural History", ["Caroline Tracey"], 9)]
    assert rank_hits(hits, "salt lakes")[0] == 2


def test_popularity_breaks_ties_between_equal_matches():
    hits = [hit(1, "The Hobbit: A Graphic Novel", ["Chuck Dixon", "J.R.R. Tolkien"], 511),
            hit(2, "The Hobbit, or There and Back Again", ["J.R.R. Tolkien"], 13426)]
    assert rank_hits(hits, "the hobbit", "tolkien")[0] == 2


def test_author_match_outweighs_same_title():
    hits = [hit(1, "Hello Beautiful", ["Someone Else"], 5000),
            hit(2, "Hello Beautiful", ["Ann Napolitano"], 900)]
    assert rank_hits(hits, "hello beautiful", "napolitano")[0] == 2


def test_main_title_is_compared_without_subtitle():
    assert title_similarity("dune", "Dune: Deluxe Edition") == 1.0


def test_missing_results_give_no_hits():
    assert hits_from_search({}) == []
    assert hits_from_search({"search": {"results": None}}) == []
