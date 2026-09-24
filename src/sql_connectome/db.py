from __future__ import annotations

from typing import Any

import psycopg
from psycopg import Connection
from psycopg.errors import UndefinedFunction, UndefinedTable
from psycopg.rows import dict_row

from .config import Settings
from .receipts import canonical_digest, make_receipt
from .sql_guard import validate_readonly_sql


def connect(settings: Settings) -> Connection[dict[str, Any]]:
    return psycopg.connect(
        settings.database_url,
        autocommit=True,
        row_factory=dict_row,
        application_name="sql-connectome",
    )


def _runtime_identity(conn: Connection[dict[str, Any]]) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT current_database() AS database_name,
               current_user AS database_user,
               current_setting('server_version_num') AS server_version_num,
               current_setting('server_version') AS server_version
        """
    ).fetchone()
    assert row is not None

    ledger = conn.execute(
        "SELECT to_regclass('sql_connectome.schema_migrations')::text AS ledger"
    ).fetchone()
    migration_head = None
    if ledger and ledger["ledger"]:
        head = conn.execute(
            """
            SELECT version, checksum
            FROM sql_connectome.schema_migrations
            ORDER BY applied_at DESC, version DESC
            LIMIT 1
            """
        ).fetchone()
        if head:
            migration_head = {"version": head["version"], "checksum": head["checksum"]}

    subject = {
        "database_name": row["database_name"],
        "database_user": row["database_user"],
        "server_version_num": row["server_version_num"],
        "server_version": row["server_version"],
        "migration_head": migration_head,
    }
    return {**subject, "identity_digest": canonical_digest(subject)}


def platform_health(settings: Settings) -> dict[str, Any]:
    with connect(settings) as conn:
        identity = _runtime_identity(conn)
    return {
        "schema": "SQL_CONNECTOME_PLATFORM_HEALTH_V1",
        "status": "ok",
        "runtime": identity,
        "receipt": make_receipt("PLATFORM_HEALTH", identity),
    }


def schema_inventory(settings: Settings) -> dict[str, Any]:
    schemas = list(settings.schema_allowlist)
    with connect(settings) as conn:
        tables = conn.execute(
            """
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = ANY(%s)
            ORDER BY table_schema, table_name
            """,
            (schemas,),
        ).fetchall()
        functions = conn.execute(
            """
            SELECT n.nspname AS function_schema,
                   p.proname AS function_name,
                   pg_get_function_identity_arguments(p.oid) AS identity_arguments
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = ANY(%s)
            ORDER BY n.nspname, p.proname, identity_arguments
            """,
            (schemas,),
        ).fetchall()
        identity = _runtime_identity(conn)

    subject = {
        "runtime_identity_digest": identity["identity_digest"],
        "schemas": schemas,
        "table_count": len(tables),
        "function_count": len(functions),
    }
    return {
        "schema": "SQL_CONNECTOME_SCHEMA_INVENTORY_V1",
        "runtime": identity,
        "schemas": schemas,
        "tables": tables,
        "functions": functions,
        "receipt": make_receipt("SCHEMA_INVENTORY", subject),
    }


def query_readonly(
    settings: Settings,
    sql: str,
    params: list[Any] | dict[str, Any] | None = None,
) -> dict[str, Any]:
    statement = validate_readonly_sql(sql)
    with connect(settings) as conn:
        with conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            conn.execute(
                "SELECT set_config('statement_timeout', %s, true)",
                (str(settings.statement_timeout_ms),),
            )
            identity = _runtime_identity(conn)
            cursor = conn.execute(statement, params or ())
            if cursor.description is None:
                raise ValueError("READ_QUERY_RETURNED_NO_RESULT")
            rows = cursor.fetchmany(settings.max_rows + 1)

    truncated = len(rows) > settings.max_rows
    if truncated:
        rows = rows[: settings.max_rows]

    subject = {
        "runtime_identity_digest": identity["identity_digest"],
        "sql_digest": canonical_digest(statement),
        "row_count": len(rows),
        "truncated": truncated,
    }
    return {
        "schema": "SQL_CONNECTOME_READ_RESULT_V1",
        "runtime": identity,
        "columns": [column.name for column in cursor.description or ()],
        "rows": rows,
        "truncated": truncated,
        "receipt": make_receipt("READ_QUERY", subject),
    }


def lantern_current_cut(
    settings: Settings,
    project_scope: str = "PROJECT_LANTERN",
) -> dict[str, Any]:
    try:
        with connect(settings) as conn:
            with conn.transaction():
                conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                conn.execute(
                    "SELECT set_config('statement_timeout', %s, true)",
                    (str(settings.statement_timeout_ms),),
                )
                identity = _runtime_identity(conn)
                cuts = conn.execute(
                    "SELECT * FROM bt2.material_cut_v1(%s)",
                    (project_scope,),
                ).fetchall()
                if len(cuts) != 1:
                    raise ValueError("LANTERN_CUT_NOT_SINGULAR")
                cut = cuts[0]
                payload = conn.execute(
                    """
                    SELECT material_id::text,
                           project_scope,
                           schema_version,
                           semantic_key,
                           canonical_digest,
                           source_digest,
                           canonical_payload,
                           created_at,
                           receipt_id::text,
                           profile_digest,
                           policy_digest
                    FROM bt2.runtime_visible_materials_v1
                    WHERE project_scope = %s
                    ORDER BY material_id
                    """,
                    (project_scope,),
                ).fetchall()
    except (UndefinedFunction, UndefinedTable) as exc:
        raise RuntimeError("LANTERN_CONTRACT_NOT_INSTALLED") from exc

    expected_count = int(cut["material_count"])
    if len(payload) != expected_count:
        raise ValueError("LANTERN_PAYLOAD_COUNT_MISMATCH")

    actual_members = [
        [
            row["material_id"],
            row["canonical_digest"],
            row["semantic_key"],
            row["source_digest"],
        ]
        for row in payload
    ]
    expected_members = cut["exact_members"]
    if actual_members != expected_members:
        raise ValueError("LANTERN_PAYLOAD_MEMBERSHIP_MISMATCH")

    for row in payload:
        if (
            row["profile_digest"] != cut["profile_digest"]
            or row["policy_digest"] != cut["policy_digest"]
        ):
            raise ValueError("LANTERN_PAYLOAD_BINDING_MISMATCH")

    subject = {
        "runtime_identity_digest": identity["identity_digest"],
        "project_scope": project_scope,
        "facade_id": cut["facade_id"],
        "profile_digest": cut["profile_digest"],
        "predecessor_digest": cut["predecessor_digest"],
        "policy_digest": cut["policy_digest"],
        "material_count": expected_count,
        "members_digest": canonical_digest(actual_members),
    }
    return {
        "schema": "SQL_CONNECTOME_LANTERN_CURRENT_CUT_V1",
        "runtime": identity,
        "cut": dict(cut),
        "payload": payload,
        "receipt": make_receipt("LANTERN_CURRENT_CUT", subject),
    }


def migration_status(settings: Settings) -> dict[str, Any]:
    with connect(settings) as conn:
        identity = _runtime_identity(conn)
        ledger = conn.execute(
            "SELECT to_regclass('sql_connectome.schema_migrations')::text AS ledger"
        ).fetchone()
        rows: list[dict[str, Any]] = []
        if ledger and ledger["ledger"]:
            rows = conn.execute(
                """
                SELECT version, checksum, source_path, applied_at
                FROM sql_connectome.schema_migrations
                ORDER BY version
                """
            ).fetchall()

    subject = {
        "runtime_identity_digest": identity["identity_digest"],
        "applied_count": len(rows),
        "migration_digest": canonical_digest(
            [[row["version"], row["checksum"], row["source_path"]] for row in rows]
        ),
    }
    return {
        "schema": "SQL_CONNECTOME_MIGRATION_STATUS_V1",
        "runtime": identity,
        "applied": rows,
        "receipt": make_receipt("MIGRATION_STATUS", subject),
    }
