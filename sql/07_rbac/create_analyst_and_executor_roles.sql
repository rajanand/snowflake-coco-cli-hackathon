-- =============================================================================
-- Phase: RBAC least-privilege role split (Task 18 of the master plan)
-- =============================================================================
-- Purpose: today only SUPPLY_CHAIN_ADMIN exists, and it owns everything (it's
-- effectively an admin role used for all build work). This script adds two
-- narrower roles:
--   1. SUPPLY_CHAIN_ANALYST_RO  -- read-only consumption role. Grants match
--      what streamlit_app.py and agents/agent_router.py actually query today:
--      SOURCE_* (Act 1 divergence demo), SILVER.shipment_crosswalk, all GOLD
--      facts/dims, the SEMANTIC_MODELS semantic view, and the Cortex Search
--      service. See sql/07_rbac/README.md for the "semantic-layer only" caveat.
--   2. SUPPLY_CHAIN_TASK_EXECUTOR -- operational role sized for what
--      sql/09_ops/pause_resume_compute.sql already does (suspend/resume every
--      Silver/Gold Dynamic Table + the Cortex Search service + the warehouse)
--      plus EXECUTE TASK for near-term Task automation.
--
-- Neither role is wired into streamlit_app.py or agent_router.py yet -- both
-- still run as SUPPLY_CHAIN_ADMIN / the connection's default role. This script
-- only creates and grants the roles so they're ready for that follow-up.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Account-level grants require ACCOUNTADMIN
-- -----------------------------------------------------------------------------
USE ROLE ACCOUNTADMIN;

CREATE ROLE IF NOT EXISTS SUPPLY_CHAIN_ANALYST_RO
    COMMENT = 'Read-only consumption role for the supply chain ontology demo (Streamlit app, agent router). See sql/07_rbac/README.md.';

CREATE ROLE IF NOT EXISTS SUPPLY_CHAIN_TASK_EXECUTOR
    COMMENT = 'Operational role for pausing/resuming Dynamic Tables + Cortex Search, and running Tasks. See sql/07_rbac/README.md.';

GRANT ROLE SUPPLY_CHAIN_ANALYST_RO TO USER RAJANAND;
GRANT ROLE SUPPLY_CHAIN_TASK_EXECUTOR TO USER RAJANAND;

-- EXECUTE TASK is account-scoped and can only be granted by ACCOUNTADMIN.
GRANT EXECUTE TASK ON ACCOUNT TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;

-- -----------------------------------------------------------------------------
-- Object-level grants inside SUPPLY_CHAIN are owned by SUPPLY_CHAIN_ADMIN
-- -----------------------------------------------------------------------------
USE ROLE SUPPLY_CHAIN_ADMIN;

-- =============================================================================
-- SUPPLY_CHAIN_ANALYST_RO -- read-only
-- =============================================================================
GRANT USAGE ON DATABASE SUPPLY_CHAIN TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE SUPPLY_CHAIN_ANALYST_RO;

GRANT USAGE ON SCHEMA SUPPLY_CHAIN.SOURCE_ERP TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT USAGE ON SCHEMA SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT USAGE ON SCHEMA SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT USAGE ON SCHEMA SUPPLY_CHAIN.SOURCE_IOT_SENSOR TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT USAGE ON SCHEMA SUPPLY_CHAIN.SOURCE_FINANCE TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT USAGE ON SCHEMA SUPPLY_CHAIN.SILVER TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT USAGE ON SCHEMA SUPPLY_CHAIN.GOLD TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT USAGE ON SCHEMA SUPPLY_CHAIN.SEMANTIC_MODELS TO ROLE SUPPLY_CHAIN_ANALYST_RO;

-- SOURCE_* -- needed for the Act 1 "Before/Chaos" legacy divergence demo
GRANT SELECT ON ALL TABLES IN SCHEMA SUPPLY_CHAIN.SOURCE_ERP TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT SELECT ON FUTURE TABLES IN SCHEMA SUPPLY_CHAIN.SOURCE_ERP TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT SELECT ON ALL TABLES IN SCHEMA SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT SELECT ON FUTURE TABLES IN SCHEMA SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT SELECT ON ALL TABLES IN SCHEMA SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT SELECT ON FUTURE TABLES IN SCHEMA SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT SELECT ON ALL TABLES IN SCHEMA SUPPLY_CHAIN.SOURCE_IOT_SENSOR TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT SELECT ON FUTURE TABLES IN SCHEMA SUPPLY_CHAIN.SOURCE_IOT_SENSOR TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT SELECT ON ALL TABLES IN SCHEMA SUPPLY_CHAIN.SOURCE_FINANCE TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT SELECT ON FUTURE TABLES IN SCHEMA SUPPLY_CHAIN.SOURCE_FINANCE TO ROLE SUPPLY_CHAIN_ANALYST_RO;

