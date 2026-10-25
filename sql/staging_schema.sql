-- ============================================================
-- Retail & Sales Intelligence Platform
-- staging_schema.sql — Schéma de staging PostgreSQL
-- ============================================================
-- Ce schéma reçoit les données nettoyées avant chargement DWH.
-- Chaque table staging reflète la structure d'un dataset source.
-- Les tables sont recréées à chaque exécution du pipeline (REPLACE).
-- ============================================================

-- Création du schéma staging
CREATE SCHEMA IF NOT EXISTS staging;

-- ── Table : stg_orders ────────────────────────────────────────────────────────
DROP TABLE IF EXISTS staging.stg_orders CASCADE;
CREATE TABLE staging.stg_orders (
    order_id                        VARCHAR(64)  NOT NULL,
    customer_id                     VARCHAR(64)  NOT NULL,
    order_status                    VARCHAR(32),
    order_purchase_timestamp        TIMESTAMP,
    order_approved_at               TIMESTAMP,
    order_delivered_carrier_date    TIMESTAMP,
    order_delivered_customer_date   TIMESTAMP,
    order_estimated_delivery_date   TIMESTAMP,
    delivery_days                   NUMERIC(10, 2),
    is_on_time                      SMALLINT,
    delay_days                      NUMERIC(10, 2),
    CONSTRAINT stg_orders_pk PRIMARY KEY (order_id)
);

COMMENT ON TABLE staging.stg_orders IS 'Données nettoyées des commandes Olist';
COMMENT ON COLUMN staging.stg_orders.delivery_days IS 'Délai réel de livraison en jours (delivered - purchase)';
COMMENT ON COLUMN staging.stg_orders.is_on_time IS '1 = livré à temps ou avant, 0 = retard';
COMMENT ON COLUMN staging.stg_orders.delay_days IS 'Nombre de jours de retard (si retard > 0)';

-- ── Table : stg_order_items ───────────────────────────────────────────────────
DROP TABLE IF EXISTS staging.stg_order_items CASCADE;
CREATE TABLE staging.stg_order_items (
    order_id            VARCHAR(64)   NOT NULL,
    order_item_id       INTEGER       NOT NULL,
    product_id          VARCHAR(64)   NOT NULL,
    seller_id           VARCHAR(64)   NOT NULL,
    shipping_limit_date TIMESTAMP,
    price               NUMERIC(10, 2) NOT NULL,
    freight_value       NUMERIC(10, 2) NOT NULL,
    CONSTRAINT stg_order_items_pk PRIMARY KEY (order_id, order_item_id)
);

COMMENT ON TABLE staging.stg_order_items IS 'Lignes de commande nettoyées — grain : 1 article par commande';

-- ── Table : stg_customers ─────────────────────────────────────────────────────
DROP TABLE IF EXISTS staging.stg_customers CASCADE;
CREATE TABLE staging.stg_customers (
    customer_id              VARCHAR(64) NOT NULL,
    customer_unique_id       VARCHAR(64),
    customer_zip_code_prefix VARCHAR(10),
    customer_city            VARCHAR(100),
    customer_state           VARCHAR(10),
    CONSTRAINT stg_customers_pk PRIMARY KEY (customer_id)
);

-- ── Table : stg_products ──────────────────────────────────────────────────────
DROP TABLE IF EXISTS staging.stg_products CASCADE;
CREATE TABLE staging.stg_products (
    product_id                      VARCHAR(64) NOT NULL,
    product_category_name           VARCHAR(100),
    product_category_name_english    VARCHAR(100),
    product_name_lenght             INTEGER,
    product_description_lenght      INTEGER,
    product_photos_qty              INTEGER,
    product_weight_g                NUMERIC(10, 2),
    product_length_cm               NUMERIC(10, 2),
    product_height_cm               NUMERIC(10, 2),
    product_width_cm                NUMERIC(10, 2),
    CONSTRAINT stg_products_pk PRIMARY KEY (product_id)
);

-- ── Table : stg_sellers ───────────────────────────────────────────────────────
DROP TABLE IF EXISTS staging.stg_sellers CASCADE;
CREATE TABLE staging.stg_sellers (
    seller_id               VARCHAR(64) NOT NULL,
    seller_zip_code_prefix  VARCHAR(10),
    seller_city             VARCHAR(100),
    seller_state            VARCHAR(10),
    CONSTRAINT stg_sellers_pk PRIMARY KEY (seller_id)
);

-- ── Table : stg_payments ──────────────────────────────────────────────────────
DROP TABLE IF EXISTS staging.stg_payments CASCADE;
CREATE TABLE staging.stg_payments (
    order_id                VARCHAR(64)   NOT NULL,
    payment_sequential      INTEGER       NOT NULL,
    payment_type            VARCHAR(50),
    payment_installments    INTEGER,
    payment_value           NUMERIC(10, 2),
    CONSTRAINT stg_payments_pk PRIMARY KEY (order_id, payment_sequential)
);

COMMENT ON TABLE staging.stg_payments IS 'Paiements — grain : 1 ligne par séquence de paiement par commande';

-- ── Table : stg_reviews ───────────────────────────────────────────────────────
DROP TABLE IF EXISTS staging.stg_reviews CASCADE;
CREATE TABLE staging.stg_reviews (
    review_id               VARCHAR(64) NOT NULL,
    order_id                VARCHAR(64) NOT NULL,
    review_score            SMALLINT,
    review_comment_title    TEXT,
    review_comment_message  TEXT,
    review_creation_date    TIMESTAMP,
    review_answer_timestamp TIMESTAMP,
    CONSTRAINT stg_reviews_pk PRIMARY KEY (review_id)
);

-- ── Schéma monitoring ─────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS monitoring;

DROP TABLE IF EXISTS monitoring.pipeline_runs CASCADE;
CREATE TABLE monitoring.pipeline_runs (
    id                  SERIAL PRIMARY KEY,
    run_id              VARCHAR(16)   NOT NULL,
    run_timestamp       TIMESTAMP     NOT NULL DEFAULT NOW(),
    status              VARCHAR(20)   NOT NULL,  -- 'success' | 'failure'
    duration_seconds    NUMERIC(10, 2),
    rows_orders         INTEGER       DEFAULT 0,
    rows_order_items    INTEGER       DEFAULT 0,
    rows_customers      INTEGER       DEFAULT 0,
    rows_products       INTEGER       DEFAULT 0,
    rows_sellers        INTEGER       DEFAULT 0,
    rows_payments       INTEGER       DEFAULT 0,
    rows_reviews        INTEGER       DEFAULT 0
);

COMMENT ON TABLE monitoring.pipeline_runs IS 'Journal des exécutions du pipeline ETL';

-- ── Vérification ──────────────────────────────────────────────────────────────
SELECT
    table_schema,
    table_name,
    pg_size_pretty(pg_total_relation_size(quote_ident(table_schema) || '.' || quote_ident(table_name))) AS size
FROM information_schema.tables
WHERE table_schema IN ('staging', 'monitoring')
ORDER BY table_schema, table_name;
