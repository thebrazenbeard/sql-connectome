from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .config import Settings
from .db import _runtime_identity, connect
from .receipts import canonical_digest, make_receipt


class ProjectRegistryError(RuntimeError):
    pass


def _effect_receipt(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    effect_kind: str,
    subject: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    subject_digest = canonical_digest(subject)
    row = conn.execute(
        """
        INSERT INTO sql_connectome.effect_receipts(
            receipt_schema,
            effect_kind,
            subject_digest,
            subject,
            result
        )
        VALUES (
            'SQL_CONNECTOME_EFFECT_RECEIPT_V1',
            %s,
            %s,
            %s::jsonb,
            %s::jsonb
        )
        RETURNING receipt_id::text, created_at
        """,
        (effect_kind, subject_digest, Jsonb(subject), Jsonb(result)),
    ).fetchone()
    assert row is not None
    return {
        "receipt_id": row["receipt_id"],
        "receipt_schema": "SQL_CONNECTOME_EFFECT_RECEIPT_V1",
        "effect_kind": effect_kind,
        "subject_digest": subject_digest,
        "created_at": row["created_at"],
    }


def register_project(
    database_url: str,
    *,
    project_key: str,
    display_name: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    subject = {
        "project_key": project_key,
        "display_name": display_name,
        "metadata": metadata,
    }

    with psycopg.connect(
        database_url,
        autocommit=False,
        row_factory=dict_row,
        application_name="sql-connectome-project-operator",
    ) as conn:
        with conn.transaction():
            row = conn.execute(
                """
                INSERT INTO sql_connectome.projects(project_key, display_name, metadata)
                VALUES (%s, %s, %s::jsonb)
                ON CONFLICT (project_key) DO NOTHING
                RETURNING project_id::text, project_key, display_name, lifecycle_state, metadata
                """,
                (project_key, display_name, Jsonb(metadata)),
            ).fetchone()

            if row is None:
                existing = conn.execute(
                    """
                    SELECT project_id::text, project_key, display_name, lifecycle_state, metadata
                    FROM sql_connectome.projects
                    WHERE project_key = %s
                    """,
                    (project_key,),
                ).fetchone()
                if existing is None:
                    raise ProjectRegistryError("PROJECT_REGISTRATION_LOST")
                if existing["display_name"] != display_name or existing["metadata"] != metadata:
                    raise ProjectRegistryError("PROJECT_KEY_CONFLICT")
                row = existing
                effect_state = "ALREADY_REGISTERED"
            else:
                effect_state = "REGISTERED"

            result = {
                "state": effect_state,
                "project_id": row["project_id"],
                "project_key": row["project_key"],
            }
            receipt = _effect_receipt(
                conn,
                effect_kind="PROJECT_REGISTER",
                subject=subject,
                result=result,
            )

    return {
        "schema": "SQL_CONNECTOME_PROJECT_REGISTRATION_V1",
        "state": effect_state,
        "project": dict(row),
        "receipt": receipt,
    }


def register_database_target(
    database_url: str,
    *,
    project_key: str,
    target_key: str,
    provider_kind: str,
    database_name: str,
    target_role: str = "PRIMARY",
    engine: str = "postgresql",
    provider_resource_ref: str | None = None,
    region: str | None = None,
    lifecycle_state: str = "REGISTERED",
    capabilities: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    capabilities = capabilities or {}
    metadata = metadata or {}
    subject = {
        "project_key": project_key,
        "target_key": target_key,
        "target_role": target_role,
        "engine": engine,
        "provider_kind": provider_kind,
        "provider_resource_ref": provider_resource_ref,
        "database_name": database_name,
        "region": region,
        "lifecycle_state": lifecycle_state,
        "capabilities": capabilities,
        "metadata": metadata,
    }

    with psycopg.connect(
        database_url,
        autocommit=False,
        row_factory=dict_row,
        application_name="sql-connectome-target-operator",
    ) as conn:
        with conn.transaction():
            project = conn.execute(
                """
                SELECT project_id::text, project_key
                FROM sql_connectome.projects
                WHERE project_key = %s
                """,
                (project_key,),
            ).fetchone()
            if project is None:
                raise ProjectRegistryError("PROJECT_NOT_FOUND")

            row = conn.execute(
                """
                INSERT INTO sql_connectome.database_targets(
                    project_id,
                    target_key,
                    target_role,
                    engine,
                    provider_kind,
                    provider_resource_ref,
                    database_name,
                    region,
                    lifecycle_state,
                    capabilities,
                    metadata
                )
                VALUES (
                    %s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb
                )
                ON CONFLICT (project_id, target_key) DO NOTHING
                RETURNING
                    target_id::text,
                    target_key,
                    target_role,
                    engine,
                    provider_kind,
                    provider_resource_ref,
                    database_name,
                    region,
                    lifecycle_state,
                    capabilities,
                    metadata
                """,
                (
                    project["project_id"],
                    target_key,
                    target_role,
                    engine,
                    provider_kind,
                    provider_resource_ref,
                    database_name,
                    region,
                    lifecycle_state,
                    Jsonb(capabilities),
                    Jsonb(metadata),
                ),
            ).fetchone()

            if row is None:
                existing = conn.execute(
                    """
                    SELECT
                        target_id::text,
                        target_key,
                        target_role,
                        engine,
                        provider_kind,
                        provider_resource_ref,
                        database_name,
                        region,
                        lifecycle_state,
                        capabilities,
                        metadata
                    FROM sql_connectome.database_targets
                    WHERE project_id = %s::uuid AND target_key = %s
                    """,
                    (project["project_id"], target_key),
                ).fetchone()
                if existing is None:
                    raise ProjectRegistryError("TARGET_REGISTRATION_LOST")

                comparable = {
                    key: existing[key]
                    for key in (
                        "target_key",
                        "target_role",
                        "engine",
                        "provider_kind",
                        "provider_resource_ref",
                        "database_name",
                        "region",
                        "lifecycle_state",
                        "capabilities",
                        "metadata",
                    )
                }
                expected = {key: subject[key] for key in comparable}
                if comparable != expected:
                    raise ProjectRegistryError("TARGET_KEY_CONFLICT")
                row = existing
                effect_state = "ALREADY_REGISTERED"
            else:
                effect_state = "REGISTERED"

            result = {
                "state": effect_state,
                "project_key": project_key,
                "target_id": row["target_id"],
                "target_key": row["target_key"],
            }
            receipt = _effect_receipt(
                conn,
                effect_kind="DATABASE_TARGET_REGISTER",
                subject=subject,
                result=result,
            )

    return {
        "schema": "SQL_CONNECTOME_DATABASE_TARGET_REGISTRATION_V1",
        "state": effect_state,
        "project_key": project_key,
        "target": dict(row),
        "receipt": receipt,
    }


def list_projects(settings: Settings) -> dict[str, Any]:
    with connect(settings) as conn:
        identity = _runtime_identity(conn)
        rows = conn.execute(
            """
            SELECT
                p.project_id::text,
                p.project_key,
                p.display_name,
                p.lifecycle_state,
                p.metadata,
                p.created_at,
                p.updated_at,
                count(t.target_id)::int AS target_count
            FROM sql_connectome.projects p
            LEFT JOIN sql_connectome.database_targets t ON t.project_id = p.project_id
            GROUP BY p.project_id
            ORDER BY p.project_key
            """
        ).fetchall()

    subject = {
        "runtime_identity_digest": identity["identity_digest"],
        "project_count": len(rows),
        "project_keys": [row["project_key"] for row in rows],
    }
    return {
        "schema": "SQL_CONNECTOME_PROJECT_LIST_V1",
        "runtime": identity,
        "projects": rows,
        "count": len(rows),
        "receipt": make_receipt("PROJECT_LIST", subject),
    }


def project_detail(settings: Settings, project_key: str) -> dict[str, Any]:
    with connect(settings) as conn:
        identity = _runtime_identity(conn)
        project = conn.execute(
            """
            SELECT
                project_id::text,
                project_key,
                display_name,
                lifecycle_state,
                metadata,
                created_at,
                updated_at
            FROM sql_connectome.projects
            WHERE project_key = %s
            """,
            (project_key,),
        ).fetchone()
        if project is None:
            raise ProjectRegistryError("PROJECT_NOT_FOUND")

        targets = conn.execute(
            """
            SELECT
                target_id::text,
                target_key,
                target_role,
                engine,
                provider_kind,
                provider_resource_ref,
                database_name,
                region,
                lifecycle_state,
                capabilities,
                metadata,
                observed_at,
                created_at,
                updated_at
            FROM sql_connectome.database_targets
            WHERE project_id = %s::uuid
            ORDER BY
                CASE target_role
                    WHEN 'PRIMARY' THEN 1
                    WHEN 'REPLICA' THEN 2
                    WHEN 'ANALYTICS' THEN 3
                    ELSE 4
                END,
                target_key
            """,
            (project["project_id"],),
        ).fetchall()

    subject = {
        "runtime_identity_digest": identity["identity_digest"],
        "project_id": project["project_id"],
        "project_key": project_key,
        "target_ids": [row["target_id"] for row in targets],
        "target_count": len(targets),
    }
    return {
        "schema": "SQL_CONNECTOME_PROJECT_DETAIL_V1",
        "runtime": identity,
        "project": project,
        "targets": targets,
        "receipt": make_receipt("PROJECT_DETAIL", subject),
    }
