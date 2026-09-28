from sql_connectome.adversarial_generation import generate_bounded_case
from sql_connectome.conformance import conformance_case_digest
from sql_connectome.conformance_corpus import parse_sqllogictest


def test_generator_is_seed_deterministic() -> None:
    assert conformance_case_digest(generate_bounded_case(42)) == conformance_case_digest(
        generate_bounded_case(42)
    )
    assert conformance_case_digest(generate_bounded_case(42)) != conformance_case_digest(
        generate_bounded_case(43)
    )


def test_minimal_sqllogictest_records_preserve_expectations() -> None:
    records = parse_sqllogictest(
        "statement ok\nCREATE TABLE t(a INTEGER)\n\n"
        "query I\nSELECT 1\n----\n1\n\n"
        "hash-threshold 8"
    )
    assert records[0].kind == "statement"
    assert records[1].expected == ("1",)
    assert records[2].supported is False
