from datetime import date

from alinea.parsing import html_to_text, parse_code

# 2999-01-01 in milliseconds, legi-data's "no end date".
OPEN_END_MS = 32472144000000


def article(num, etat="VIGUEUR", html="<p>Texte.</p>", date_fin=OPEN_END_MS):
    return {
        "type": "article",
        "data": {
            "id": f"LEGIARTI-{num.strip()}",
            "cid": f"CID-{num.strip()}",
            "num": num,
            "etat": etat,
            "texteHtml": html,
            "notaHtml": "",
            "dateDebut": 1209600000000,  # 2008-05-01
            "dateFin": date_fin,
        },
    }


def section(title, *children):
    return {"type": "section", "data": {"title": title}, "children": list(children)}


def code(*children):
    return {"type": "code", "data": {"title": "Code du travail"}, "children": list(children)}


def test_html_to_text_keeps_one_paragraph_per_line():
    html = "<p>Premier alinéa : </p><p> 1° Pour les cadres,<br/>de quatre mois. </p><p></p>"
    assert html_to_text(html) == "Premier alinéa :\n1° Pour les cadres,\nde quatre mois."


def test_html_to_text_drops_links_but_keeps_their_text():
    html = '<p>Voir l\'article <a href="/affichCodeArticle.do?id=1">L. 1221-19</a>.</p>'
    assert html_to_text(html) == "Voir l'article L. 1221-19."


def test_html_to_text_decodes_entities_and_puts_table_cells_on_lines():
    html = "<table><tr><td>Durée</td><td>2 mois &amp; plus</td></tr></table>"
    assert html_to_text(html) == "Durée\n2 mois & plus"


def test_parse_code_builds_breadcrumb_and_fields():
    livre = section("Livre II :\r\n Le contrat", article("L1221-19"))
    tree = code(section("Partie législative  ", livre))
    [a] = parse_code(tree).articles
    assert a.num == "L1221-19"
    assert a.part == "L"
    assert a.breadcrumb == ("Partie législative", "Livre II : Le contrat")
    assert a.text == "Texte."
    assert a.valid_from == date(2008, 5, 1)
    assert a.valid_to is None
    assert a.url == "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI-L1221-19"


def test_parse_code_keeps_articles_in_force_with_scheduled_changes():
    repeal_ms = 1798761600000  # 2027-01-01
    tree = code(
        article("L1", etat="ABROGE_DIFF", date_fin=repeal_ms),
        article("R2", etat="MODIFIE"),
    )
    first, second = parse_code(tree).articles
    assert first.valid_to == date(2027, 1, 1)
    assert second.status == "MODIFIE"


def test_parse_code_skips_annexes_and_repealed_articles():
    tree = code(article("Annexe I"), article("D3", etat="ABROGE"), article(" L1251-33-1"))
    result = parse_code(tree)
    assert [a.num for a in result.articles] == ["L1251-33-1"]  # leading space removed
    assert result.skipped == ["Annexe I: not an article number", "D3: state ABROGE"]


def test_parse_code_keeps_official_number_variants():
    tree = code(article("R*2122-1"), article("L5214-1 A"), article("D3332-21-3-1"))
    assert [a.num for a in parse_code(tree).articles] == ["R*2122-1", "L5214-1 A", "D3332-21-3-1"]
