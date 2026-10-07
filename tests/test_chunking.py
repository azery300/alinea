import pytest

from alinea.chunking import fixed_size_chunks, join_articles

ARTICLES = [
    ("L1", "Premier article assez court."),
    ("L2", " ".join(f"mot{i}" for i in range(60))),  # about 400 characters
    ("L3", "Dernier article."),
]


def test_join_articles_adds_headers_and_spans():
    text, spans = join_articles([("L1", "Un."), ("L2", "Deux.")])
    assert text == "Article L1\nUn.\n\nArticle L2\nDeux."
    assert [text[s.start : s.end] for s in spans] == ["Article L1\nUn.", "Article L2\nDeux."]


def test_chunks_respect_size_and_cover_the_whole_text():
    chunks = fixed_size_chunks(ARTICLES, size=120, overlap=20)
    assert all(len(c.text) <= 120 for c in chunks)
    assert chunks[0].text.startswith("Article L1")
    assert chunks[-1].text.endswith("Dernier article.")


def test_chunks_do_not_cut_words():
    words = set(join_articles(ARTICLES)[0].split())
    for chunk in fixed_size_chunks(ARTICLES, size=120, overlap=20):
        assert set(chunk.text.split()) <= words


def test_consecutive_chunks_overlap():
    first, second = fixed_size_chunks(ARTICLES, size=120, overlap=20)[:2]
    last_word = first.text.split()[-1]
    assert last_word in second.text.split()[:5]


def test_chunk_lists_every_article_it_overlaps():
    chunks = fixed_size_chunks(ARTICLES, size=120, overlap=20)
    assert chunks[0].article_nums == ("L1", "L2")  # small articles get mixed: the V1 weakness
    assert all(c.article_nums for c in chunks)
    assert {n for c in chunks for n in c.article_nums} == {"L1", "L2", "L3"}
    assert chunks[-1].article_nums[-1] == "L3"


def test_one_chunk_when_text_fits():
    [chunk] = fixed_size_chunks([("L1", "Court.")], size=500, overlap=50)
    assert chunk.text == "Article L1\nCourt."
    assert chunk.article_nums == ("L1",)


def test_overlap_must_stay_below_half_the_size():
    with pytest.raises(ValueError):
        fixed_size_chunks(ARTICLES, size=100, overlap=50)
