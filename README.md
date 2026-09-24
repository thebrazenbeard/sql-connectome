# SQL Connectome

SQL Connectome is a provider-independent PostgreSQL platform and governed ChatGPT/MCP control surface.

The project is designed as a general-purpose platform: standard PostgreSQL remains the database engine while SQL Connectome provides the control plane, currentness and receipt semantics, recovery contract, and AI-facing interfaces.

It is deliberately **not** a PostgreSQL fork. PostgreSQL remains the database engine; SQL Connectome owns the control plane, currentness/receipt semantics, recovery contract, and AI-facing interface.

## V1 slice

This branch establishes:

- a FastAPI control service with bearer authentication;
- provider-neutral runtime identity;
- bounded read-only SQL execution inside PostgreSQL read-only transactions;
- schema inventory;
- a Lantern current-cut adapter using one `REPEATABLE READ READ ONLY` transaction;
- canonical migration ledger and effect-receipt storage;
- provider-independent migration tooling;
- local PostgreSQL Docker development;
- unit/integration CI against PostgreSQL 17.

Protected database writes are intentionally absent from the first API slice.

## Local development

```bash
cp .env.example .env
docker compose up -d db
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
export SQL_CONNECTOME_DATABASE_URL='postgresql://postgres:postgres@localhost:5432/sql_connectome'
export SQL_CONNECTOME_API_TOKEN='local-dev-token'
python scripts/apply_migrations.py
uvicorn sql_connectome.app:app --reload
```

Run tests:

```bash
pytest
ruff check .
```

## Authority boundary

SQL Connectome source, an installed plugin, or a successful database read does not grant write authority. Provider provisioning, credential changes, migrations against durable environments, restore, destructive operations, plugin installation, and protected writes are separate effects and require explicit authority plus verification.
