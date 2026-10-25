"""Unwired, opt-in tenant/RLS reference. NOT a public Auth or SQL API.

An independently trusted issuer verifier must validate token signature,
algorithm, key selection, revocation, and issuer keys *before* returning claims.
This module only checks the returned claim binding and uses a dedicated,
non-owner PostgreSQL LOGIN under a fixed SQL read. PostgreSQL custom GUCs
are user-settable: never expose these credentials or arbitrary caller SQL.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from psycopg.pq import TransactionStatus


@dataclass(frozen=True)
class TenantPrincipal:
    subject: str
    tenant_id: UUID
    issuer: str
    audience: str
    not_before: int
    expires_at: int


def _reject() -> None:
    raise PermissionError("TENANT_IDENTITY_REJECTED")


def authorize_principal(
    token: str,
    verified_claims: Callable[[str], dict[str, Any]] | None,
    *,
    expected_issuer: str,
    expected_audience: str,
    now: int | None = None,
) -> TenantPrincipal:
    """Admit ONLY an externally verified token's exact, fresh tenant claims.

    The callback must perform real cryptographic verification. An application
    must not pass unverified decoded JWT claims as this callback's output.
    No callback is configured or called by the existing REST/MCP endpoints.
    """
    if (
        type(token) is not str
        or not token
        or len(token) > 8192
        or any(ord(char) < 33 or ord(char) > 126 for char in token)
        or not callable(verified_claims)
        or not expected_issuer
        or not expected_audience
    ):
        _reject()
    try:
        claims = verified_claims(token)
        if type(claims) is not dict:
            _reject()
        subject = claims["sub"]
        tenant_text = claims["tenant_id"]
        not_before = claims["nbf"]
        expires_at = claims["exp"]
        if (
            type(subject) is not str
            or not (1 <= len(subject) <= 128)
            or any(ord(char) < 33 or ord(char) > 126 for char in subject)
            or type(tenant_text) is not str
            or type(not_before) is not int
            or type(expires_at) is not int
            or claims["iss"] != expected_issuer
            or claims["aud"] != expected_audience
        ):
            _reject()
        tenant_id = UUID(tenant_text)
        if str(tenant_id) != tenant_text:
            _reject()
        instant = int(time.time()) if now is None else now
        if type(instant) is not int or not_before > instant or expires_at <= instant:
            _reject()
        return TenantPrincipal(
            subject, tenant_id, expected_issuer, expected_audience, not_before, expires_at
        )
    except Exception:
        # Do not leak token contents, verifier exceptions, or key details.
        _reject()


def read_tenant_documents(
    connection: Any,
    token: str,
    verified_claims: Callable[[str], dict[str, Any]] | None,
    *,
    expected_issuer: str,
    expected_audience: str,
    enabled: bool = False,
) -> list[dict[str, Any]]:
    """Fixed-table RLS probe, requiring a dedicated LOGIN and fresh tx scope.

    `connection` must be a private dict-row psycopg connection, never a public
    SQL session. The fixed fixture schema is not a production data API.
    """
    if enabled is not True:
        raise PermissionError("TENANT_RLS_DISABLED")
    # A public claims dataclass is evidence only, never authority. Reverify
    # the raw token at the read entrypoint; no caller-supplied tenant override.
    principal = authorize_principal(
        token,
        verified_claims,
        expected_issuer=expected_issuer,
        expected_audience=expected_audience,
    )
    if connection.info.transaction_status != TransactionStatus.IDLE:
        raise PermissionError("TENANT_RLS_TRANSACTION_NOT_IDLE")

    with connection.transaction():
        connection.execute("SET TRANSACTION READ ONLY")
        connection.execute("SELECT set_config('row_security', 'on', true)")
        acl = connection.execute(
            """
            SELECT r.rolsuper, r.rolbypassrls, r.rolinherit, r.rolcanlogin,
                   r.rolcreaterole, r.rolcreatedb, r.rolreplication,
                   (c.relowner = r.oid) AS table_owner,
                   c.relrowsecurity, c.relforcerowsecurity,
                   pg_catalog.pg_has_role(r.rolname, c.relowner, 'SET') AS can_set_owner,
                   EXISTS (
                     SELECT 1 FROM pg_catalog.pg_auth_members AS m
                     WHERE m.member = r.oid
                   ) AS has_role_membership
            FROM pg_catalog.pg_roles AS r
            JOIN pg_catalog.pg_namespace AS n ON n.nspname = 'sql_connectome_rls_ci'
            JOIN pg_catalog.pg_class AS c ON c.relnamespace = n.oid
            WHERE r.rolname = current_user AND session_user = current_user
              AND c.relname = 'tenant_documents' AND c.relkind = 'r'
            """
        ).fetchone()
        if (
            acl is None
            or acl["rolsuper"]
            or acl["rolbypassrls"]
            or acl["rolinherit"]
            or acl["rolcreaterole"]
            or acl["rolcreatedb"]
            or acl["rolreplication"]
            or not acl["rolcanlogin"]
            or acl["table_owner"]
            or not acl["relrowsecurity"]
            or not acl["relforcerowsecurity"]
            or acl["can_set_owner"]
            or acl["has_role_membership"]
        ):
            raise PermissionError("TENANT_RLS_ROLE_NOT_ISOLATED")

        connection.execute(
            "SELECT set_config('sql_connectome.tenant_id', %s, true)",
            (str(principal.tenant_id),),
        )
        # No tenant WHERE is used: PostgreSQL's actual RLS policy must filter.
        records = connection.execute(
            "SELECT document_id, tenant_id::text AS tenant_id, body "
            "FROM sql_connectome_rls_ci.tenant_documents ORDER BY document_id LIMIT 101"
        ).fetchall()
        if len(records) > 100:
            raise ValueError("TENANT_RLS_RESULT_LIMIT_EXCEEDED")
        # RLS enabled/FORCE flags cannot prove its policy is restrictive:
        # permissive policies combine with OR. Reject the *entire* result on
        # one wrong-tenant row; never silently filter a leaked row in Python.
        if any(row.get("tenant_id") != str(principal.tenant_id) for row in records):
            raise PermissionError("TENANT_RLS_POLICY_DRIFT")
        return list(records)
