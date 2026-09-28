from __future__ import annotations

import random

from .conformance import ComparisonMode, ComparisonPolicy, ConformanceCase


def generate_bounded_case(seed: int) -> ConformanceCase:
    rng = random.Random(seed)
    values: list[str] = []
    for _ in range(6):
        choice = rng.randrange(3)
        if choice == 0:
            values.append("NULL")
        elif choice == 1:
            values.append(str(rng.randint(-5, 5)))
        else:
            text = f"v{rng.randint(0, 4)}".replace("'", "''")
            values.append(f"'{text}'")
    inserts = ", ".join(f"({value})" for value in values)
    return ConformanceCase(
        case_id=f"generated-{seed}",
        seed=seed,
        setup_sql=(
            "CREATE TABLE generated(v)",
            f"INSERT INTO generated VALUES {inserts}",
        ),
        source_sql="SELECT v FROM generated",
        transformed_sql="SELECT v FROM (SELECT v FROM generated) q",
        comparison_policy=ComparisonPolicy(ComparisonMode.BAG),
        assumptions=("bounded integer/text/null generator", "no oracle claim"),
    )
