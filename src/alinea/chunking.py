"""V1 chunking: fixed-size windows over the whole code, blind to article boundaries.

This is the naive baseline on purpose. The articles are joined in code order, each one under an
"Article <num>" header (like a PDF of the code), then cut into windows of a fixed size with some
overlap. A window can hold the end of one article and the start of the next. Each chunk keeps
the numbers of the articles it overlaps, which is what retrieval recall@k is measured on.
"""

from bisect import bisect_left, bisect_right
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    text: str
    article_nums: tuple[str, ...]


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    num: str


def join_articles(articles: list[tuple[str, str]]) -> tuple[str, list[Span]]:
    """Join (num, text) pairs into one text; return it with the character span of each article
    (header included)."""
    parts: list[str] = []
    spans: list[Span] = []
    offset = 0
    for num, text in articles:
        block = f"Article {num}\n{text}"
        spans.append(Span(offset, offset + len(block), num))
        parts.append(block)
        offset += len(block) + 2  # the "\n\n" separator
    return "\n\n".join(parts), spans


def _cut_at_space(text: str, start: int, end: int) -> int:
    """Move `end` back to the last whitespace, so a window does not stop mid-word. Keeps `end`
    when there is no whitespace in the second half of the window."""
    if end >= len(text):
        return len(text)
    space = max(text.rfind(" ", start, end), text.rfind("\n", start, end))
    return space if space > start + (end - start) // 2 else end


def fixed_size_chunks(articles: list[tuple[str, str]], size: int, overlap: int) -> list[Chunk]:
    """Cut the joined articles into windows of at most `size` characters, each one starting
    `overlap` characters before the end of the previous one."""
    # A window keeps at least half of `size` (see _cut_at_space), so an overlap below half the
    # size guarantees that each window starts after the previous one.
    if not 0 <= overlap < size // 2:
        raise ValueError("overlap must be in [0, size / 2)")
    text, spans = join_articles(articles)
    starts = [s.start for s in spans]
    ends = [s.end for s in spans]

    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = _cut_at_space(text, start, start + size)
        # Articles overlapping [start, end): span.start < end and span.end > start.
        first, last = bisect_right(ends, start), bisect_left(starts, end)
        nums = tuple(span.num for span in spans[first:last])
        chunks.append(Chunk(text[start:end].strip(), nums))
        if end == len(text):
            break
        # Next window starts `overlap` characters back, moved forward to a word start.
        start = end - overlap
        space = text.find(" ", start, end)
        start = space + 1 if space != -1 else start
    return chunks
