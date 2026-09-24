from sql_connectome.connectome import inspect_sql_contracts


def _contracts_by_name(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    contracts = payload["expression_contracts"]
    assert isinstance(contracts, list)
    return {str(row["name"]): row for row in contracts}


def test_contracts_expose_fixed_and_inferred_type_rules() -> None:
    payload = inspect_sql_contracts(
        "SELECT LENGTH(name), LEAST(score, fallback_score) FROM results",
        "postgresql",
    )
    contracts = _contracts_by_name(payload)

    assert contracts["LENGTH"]["type_rule"] == "FIXED_RETURN"
    assert contracts["LENGTH"]["fixed_return_type"] == "INT"
    assert contracts["LEAST"]["type_rule"] == "INFERRED"
    assert contracts["LEAST"]["fixed_return_type"] is None


def test_contracts_expose_expression_argument_shape() -> None:
    payload = inspect_sql_contracts("SELECT COALESCE(a, b, c) FROM t", "postgresql")
    contracts = _contracts_by_name(payload)
    coalesce = contracts["COALESCE"]

    assert "this" in coalesce["required_args"]
    assert coalesce["variable_length_args"] is True
    assert coalesce["variable_length_arg_key"] == "expressions"


def test_contracts_include_dialect_coercion_graph() -> None:
    payload = inspect_sql_contracts("SELECT 1", "postgresql")

    assert payload["source"] == "SQLGLOT_EXPRESSION_METADATA"
    assert payload["sqlglot_version"]
    assert isinstance(payload["coercions"], list)


def test_contracts_are_query_scoped() -> None:
    payload = inspect_sql_contracts("SELECT ABS(x) FROM t", "postgresql")
    names = {row["name"] for row in payload["expression_contracts"]}

    assert "ABS" in names
    assert "LEAST" not in names
