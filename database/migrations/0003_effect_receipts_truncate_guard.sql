-- Close the TRUNCATE bypass for append-only effect receipts.
-- The pre-existing mutation rejection function always raises; PostgreSQL
-- requires a statement-level trigger for TRUNCATE (there are no row triggers).
-- Table owners/superusers may still disable or drop triggers: least-privilege
-- database grants and separate evidence custody remain mandatory.

DROP TRIGGER IF EXISTS effect_receipts_no_truncate_v1
    ON sql_connectome.effect_receipts;

CREATE TRIGGER effect_receipts_no_truncate_v1
BEFORE TRUNCATE ON sql_connectome.effect_receipts
FOR EACH STATEMENT
EXECUTE FUNCTION sql_connectome.reject_effect_receipt_mutation_v1();
