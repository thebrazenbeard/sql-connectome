CREATE SCHEMA IF NOT EXISTS sql_connectome;

CREATE TABLE IF NOT EXISTS sql_connectome.schema_migrations (
    version text PRIMARY KEY,
    checksum text NOT NULL,
    source_path text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS sql_connectome.effect_receipts (
    receipt_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_schema text NOT NULL,
    effect_kind text NOT NULL,
    subject_digest text NOT NULL,
    subject jsonb NOT NULL,
    result jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS effect_receipts_subject_digest_idx
    ON sql_connectome.effect_receipts(subject_digest);

CREATE TABLE IF NOT EXISTS sql_connectome.platform_metadata (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    platform_schema text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO sql_connectome.platform_metadata(singleton, platform_schema)
VALUES (true, 'SQL_CONNECTOME_PLATFORM_V1')
ON CONFLICT (singleton)
DO UPDATE SET platform_schema = EXCLUDED.platform_schema,
              updated_at = clock_timestamp();
