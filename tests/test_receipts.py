from sql_connectome.receipts import canonical_digest, make_receipt


def test_canonical_digest_is_key_order_independent() -> None:
    assert canonical_digest({"a": 1, "b": 2}) == canonical_digest({"b": 2, "a": 1})


def test_receipt_is_deterministic_for_fixed_timestamp() -> None:
    one = make_receipt("TEST", {"x": 1}, issued_at="2026-09-24T00:00:00+00:00")
    two = make_receipt("TEST", {"x": 1}, issued_at="2026-09-24T00:00:00+00:00")
    assert one == two
    assert len(one["receipt_digest"]) == 64
