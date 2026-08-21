-- TPC-H supplier-selection schema for the Table 8 / RQ1 experiment (§5.2).
--
-- This is the exact schema baked into `data/tpch.db`, extracted here so the
-- feature definitions are visible and reproducible (rather than hidden inside
-- the binary DB). The DB ships ready-to-use; you only need this file if you
-- want to rebuild it from freshly generated TPC-H base tables.
--
-- Base tables hold a scale-factor 0.01 TPC-H instance: 100 suppliers,
-- 25 nations, 8000 partsupp rows. To regenerate them, run the TPC-H `dbgen`
-- tool (SF 0.01) and load supplier.tbl / nation.tbl / partsupp.tbl, then
-- execute the view definitions below:
--
--     sqlite3 data/tpch.db < data/tpch_schema.sql
--
-- The `SupplierFeatures` view is what experiments/run_table8_tpch.py reads.
-- These are the feature definitions used for the paper's Table 8: each
-- supplier is scored on five features, normalized to roughly [0, 1] using
-- aggregates over PARTSUPP:
--   price_score        - normalized (inverted) avg supply cost from PARTSUPP
--   availability_score - normalized avg available quantity from PARTSUPP
--   region_america     - 1.0 if the supplier's nation is in region 1
--   region_europe      - 1.0 if the supplier's nation is in region 3
--   balance_score      - normalized supplier account balance
-- plus `count` (bundle cardinality), enforced in the experiment itself.

-- ---------------------------------------------------------------------------
-- Base tables
-- ---------------------------------------------------------------------------
CREATE TABLE NATION (
    N_NATIONKEY  INTEGER PRIMARY KEY,
    N_NAME       TEXT,
    N_REGIONKEY  INTEGER,
    N_COMMENT    TEXT
);

CREATE TABLE PARTSUPP (
    PS_PARTKEY     INTEGER,
    PS_SUPPKEY     INTEGER,
    PS_AVAILQTY    INTEGER,
    PS_SUPPLYCOST  REAL,
    PS_COMMENT     TEXT,
    PRIMARY KEY (PS_PARTKEY, PS_SUPPKEY)
);

CREATE TABLE SUPPLIER (
    S_SUPPKEY     INTEGER PRIMARY KEY,
    S_NAME        TEXT,
    S_ADDRESS     TEXT,
    S_NATIONKEY   INTEGER,
    S_PHONE       TEXT,
    S_ACCTBAL     REAL,
    S_COMMENT     TEXT
);

-- ---------------------------------------------------------------------------
-- Feature views (created in dependency order: V_STATS -> V_BOUNDS -> features)
-- ---------------------------------------------------------------------------
CREATE VIEW V_STATS AS
SELECT PS_SUPPKEY, AVG(PS_SUPPLYCOST) as avg_cost, AVG(PS_AVAILQTY) as avg_qty
FROM PARTSUPP GROUP BY PS_SUPPKEY;

CREATE VIEW V_BOUNDS AS
SELECT
MIN(avg_cost) as min_c, MAX(avg_cost) as max_c,
MAX(avg_qty) as max_q,
MIN(S_ACCTBAL) as min_b, MAX(S_ACCTBAL) as max_b
FROM V_STATS, SUPPLIER;

CREATE VIEW SupplierFeatures AS
SELECT
S.S_SUPPKEY as supplier_id,
S.S_NAME as name,
(B.max_c - ST.avg_cost) / (B.max_c - B.min_c) as price_score,
ST.avg_qty / B.max_q as availability_score,
CASE WHEN N.N_REGIONKEY = 1 THEN 1.0 ELSE 0.0 END as region_america,
CASE WHEN N.N_REGIONKEY = 3 THEN 1.0 ELSE 0.0 END as region_europe,
(S.S_ACCTBAL - B.min_b) / (B.max_b - B.min_b) as balance_score
FROM SUPPLIER S, NATION N, V_STATS ST, V_BOUNDS B
WHERE S.S_NATIONKEY = N.N_NATIONKEY
AND S.S_SUPPKEY = ST.PS_SUPPKEY;
