"""Operator configuration cannot silently disable bounded PostgreSQL reads."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sql_connectome.config import Settings


def _settings(**overrides: object) -> Settings:
    return Settings(
        database_url="postgresql://unused:unused@localhost/unused",
        api_token="isolated-test-token",
        **overrides,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("statement_timeout_ms", -1),
        ("statement_timeout_ms", 0),
        ("statement_timeout_ms", 60_001),
        ("statement_timeout_ms", 10**100),
        ("statement_timeout_ms", "not-an-integer"),
        ("max_rows", -1),
        ("max_rows", 0),
        ("max_rows", 10_001),
        ("max_rows", 10**100),
        ("max_rows", "not-an-integer"),
    ],
)
def test_invalid_query_bounds_rejected_at_initialization(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        _settings(**{field: value})


@pytest.mark.parametrize(
    ("environment_key", "value"),
    [
        ("SQL_CONNECTOME_STATEMENT_TIMEOUT_MS", "0"),
        ("SQL_CONNECTOME_STATEMENT_TIMEOUT_MS", "-7"),
        ("SQL_CONNECTOME_STATEMENT_TIMEOUT_MS", "60001"),
        ("SQL_CONNECTOME_STATEMENT_TIMEOUT_MS", "garbage"),
        ("SQL_CONNECTOME_MAX_ROWS", "0"),
        ("SQL_CONNECTOME_MAX_ROWS", "-7"),
        ("SQL_CONNECTOME_MAX_ROWS", "10001"),
        ("SQL_CONNECTOME_MAX_ROWS", "garbage"),
    ],
)
def test_invalid_environment_query_bounds_fail_closed(
    monkeypatch: pytest.MonkeyPatch, environment_key: str, value: str
) -> None:
    monkeypatch.delenv("SQL_CONNECTOME_STATEMENT_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("SQL_CONNECTOME_MAX_ROWS", raising=False)
    monkeypatch.setenv(environment_key, value)
    with pytest.raises(ValidationError):
        _settings()


@pytest.mark.parametrize(
    ("timeout", "rows"),
    [(1, 1), (5_000, 500), (60_000, 10_000)],
)
def test_query_bounds_accept_valid_extremes(timeout: int, rows: int) -> None:
    settings = _settings(statement_timeout_ms=timeout, max_rows=rows)
    assert settings.statement_timeout_ms == timeout
    assert settings.max_rows == rows


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [("statement_timeout_ms", 0), ("max_rows", 0)],
)
def test_query_bounds_reject_invalid_assignment(field: str, bad_value: int) -> None:
    settings = _settings()
    old_value = getattr(settings, field)
    with pytest.raises(ValidationError):
        setattr(settings, field, bad_value)
    assert getattr(settings, field) == old_value
