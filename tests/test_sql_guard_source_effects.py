import pytest

from sql_connectome.sql_guard import SQLRejected, validate_readonly_sql


@pytest.mark.parametrize("statement", [
    "SELECT 1 INTO new_table",
    "SELECT * INTO TEMP TABLE copied_rows FROM source_rows",
])
def test_select_into_is_mutating_even_when_statement_starts_select(statement):
    with pytest.raises(SQLRejected, match="WRITE|INTO|ONLY_SELECT"):
        validate_readonly_sql(statement)


def test_into_word_inside_string_literal_is_not_mutation():
    assert validate_readonly_sql("SELECT 'INTO' AS literal") == "SELECT 'INTO' AS literal"
