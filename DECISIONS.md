# Decisions

Each non-trivial choice, with its reason and, when possible, a number.

## Step 0: skeleton

- **Hosting: GitHub.** More visible to recruiters than GitLab. CI runs on GitHub Actions.
- **Project name: Alinea.** An "alinéa" is a paragraph of a legal article, which is also the
  unit used to split long articles in the V2 chunking.
- **Observability: Langfuse cloud (free tier).** Self-hosting Langfuse v3 needs Postgres,
  ClickHouse, Redis and S3 storage, which adds operations work with no benefit for this project.
  The data sent (questions and public legal texts) is not sensitive.
- **Demo UI: static HTML page served by FastAPI.** No extra dependency, easy to explain.
  Chainlit can come later if the demo needs to show the agent steps.
- **LLM and embedding provider: deferred to step 2.** No access to Azure AI Foundry. Free tiers
  (Google Gemini API, Mistral) will be checked for limits and terms at step 2. The skeleton does
  not call any model. Azure stays the deployment target (step 8).
- **Containers: compose file compatible with both Docker and Podman.** Developed locally with
  Podman, CI uses Docker. The Makefile picks whichever is installed.
- **Database: `pgvector/pgvector:pg16` image.** Postgres 16 with pgvector preinstalled, same
  engine as the planned Azure Database for PostgreSQL Flexible Server.
- **Python pinned to 3.12** (`.python-version`, `requires-python`). uv
  downloads it, so the system Python (3.14) is not used.

## Step 1: data

- **LLM and embedding provider for step 2: Google Gemini API** (embedding model available on
  the free tier). Azure stays the deployment target and may be revisited later.
- **Source: `@socialgouv/legi-data`, pinned to version 2.570.0** (published 2026-10-06, text
  version of the code dated 2026-10-01). Compared on 2026-10-06 with the two other candidates:

  | | legi-data | HF `louisbrulenaudet/code-travail` | DILA LEGI |
  |---|---|---|---|
  | Freshness | daily npm release | last update 2025-07-11 | daily |
  | Articles | 11,591 | 9,774 (1,869 present in legi-data are missing) | |
  | Hierarchy | full tree | one string per article | full |
  | License | Apache 2.0 | Apache 2.0 | Licence Ouverte |
  | Cost to use | one JSON file in a tarball | one parquet file | large XML dumps |

  legi-data is itself a daily extraction of LEGI, so it gives the official text and the full
  hierarchy at the lowest cost. Caveat: its README says "experimental, for internal usage
  only", which is a support warning, not a license restriction. The tarball is downloaded
  straight from the npm registry (no Node needed) and checked against the sha512 the registry
  publishes, so every run with the same pin ingests the same bytes.
- **Articles kept: every article in force today.** That covers three states: `VIGUEUR`
  (11,472), `ABROGE_DIFF` (108, repeal scheduled between 2027 and 2029, still in force now) and
  `MODIFIE` (1, R4451-39, new version scheduled for 2027-07-01). The legi-data tree only
  contains the current version, so there is no repealed article to filter out.
- **Annexes left out (10 items).** They have no standard article number and are mostly long
  technical tables (up to 112,726 characters). They are 0.09% of the items. Known limit:
  questions whose answer sits only in an annex cannot be answered.
- **Article numbers kept as Legifrance writes them**, including two official variants a naive
  regex misses: `R*2122-1` (13 articles, decrees adopted in the Council of Ministers) and
  `L5214-1 A` (8 articles inserted between two others). A first version of the regex dropped
  these 21 real articles; the stats below were measured after the fix. The lookup by number
  (step 4) will need to accept `R2122-1` for `R*2122-1`.
- **Text taken from `texteHtml`, not `texte`.** The `texte` field flattens the paragraphs of an
  article into one line. The HTML keeps one `<p>` per paragraph (alinea), which the V2
  structural chunking needs. Tags are stripped, one paragraph per line (3.0 lines per article on
  average). Links to other articles keep their text. The 29 tables are flattened to one cell per
  line. The `nota` (often an entry-into-force rule) is stored in its own column (2,182 articles
  have one).
- **Legifrance URL built from the version id**: `https://www.legifrance.gouv.fr/codes/article_lc/<LEGIARTI id>`.
  Checked by hand on L1 (Legifrance blocks scripted requests).
- **Loading: TRUNCATE + COPY in one transaction.** Reloading is idempotent and readers never
  see a half-loaded code. Takes about 2 seconds for the whole code.

**Result (legi-data 2.570.0): 11,581 articles.** Text length in characters:

| Part | Articles | Min | Median | p90 | p99 | Max | Mean |
|---|---|---|---|---|---|---|---|
| L (legislative) | 4,426 | 35 | 410 | 1,211 | 3,220 | 8,614 | 592 |
| R (regulatory) | 5,604 | 35 | 395 | 1,075 | 3,006 | 31,801 | 563 |
| D (regulatory) | 1,551 | 48 | 420 | 1,093 | 2,975 | 10,651 | 580 |
| All | 11,581 | 35 | 403 | 1,133 | 3,081 | 31,801 | 577 |

What it means for chunking: half of the articles are under about 400 characters, far below a
500-token chunk, so the V1 fixed-size chunks will often mix several articles. 341 articles
(2.9%) are over 2,000 characters; the longest (R2312-9, 31,801 characters) is a list of
information items, and the V2 split by paragraph is meant for those. The breadcrumb is up to 9
levels deep.
