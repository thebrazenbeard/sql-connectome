from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CorpusRecord:
    kind: str
    sql: str
    expected: tuple[str, ...] = ()
    supported: bool = True


def parse_sqllogictest(text: str) -> tuple[CorpusRecord, ...]:
    records: list[CorpusRecord] = []
    blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
    for block in blocks:
        lines = block.splitlines()
        header = lines[0].split()
        if not header:
            continue
        if header[0] == "statement" and len(lines) >= 2:
            records.append(CorpusRecord("statement", "\n".join(lines[1:])))
        elif header[0] == "query" and len(lines) >= 2:
            separator = lines.index("----") if "----" in lines else len(lines)
            sql = "\n".join(lines[1:separator])
            expected = tuple(lines[separator + 1 :]) if separator < len(lines) else ()
            records.append(CorpusRecord("query", sql, expected))
        else:
            records.append(CorpusRecord("unsupported", block, supported=False))
    return tuple(records)
