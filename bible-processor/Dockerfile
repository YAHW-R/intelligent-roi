# Image for the promise-extraction pipeline (Fase 1).
# Builds candidates -> classify -> sanitize using a local Ollama instance.
#
# The SQLite database is NOT stored in a Docker volume: the host directory
# bible-processor/ is bind-mounted into /app, so promesas.db is written as a
# plain file on the host, immediately reusable by the Go CLI and other tools.
FROM python:3.12-slim

RUN pip install --no-cache-dir pandas

WORKDIR /app

# The pipeline entrypoint. Extra args (e.g. --limit 50) are forwarded to
# classify.py via run_pipeline.sh.
ENTRYPOINT ["./run_pipeline.sh"]
