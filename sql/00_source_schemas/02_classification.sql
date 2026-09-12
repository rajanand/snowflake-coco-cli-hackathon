-- Phase 0: Sensitive-data classification check for SUPPLY_CHAIN.
-- Manual (exploratory) classification via SYSTEM$CLASSIFY — confirms no PII/sensitive
-- data is present in this synthetic supply-chain dataset, per Snowflake governance
-- best practice of classifying before deciding on masking/row-access policies.
--
-- Run after 01_governance_tags.sql. Read-only / exploratory — no auto_tag, no profile,
-- no ongoing monitoring is configured (not needed for static synthetic Phase 0 data;
-- revisit if SOURCE_* tables are ever fed by real production data).
USE ROLE SUPPLY_CHAIN_ADMIN;

CALL SYSTEM$CLASSIFY('SUPPLY_CHAIN.SOURCE_ERP.ORDERS', null);
CALL SYSTEM$CLASSIFY('SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.DELIVERIES', null);
CALL SYSTEM$CLASSIFY('SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.SHIPMENTS', null);
CALL SYSTEM$CLASSIFY('SUPPLY_CHAIN.SOURCE_FINANCE.DAILY_COGS', null);

-- Result (validated on last run): zero semantic/privacy category recommendations on any
-- column across all four representative tables — no PII detected. Free-text fields like
-- ORIGIN_SUPPLIER_NAME are business (organization) identifiers, not personal data.
--
-- To inspect full JSON results for a table:
-- SELECT SYSTEM$GET_CLASSIFICATION_RESULT('SUPPLY_CHAIN.SOURCE_ERP.ORDERS');
