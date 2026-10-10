import sqlparse
from sqlparse import tokens as T


class SQLRejected(ValueError):
    pass


def validate_readonly_sql(sql: str) -> str:
    text = sql.strip()
    if not text:
        raise SQLRejected("EMPTY_SQL")
    if "\x00" in text:
        raise SQLRejected("NUL_BYTE")

    statements = [stmt for stmt in sqlparse.parse(text) if str(stmt).strip()]
    if len(statements) != 1:
        raise SQLRejected("MULTI_STATEMENT")

    statement = statements[0]
    if statement.get_type().upper() != "SELECT":
        raise SQLRejected("ONLY_SELECT_ALLOWED")

    # PostgreSQL and other engines permit SELECT ... INTO as a table write.
    # Inspect parsed keywords, not raw text: literals and comments may say INTO.
    if any(
        token.ttype in T.Keyword and token.normalized == "INTO"
        for token in statement.flatten()
    ):
        raise SQLRejected("SELECT_INTO_IS_WRITE")

    return text
