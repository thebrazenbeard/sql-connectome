"""Source-only acceptance tests; this is NOT a public user-auth endpoint."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest

from sql_connectome.tenant_rls_candidate import (
    TenantPrincipal,
    authorize_principal,
    read_tenant_documents,
)

ISSUER = "https://id.example.invalid"
AUDIENCE = "sql-connectome-tenant-prototype"
TENANT_A = "11111111-1111-4111-8111-111111111111"


def _claims(**changes: Any) -> dict[str, Any]:
    claims = {
        "sub": "alice",
        "tenant_id": TENANT_A,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "nbf": 1000,
        "exp": 1200,
    }
    return {**claims, **changes}


class FixtureVerifier:
    """Test-only signature-verifier stand-in; NO runtime issuer is supplied."""

    def __init__(self, claims: dict[str, Any]) -> None:
        self.claims = claims

    def __call__(self, token: str) -> dict[str, Any]:
        if token != "fixture-authentic-token":
            raise ValueError("signature rejected")
        return self.claims


def _authorize(claims: dict[str, Any], token: str = "fixture-authentic-token"):
    return authorize_principal(
        token,
        FixtureVerifier(claims),
        expected_issuer=ISSUER,
        expected_audience=AUDIENCE,
        now=1100,
    )


def test_valid_fresh_verified_principal():
    principal = _authorize(_claims())
    assert principal.subject == "alice"
    assert str(principal.tenant_id) == TENANT_A


@pytest.mark.parametrize(
    ("claims", "token"),
    [
        (_claims(), "forged-token"),
        (_claims(exp=1100), "fixture-authentic-token"),
        (_claims(nbf=1101), "fixture-authentic-token"),
        (_claims(iss="https://evil.invalid"), "fixture-authentic-token"),
        (_claims(aud="other-resource"), "fixture-authentic-token"),
        (_claims(exp=True), "fixture-authentic-token"),
        (_claims(tenant_id="not-a-uuid"), "fixture-authentic-token"),
        (_claims(tenant_id="11111111111141118111111111111111"), "fixture-authentic-token"),
        (_claims(sub=""), "fixture-authentic-token"),
    ],
)
def test_unverified_stale_or_invalid_identity_is_denied(claims, token):
    with pytest.raises(PermissionError, match="TENANT_IDENTITY_REJECTED"):
        _authorize(claims, token)


def test_no_external_verifier_means_no_identity():
    with pytest.raises(PermissionError, match="TENANT_IDENTITY_REJECTED"):
        authorize_principal(
            "fixture-authentic-token",
            None,
            expected_issuer=ISSUER,
            expected_audience=AUDIENCE,
            now=1100,
        )


def test_read_route_disabled_by_default_even_with_identity():
    with pytest.raises(PermissionError, match="TENANT_RLS_DISABLED"):
        read_tenant_documents(
            None,
            "fixture-authentic-token",
            FixtureVerifier(_claims()),
            expected_issuer=ISSUER,
            expected_audience=AUDIENCE,
        )


def test_public_claims_dataclass_never_authorizes_read():
    forged = TenantPrincipal("mallory", UUID(TENANT_A), ISSUER, AUDIENCE, 1000, 1200)
    with pytest.raises(PermissionError, match="TENANT_IDENTITY_REJECTED"):
        read_tenant_documents(
            None,
            forged,
            FixtureVerifier(_claims()),
            expected_issuer=ISSUER,
            expected_audience=AUDIENCE,
            enabled=True,
        )


def test_read_route_rejects_expired_token_before_db_access():
    with pytest.raises(PermissionError, match="TENANT_IDENTITY_REJECTED"):
        read_tenant_documents(
            None,
            "fixture-authentic-token",
            FixtureVerifier(_claims(nbf=1, exp=2)),
            expected_issuer=ISSUER,
            expected_audience=AUDIENCE,
            enabled=True,
        )


def test_read_route_cannot_accept_caller_supplied_clock():
    with pytest.raises(TypeError, match="now"):
        read_tenant_documents(
            None,
            "fixture-authentic-token",
            FixtureVerifier(_claims(nbf=1, exp=2)),
            expected_issuer=ISSUER,
            expected_audience=AUDIENCE,
            enabled=True,
            now=1100,  # type: ignore[call-arg]
        )
