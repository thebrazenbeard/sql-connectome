import os

import pymysql
import pytest

from sql_connectome.mariadb_engine import validate_mariadb_readonly
from sql_connectome.mysql_engine import validate_mysql_readonly


def _connect(prefix: str):
    host = os.getenv(f"{prefix}_HOST")
    if not host:
        pytest.skip(f"{prefix}_HOST not set")
    return pymysql.connect(
        host=host,
        port=int(os.getenv(f"{prefix}_PORT", "3306")),
        user=os.getenv(f"{prefix}_USER", "root"),
        password=os.environ[f"{prefix}_PASSWORD"],
        database=os.getenv(f"{prefix}_DATABASE", "app"),
        autocommit=True,
    )


def test_mysql_adapter_against_real_engine() -> None:
    with _connect("SQL_CONNECTOME_MYSQL") as connection:
        result = validate_mysql_readonly("SELECT 1 AS value", connection=connection)
    assert result.status.value == "PASS"
    assert result.runtime.engine == "mysql"
    assert result.runtime.version
    assert result.query_executed is False
    assert result.native_payload


def test_mariadb_adapter_against_real_engine() -> None:
    with _connect("SQL_CONNECTOME_MARIADB") as connection:
        result = validate_mariadb_readonly("SELECT 1 AS value", connection=connection)
    assert result.status.value == "PASS"
    assert result.runtime.engine == "mariadb"
    assert result.runtime.version
    assert result.query_executed is False
    assert result.native_payload
