# Alinea

An agentic RAG assistant that answers questions about the French Labor Code (Code du travail),
cites the articles behind each answer, and refuses when a question is out of scope or the
sources are not enough.

**Status: work in progress (step 1, data).** The Code du travail is loaded into Postgres;
search, agent and evaluation are not built yet.
This README only describes what exists and has been measured.

> This project provides legal information, not legal advice.

## Quickstart

Requirements: [uv](https://docs.astral.sh/uv/), make, and Docker or Podman with compose.

```bash
cp .env.example .env
make install   # create the virtualenv and install dependencies
make db-up     # start Postgres 16 + pgvector
make ingest    # download the Code du travail (legi-data) and load the articles table
make lint
make test
```

## Résumé en français

Alinea est un assistant qui répond à des questions sur le Code du travail en citant les articles
qui fondent sa réponse, et qui refuse quand la question sort du périmètre. Projet en cours de
construction : pour l'instant, les 11 581 articles en vigueur sont chargés dans Postgres.

## Author

Adam Britel

## License

MIT
