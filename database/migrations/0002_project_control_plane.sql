-- SQL Connectome project/database control plane V1.
-- Provider metadata is descriptive. Provider identity never defines SQL semantics.

CREATE TABLE sql_connectome.projects (
    project_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_key text NOT NULL UNIQUE
        CHECK (project_key ~ '^[a-z][a-z0-9-]{0,62}$'),
    display_name text NOT NULL CHECK (btrim(display_name) <> ''),
    lifecycle_state text NOT NULL DEFAULT 'ACTIVE'
        CHECK (lifecycle_state IN ('ACTIVE', 'SUSPENDED', 'ARCHIVED')),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(metadata) = 'object'),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE sql_connectome.database_targets (
    target_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL
        REFERENCES sql_connectome.projects(project_id) ON DELETE RESTRICT,
    target_key text NOT NULL
        CHECK (target_key ~ '^[a-z][a-z0-9-]{0,62}$'),
    target_role text NOT NULL DEFAULT 'PRIMARY'
        CHECK (target_role IN ('PRIMARY', 'REPLICA', 'ANALYTICS', 'ARCHIVE')),
    engine text NOT NULL DEFAULT 'postgresql' CHECK (btrim(engine) <> ''),
    provider_kind text NOT NULL CHECK (btrim(provider_kind) <> ''),
    provider_resource_ref text,
    database_name text NOT NULL CHECK (btrim(database_name) <> ''),
    region text,
    lifecycle_state text NOT NULL DEFAULT 'REGISTERED'
        CHECK (
            lifecycle_state IN (
                'REGISTERED',
                'PROVISIONING',
                'RUNNING',
                'DEGRADED',
                'STOPPED',
                'RETIRED',
                'UNKNOWN'
            )
        ),
    capabilities jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(capabilities) = 'object'),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(metadata) = 'object'),
    observed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (project_id, target_key)
);

CREATE UNIQUE INDEX database_targets_one_live_primary_v1
    ON sql_connectome.database_targets(project_id)
    WHERE target_role = 'PRIMARY' AND lifecycle_state <> 'RETIRED';

CREATE INDEX database_targets_project_state_v1
    ON sql_connectome.database_targets(project_id, lifecycle_state, target_key);

CREATE OR REPLACE FUNCTION sql_connectome.reject_effect_receipt_mutation_v1()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    RAISE EXCEPTION 'SQL_CONNECTOME_EFFECT_RECEIPTS_ARE_APPEND_ONLY';
END
$function$;

DROP TRIGGER IF EXISTS effect_receipts_no_update_delete_v1
    ON sql_connectome.effect_receipts;

CREATE TRIGGER effect_receipts_no_update_delete_v1
BEFORE UPDATE OR DELETE ON sql_connectome.effect_receipts
FOR EACH ROW
EXECUTE FUNCTION sql_connectome.reject_effect_receipt_mutation_v1();
