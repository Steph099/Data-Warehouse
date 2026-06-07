# Acme DWH

A bi-temporal data warehouse for financial markets data. It pulls time-series
data from external vendors (Bitfinex, Nasdaq Data Link), stores every version
immutably in Cassandra, serves it over a REST API, runs Spark jobs on top of it,
and lets you query the whole thing in plain English through an LLM assistant.

There's also a React dashboard that wraps all of it into one UI.

## What's in it

- **Ingestion (ETL)** — fetches vendor data, normalizes it, loads it idempotently.
- **REST API** — paginated queries over assets, data sources, and time series,
  with OpenAPI docs at `/docs`.
- **Analytics** — two Spark jobs: per-year totals and a regression that predicts
  daily open price.
- **MCP server + assistant** — read-only tools a local Ollama model can call to
  answer questions about the data.
- **Web UI** — React/Vite dashboard: market overview, asset/source browsers,
  a time-series explorer with as-of time travel, analytics, ingest, and chat.

Everything is bi-temporal: records are never overwritten. Each row keeps a
business date (when it was true) and a system time (when we stored it), so you
can always reproduce what the data looked like at any point in the past.

## Stack

Python 3.12+, FastAPI, Cassandra 5.0, PySpark, MCP, Ollama, React + Vite.
Cassandra and Spark run in Docker.

The API talks to Cassandra only through a Data Access Layer — that's the one
place any CQL lives. The MCP server sits on top of the REST API, not the database.

## Requirements

- Docker Desktop (Cassandra + Spark)
- Python 3.12+
- Node.js 18+ (for the frontend)
- Ollama with a tool-calling model — only needed for the assistant

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows
# source .venv/bin/activate         # macOS/Linux
pip install -r requirements-dev.txt
pip install -e .

copy .env.example .env              # optional, defaults work

docker compose up -d cassandra      # wait ~60-90s until healthy
acme-init-db                        # creates keyspace + tables
```

## Run

```powershell
# 1. Ingest some data
acme-ingest BTCUSD ETHUSD --start 2021-01-01

# 2. Start the API  ->  http://127.0.0.1:8000/docs
uvicorn acme_dwh.api.main:app

# 3. Frontend  ->  http://localhost:5173
npm install --prefix frontend
npm run dev --prefix frontend
```

The Vite dev server proxies `/api` to the backend, so no CORS setup needed.

### Spark jobs (optional)

```powershell
docker compose up -d --build spark

# per-year totals
docker compose exec spark /opt/spark/bin/spark-submit --master "local[*]" `
  --packages com.datastax.spark:spark-cassandra-connector_2.12:3.5.1 `
  --conf spark.jars.ivy=/tmp/.ivy2 --conf spark.cassandra.connection.host=cassandra `
  /opt/jobs/aggregation_job.py

# regression
docker compose exec -e ASSET_ID=BTCUSD spark /opt/spark/bin/spark-submit --master "local[*]" `
  --packages com.datastax.spark:spark-cassandra-connector_2.12:3.5.1 `
  --conf spark.jars.ivy=/tmp/.ivy2 --conf spark.cassandra.connection.host=cassandra `
  /opt/jobs/regression_job.py
```

### Assistant (optional)

```powershell
ollama pull llama3.2
# keep the API running, then:
acme-assistant "What crypto assets do we have, and how did BTCUSD move recently?"
```

## Tests

```powershell
pytest
```

Unit tests run without Cassandra. Integration tests auto-skip unless Cassandra
is up (`docker compose up -d cassandra` + `acme-init-db`).

## Layout

```
src/acme_dwh/
  dal/          data access layer (all CQL lives here)
  ingestion/    ETL + vendor providers
  api/          FastAPI app + routers
  analytics/    Spark jobs
  mcp/          MCP server + Ollama client
  db/           schema.cql + init_db
frontend/       React + Vite dashboard
tests/          unit + integration
```
