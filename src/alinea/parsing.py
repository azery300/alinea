"""Turn the legi-data JSON tree of the Code du travail into flat article records."""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from html.parser import HTMLParser

# All three states are in force today. ABROGE_DIFF has a repeal scheduled for a later date,
# MODIFIE has a new version scheduled for a later date.
IN_FORCE_STATES = {"VIGUEUR", "ABROGE_DIFF", "MODIFIE"}

# L1, L1221-19, D3332-21-3-1, plus two official variants: R*2122-1 (decree in Conseil d'Etat
# adopted in the Council of Ministers) and L5214-1 A (article inserted between two others).
# Annexes ("Annexe I", "Annexe à l'article R1422-4") do not match and are left out on purpose.
ARTICLE_NUM = re.compile(r"[LRD]\*?\d+(-\d+)*( [A-Z])?")

# legi-data marks "no end date" with 2999-01-01.
OPEN_END = date(2999, 1, 1)

LEGIFRANCE_URL = "https://www.legifrance.gouv.fr/codes/article_lc/{id}"


@dataclass(frozen=True)
class Article:
    id: str  # LEGIARTI id of the version in force
    cid: str  # id shared by all versions of the article
    num: str  # e.g. "L1221-19"
    text: str  # plain text, one paragraph (alinea) per line
    breadcrumb: tuple[str, ...]  # partie > livre > titre > chapitre > section...
    status: str
    valid_from: date
    valid_to: date | None  # None when no end date is planned
    nota: str

    @property
    def part(self) -> str:
        """L (legislative), R or D (regulatory)."""
        return self.num[0]

    @property
    def url(self) -> str:
        return LEGIFRANCE_URL.format(id=self.id)


@dataclass
class ParseResult:
    articles: list[Article]
    skipped: list[str]  # numbers of the articles left out, with the reason


class _TextExtractor(HTMLParser):
    # Tags that start a new line. Table cells also get their own line: only 29 articles
    # contain a table, and one cell per line keeps the text readable.
    BLOCK_TAGS = {"p", "br", "div", "center", "table", "tr", "td", "th"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(html: str) -> str:
    """Strip tags, keep one paragraph per line, collapse whitespace inside lines."""
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    lines = (" ".join(line.split()) for line in "".join(parser.parts).split("\n"))
    return "\n".join(line for line in lines if line)


def clean_title(title: str) -> str:
    """Section titles come with stray spaces and line breaks."""
    return " ".join(title.split())


def _to_date(ms: int) -> date:
    return datetime.fromtimestamp(ms / 1000, UTC).date()


def walk_articles(node: dict, breadcrumb: tuple[str, ...] = ()) -> Iterator[tuple[dict, tuple]]:
    """Yield (article data, breadcrumb) for every article node of the tree, in code order."""
    if node["type"] == "article":
        yield node["data"], breadcrumb
        return
    if node["type"] == "section":
        breadcrumb = (*breadcrumb, clean_title(node["data"]["title"]))
    for child in node.get("children") or []:
        yield from walk_articles(child, breadcrumb)


def parse_code(tree: dict) -> ParseResult:
    result = ParseResult(articles=[], skipped=[])
    for data, breadcrumb in walk_articles(tree):
        num = data["num"].strip()  # one article number comes with a leading space
        if not ARTICLE_NUM.fullmatch(num):
            result.skipped.append(f"{num}: not an article number")
            continue
        if data["etat"] not in IN_FORCE_STATES:
            result.skipped.append(f"{num}: state {data['etat']}")
            continue
        valid_to = _to_date(data["dateFin"])
        result.articles.append(
            Article(
                id=data["id"],
                cid=data["cid"],
                num=num,
                text=html_to_text(data["texteHtml"]),
                breadcrumb=breadcrumb,
                status=data["etat"],
                valid_from=_to_date(data["dateDebut"]),
                valid_to=None if valid_to >= OPEN_END else valid_to,
                nota=html_to_text(data.get("notaHtml") or ""),
            )
        )
    return result
