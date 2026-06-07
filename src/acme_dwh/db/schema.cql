-- Acme DWH schema. The keyspace is created by init_db.py (name/RF configurable),
-- which then applies these statements. All use IF NOT EXISTS (idempotent).

-- Asset: details/history. system_time DESC => latest version is the first row.
CREATE TABLE IF NOT EXISTS asset (
    id          text,
    system_time timestamp,
    name        text,
    description text,
    attributes  map<text, text>,
    deleted     boolean,
    PRIMARY KEY (id, system_time)
) WITH CLUSTERING ORDER BY (system_time DESC);

-- alphabetical, pageable asset ids in one partition (Cassandra has no OFFSET / ordered partition keys).
CREATE TABLE IF NOT EXISTS asset_ids (
    bucket text,
    id     text,
    PRIMARY KEY (bucket, id)
) WITH CLUSTERING ORDER BY (id ASC);

-- Data source: details/history.
CREATE TABLE IF NOT EXISTS data_source (
    id          text,
    system_time timestamp,
    name        text,
    description text,
    attributes  set<text>,
    deleted     boolean,
    PRIMARY KEY (id, system_time)
) WITH CLUSTERING ORDER BY (system_time DESC);

-- alphabetical, pageable data-source ids.
CREATE TABLE IF NOT EXISTS data_source_ids (
    bucket text,
    id     text,
    PRIMARY KEY (bucket, id)
) WITH CLUSTERING ORDER BY (id ASC);

-- Time series. Partition sharded by business year to stay bounded. Clustering by
-- (business_date DESC, system_time DESC) puts the newest day + newest version first.
-- Indicators are split by type into typed maps. deleted=true is a temporal tombstone.
CREATE TABLE IF NOT EXISTS data (
    asset_id           text,
    data_source_id     text,
    business_date_year int,
    business_date      date,
    system_time        timestamp,
    values_double      map<text, double>,
    values_int         map<text, bigint>,
    values_text        map<text, text>,
    deleted            boolean,
    PRIMARY KEY ((asset_id, data_source_id, business_date_year), business_date, system_time)
) WITH CLUSTERING ORDER BY (business_date DESC, system_time DESC);

-- Spark analytics outputs.
CREATE TABLE IF NOT EXISTS totals (
    asset_id           text,
    data_source_id     text,
    business_date_year int,
    cnt                bigint,
    min_close          double,
    max_close          double,
    avg_close          double,
    PRIMARY KEY ((asset_id, data_source_id), business_date_year)
) WITH CLUSTERING ORDER BY (business_date_year DESC);

CREATE TABLE IF NOT EXISTS regression_results (
    asset_id       text,
    data_source_id text,
    seconds        bigint,
    business_date  date,
    open           double,
    prediction     double,
    PRIMARY KEY ((asset_id, data_source_id), seconds)
);
