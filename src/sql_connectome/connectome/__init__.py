from .binding import bind_sql_text
from .catalog import (
    DEFAULT_CATALOG,
    DEFAULT_PARSER_ADAPTERS,
    ConnectomeCatalog,
)
from .compare import compare_dialects
from .ir import IREdge, IRNode, SQLSemanticIR, TranslationLoss
from .model import (
    AppliedRewrite,
    DialectGenome,
    RewriteRule,
    SemanticDimension,
    TranslationFidelity,
    TranslationPlan,
)
from .operations import (
    DEFAULT_OPERATION_CATALOG,
    DeterminismClass,
    EvaluationClass,
    OperationCatalog,
    OperationKind,
    OperationSpec,
    operation_catalog_payload,
    operation_graph,
)
from .planner import list_dialects, plan_translation
from .probe import DialectCandidate, probe_sql_dialects
from .registry import DEFAULT_DIALECTS, DEFAULT_REWRITE_RULES, resolve_dialect
from .semantics import (
    SemanticRisk,
    assess_expression_semantics,
    combined_fidelity,
    dialect_semantic_profile,
)
from .text_pipeline import (
    SQLTextAnalysis,
    SQLTextError,
    inspect_operation_catalog,
    inspect_operation_graph,
    inspect_sql_contracts,
    inspect_type_system,
    parse_sql_text,
    transpile_sql_text,
)
from .type_system import (
    CanonicalTypeFamily,
    TypeProjectionRisk,
    assess_type_semantics,
    canonical_type_family,
    dialect_type_graph,
)

__all__ = [
    "AppliedRewrite",
    "operation_graph",
    "operation_catalog_payload",
    "inspect_operation_graph",
    "inspect_operation_catalog",
    "OperationSpec",
    "OperationKind",
    "OperationCatalog",
    "EvaluationClass",
    "DeterminismClass",
    "DEFAULT_OPERATION_CATALOG",
    "inspect_type_system",
    "dialect_type_graph",
    "canonical_type_family",
    "assess_type_semantics",
    "TypeProjectionRisk",
    "CanonicalTypeFamily",
    "bind_sql_text",
    "ConnectomeCatalog",
    "DEFAULT_CATALOG",
    "DEFAULT_DIALECTS",
    "DEFAULT_PARSER_ADAPTERS",
    "DEFAULT_REWRITE_RULES",
    "DialectCandidate",
    "DialectGenome",
    "IREdge",
    "IRNode",
    "RewriteRule",
    "SemanticRisk",
    "SQLSemanticIR",
    "SQLTextAnalysis",
    "SQLTextError",
    "SemanticDimension",
    "TranslationFidelity",
    "TranslationLoss",
    "TranslationPlan",
    "assess_expression_semantics",
    "combined_fidelity",
    "compare_dialects",
    "dialect_semantic_profile",
    "inspect_sql_contracts",
    "list_dialects",
    "parse_sql_text",
    "plan_translation",
    "probe_sql_dialects",
    "resolve_dialect",
    "transpile_sql_text",
]