-- SILVER -- needed for the entity-resolution proof (shipment_crosswalk).
-- NOTE: every object in SILVER is a Dynamic Table, not a plain TABLE --
-- "GRANT SELECT ON ALL TABLES" does NOT cover Dynamic Tables in this Snowflake
-- version (confirmed via SHOW GRANTS: it granted nothing here). Dynamic Tables
-- are a distinct grantable object type and need their own ALL/FUTURE grant.
GRANT SELECT ON ALL TABLES IN SCHEMA SUPPLY_CHAIN.SILVER TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT SELECT ON FUTURE TABLES IN SCHEMA SUPPLY_CHAIN.SILVER TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT SELECT ON ALL DYNAMIC TABLES IN SCHEMA SUPPLY_CHAIN.SILVER TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT SELECT ON FUTURE DYNAMIC TABLES IN SCHEMA SUPPLY_CHAIN.SILVER TO ROLE SUPPLY_CHAIN_ANALYST_RO;

-- GOLD -- the app's Acts 2-5 query these fact/dim tables directly.
-- Same dynamic-table caveat as SILVER; dim_date is the one plain TABLE here
-- (it's static, per sql/09_ops/pause_resume_compute.sql), everything else is
-- a Dynamic Table.
GRANT SELECT ON ALL TABLES IN SCHEMA SUPPLY_CHAIN.GOLD TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT SELECT ON FUTURE TABLES IN SCHEMA SUPPLY_CHAIN.GOLD TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT SELECT ON ALL DYNAMIC TABLES IN SCHEMA SUPPLY_CHAIN.GOLD TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT SELECT ON FUTURE DYNAMIC TABLES IN SCHEMA SUPPLY_CHAIN.GOLD TO ROLE SUPPLY_CHAIN_ANALYST_RO;

-- SEMANTIC_MODELS -- the governed consumption surface (Cortex Analyst + Search)
GRANT SELECT ON SEMANTIC VIEW SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT USAGE ON CORTEX SEARCH SERVICE SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_DOCUMENTS TO ROLE SUPPLY_CHAIN_ANALYST_RO;

-- =============================================================================
-- SUPPLY_CHAIN_TASK_EXECUTOR -- operational
-- =============================================================================
GRANT USAGE ON DATABASE SUPPLY_CHAIN TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;
GRANT USAGE, OPERATE ON WAREHOUSE COMPUTE_WH TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;

GRANT USAGE ON SCHEMA SUPPLY_CHAIN.SILVER TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;
GRANT USAGE ON SCHEMA SUPPLY_CHAIN.GOLD TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;
GRANT USAGE ON SCHEMA SUPPLY_CHAIN.SEMANTIC_MODELS TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;

-- OPERATE covers ALTER DYNAMIC TABLE ... SUSPEND/RESUME (pause_resume_compute.sql)
GRANT OPERATE ON ALL DYNAMIC TABLES IN SCHEMA SUPPLY_CHAIN.SILVER TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;
GRANT OPERATE ON FUTURE DYNAMIC TABLES IN SCHEMA SUPPLY_CHAIN.SILVER TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;
GRANT OPERATE ON ALL DYNAMIC TABLES IN SCHEMA SUPPLY_CHAIN.GOLD TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;
GRANT OPERATE ON FUTURE DYNAMIC TABLES IN SCHEMA SUPPLY_CHAIN.GOLD TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;

GRANT OPERATE ON CORTEX SEARCH SERVICE SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_DOCUMENTS TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;

-- NOTE: CREATE TASK / USAGE on an AUTOMATION schema is deliberately NOT granted
-- yet -- that schema doesn't exist (Gap 2 of the pending-gaps list is deferred).
-- Add "GRANT USAGE, CREATE TASK ON SCHEMA SUPPLY_CHAIN.AUTOMATION TO ROLE
-- SUPPLY_CHAIN_TASK_EXECUTOR;" when that work starts.

-- -----------------------------------------------------------------------------
-- Verification (already executed live -- see sql/07_rbac/README.md for results)
-- -----------------------------------------------------------------------------
-- SHOW GRANTS TO ROLE SUPPLY_CHAIN_ANALYST_RO;
-- SHOW GRANTS TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;
--
-- Negative test (proves least-privilege, not silently admin):
--   USE ROLE SUPPLY_CHAIN_ANALYST_RO;
--   CREATE TABLE SUPPLY_CHAIN.GOLD.SHOULD_FAIL_TEST (x INT);  -- must fail
--   SELECT COUNT(*) FROM SUPPLY_CHAIN.GOLD.fact_shipment;      -- must succeed
--
-- OPERATE test (TASK_EXECUTOR):
--   USE ROLE SUPPLY_CHAIN_TASK_EXECUTOR;
--   ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.dim_customer RESUME;
--   ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.dim_customer SUSPEND;  -- restore state
