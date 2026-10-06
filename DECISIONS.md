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
