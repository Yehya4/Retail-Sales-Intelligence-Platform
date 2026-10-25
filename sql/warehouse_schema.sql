-- ============================================================
-- Retail & Sales Intelligence Platform
-- warehouse_schema.sql — Data Warehouse (Star Schema)
-- ============================================================
-- Modèle en étoile pour l'analyse BI.
-- Dimensions : date, customer, product, seller
-- Faits      : fact_order_items, fact_orders, fact_payments
-- ============================================================

CREATE SCHEMA IF NOT EXISTS dw;

-- ════════════════════════════════════════════════════════════
-- DIMENSIONS
-- ════════════════════════════════════════════════════════════

-- ── Dimension Date ────────────────────────────────────────────────────────────
-- Utilisée comme rôle multiple : date commande, livraison, livraison estimée.
DROP TABLE IF EXISTS dw.dim_date CASCADE;
CREATE TABLE dw.dim_date (
    date_key        INTEGER     NOT NULL,   -- Format YYYYMMDD (ex: 20171201)
    full_date       DATE        NOT NULL,
    day_of_month    SMALLINT    NOT NULL,
    day_of_week     SMALLINT    NOT NULL,   -- 1=Lundi ... 7=Dimanche
    day_name        VARCHAR(15) NOT NULL,
    week_of_year    SMALLINT    NOT NULL,
    month_number    SMALLINT    NOT NULL,
    month_name      VARCHAR(15) NOT NULL,
    quarter         SMALLINT    NOT NULL,
    year            SMALLINT    NOT NULL,
    is_weekend      BOOLEAN     NOT NULL DEFAULT FALSE,
    CONSTRAINT dim_date_pk PRIMARY KEY (date_key)
);

COMMENT ON TABLE dw.dim_date IS 'Dimension temporelle — utilisable pour plusieurs rôles de date';

-- Population de dim_date (2015-01-01 au 2020-12-31)
INSERT INTO dw.dim_date (
    date_key, full_date, day_of_month, day_of_week, day_name,
    week_of_year, month_number, month_name, quarter, year, is_weekend
)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INTEGER             AS date_key,
    d::DATE                                      AS full_date,
    EXTRACT(DAY   FROM d)::SMALLINT             AS day_of_month,
    EXTRACT(ISODOW FROM d)::SMALLINT            AS day_of_week,
    TO_CHAR(d, 'Day')                            AS day_name,
    EXTRACT(WEEK  FROM d)::SMALLINT             AS week_of_year,
    EXTRACT(MONTH FROM d)::SMALLINT             AS month_number,
    TO_CHAR(d, 'Month')                          AS month_name,
    EXTRACT(QUARTER FROM d)::SMALLINT           AS quarter,
    EXTRACT(YEAR  FROM d)::SMALLINT             AS year,
    EXTRACT(ISODOW FROM d) IN (6, 7)            AS is_weekend
FROM generate_series('2015-01-01'::DATE, '2020-12-31'::DATE, '1 day'::INTERVAL) AS d
ON CONFLICT (date_key) DO NOTHING;

-- ── Dimension Customer ────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dw.dim_customer CASCADE;
CREATE TABLE dw.dim_customer (
    customer_key        SERIAL      NOT NULL,
    customer_id         VARCHAR(64) NOT NULL UNIQUE,
    customer_unique_id  VARCHAR(64),
    customer_city       VARCHAR(100),
    customer_state      VARCHAR(10),
    CONSTRAINT dim_customer_pk PRIMARY KEY (customer_key)
);

CREATE INDEX idx_dim_customer_id ON dw.dim_customer (customer_id);

-- ── Dimension Product ─────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dw.dim_product CASCADE;
CREATE TABLE dw.dim_product (
    product_key                     SERIAL      NOT NULL,
    product_id                      VARCHAR(64) NOT NULL UNIQUE,
    product_category_name           VARCHAR(100),
    product_category_name_english   VARCHAR(100),
    product_weight_g                NUMERIC(10, 2),
    product_length_cm               NUMERIC(10, 2),
    product_height_cm               NUMERIC(10, 2),
    product_width_cm                NUMERIC(10, 2),
    CONSTRAINT dim_product_pk PRIMARY KEY (product_key)
);

CREATE INDEX idx_dim_product_id ON dw.dim_product (product_id);
CREATE INDEX idx_dim_product_category ON dw.dim_product (product_category_name_english);

-- ── Dimension Seller ──────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dw.dim_seller CASCADE;
CREATE TABLE dw.dim_seller (
    seller_key              SERIAL      NOT NULL,
    seller_id               VARCHAR(64) NOT NULL UNIQUE,
    seller_city             VARCHAR(100),
    seller_state            VARCHAR(10),
    CONSTRAINT dim_seller_pk PRIMARY KEY (seller_key)
);

CREATE INDEX idx_dim_seller_id ON dw.dim_seller (seller_id);

-- ════════════════════════════════════════════════════════════
-- TABLES DE FAITS
-- ════════════════════════════════════════════════════════════

-- ── Fait : fact_order_items ───────────────────────────────────────────────────
-- Grain : 1 ligne par article d'une commande.
-- Permet l'analyse du CA au niveau produit/vendeur.
DROP TABLE IF EXISTS dw.fact_order_items CASCADE;
CREATE TABLE dw.fact_order_items (
    order_item_key      SERIAL          NOT NULL,
    order_id            VARCHAR(64)     NOT NULL,
    order_item_id       INTEGER         NOT NULL,
    customer_key        INTEGER         NOT NULL REFERENCES dw.dim_customer(customer_key),
    product_key         INTEGER         NOT NULL REFERENCES dw.dim_product(product_key),
    seller_key          INTEGER         NOT NULL REFERENCES dw.dim_seller(seller_key),
    order_date_key      INTEGER                  REFERENCES dw.dim_date(date_key),
    price               NUMERIC(10, 2)  NOT NULL,
    freight_value       NUMERIC(10, 2)  NOT NULL DEFAULT 0,
    CONSTRAINT fact_order_items_pk PRIMARY KEY (order_item_key),
    CONSTRAINT fact_order_items_uq UNIQUE (order_id, order_item_id)
);

COMMENT ON TABLE dw.fact_order_items IS
    'Faits au niveau article. Grain : 1 ligne par (order_id, order_item_id). '
    'Ne pas sommer payment_value ici pour éviter le double comptage.';

CREATE INDEX idx_foi_order_id ON dw.fact_order_items (order_id);
CREATE INDEX idx_foi_customer_key ON dw.fact_order_items (customer_key);
CREATE INDEX idx_foi_product_key ON dw.fact_order_items (product_key);
CREATE INDEX idx_foi_date_key ON dw.fact_order_items (order_date_key);

-- ── Fait : fact_orders ────────────────────────────────────────────────────────
-- Grain : 1 ligne par commande.
-- Permet l'analyse des volumes, délais et statuts au niveau commande.
DROP TABLE IF EXISTS dw.fact_orders CASCADE;
CREATE TABLE dw.fact_orders (
    order_key                   SERIAL      NOT NULL,
    order_id                    VARCHAR(64) NOT NULL UNIQUE,
    customer_key                INTEGER     NOT NULL REFERENCES dw.dim_customer(customer_key),
    order_date_key              INTEGER              REFERENCES dw.dim_date(date_key),
    delivered_date_key          INTEGER              REFERENCES dw.dim_date(date_key),
    estimated_delivery_date_key INTEGER              REFERENCES dw.dim_date(date_key),
    order_status                VARCHAR(32),
    delivery_days               NUMERIC(10, 2),
    is_on_time                  SMALLINT,
    delay_days                  NUMERIC(10, 2),
    CONSTRAINT fact_orders_pk PRIMARY KEY (order_key)
);

COMMENT ON TABLE dw.fact_orders IS
    'Faits au niveau commande. Grain : 1 ligne par order_id. '
    'Utiliser pour volumes, délais et taux de livraison à temps.';

CREATE INDEX idx_fo_order_id ON dw.fact_orders (order_id);
CREATE INDEX idx_fo_customer_key ON dw.fact_orders (customer_key);
CREATE INDEX idx_fo_order_date_key ON dw.fact_orders (order_date_key);

-- ── Fait : fact_payments ──────────────────────────────────────────────────────
-- Grain : 1 ligne par séquence de paiement (une commande peut avoir plusieurs paiements).
DROP TABLE IF EXISTS dw.fact_payments CASCADE;
CREATE TABLE dw.fact_payments (
    payment_key             SERIAL          NOT NULL,
    order_id                VARCHAR(64)     NOT NULL,
    payment_sequential      INTEGER         NOT NULL,
    order_date_key          INTEGER                  REFERENCES dw.dim_date(date_key),
    payment_type            VARCHAR(50),
    payment_installments    INTEGER,
    payment_value           NUMERIC(10, 2)  NOT NULL,
    CONSTRAINT fact_payments_pk PRIMARY KEY (payment_key),
    CONSTRAINT fact_payments_uq UNIQUE (order_id, payment_sequential)
);

COMMENT ON TABLE dw.fact_payments IS
    'Faits de paiement. Grain : 1 ligne par séquence de paiement par commande. '
    'Ne pas joindre directement avec fact_order_items sans agrégation préalable.';

CREATE INDEX idx_fp_order_id ON dw.fact_payments (order_id);
CREATE INDEX idx_fp_payment_type ON dw.fact_payments (payment_type);

-- ── Fait : fact_reviews ───────────────────────────────────────────────────────
-- Grain : 1 ligne par avis client.
DROP TABLE IF EXISTS dw.fact_reviews CASCADE;
CREATE TABLE dw.fact_reviews (
    review_key          SERIAL      NOT NULL,
    review_id           VARCHAR(64) NOT NULL UNIQUE,
    order_id            VARCHAR(64) NOT NULL,
    customer_key        INTEGER              REFERENCES dw.dim_customer(customer_key),
    review_date_key     INTEGER              REFERENCES dw.dim_date(date_key),
    review_score        SMALLINT,
    has_comment         BOOLEAN     DEFAULT FALSE,
    CONSTRAINT fact_reviews_pk PRIMARY KEY (review_key)
);

CREATE INDEX idx_fr_order_id ON dw.fact_reviews (order_id);
CREATE INDEX idx_fr_review_score ON dw.fact_reviews (review_score);

-- ════════════════════════════════════════════════════════════
-- PROCÉDURE DE CHARGEMENT DWH DEPUIS STAGING
-- ════════════════════════════════════════════════════════════

CREATE OR REPLACE PROCEDURE dw.load_dimensions()
LANGUAGE plpgsql AS $$
BEGIN
    -- dim_customer
    INSERT INTO dw.dim_customer (customer_id, customer_unique_id, customer_city, customer_state)
    SELECT customer_id, customer_unique_id, customer_city, customer_state
    FROM staging.stg_customers
    ON CONFLICT (customer_id) DO UPDATE SET
        customer_city  = EXCLUDED.customer_city,
        customer_state = EXCLUDED.customer_state;

    RAISE NOTICE 'dim_customer chargée';

    -- dim_product
    INSERT INTO dw.dim_product (
        product_id, product_category_name, product_category_name_english,
        product_weight_g, product_length_cm, product_height_cm, product_width_cm
    )
    SELECT product_id, product_category_name, product_category_name_english,
           product_weight_g, product_length_cm, product_height_cm, product_width_cm
    FROM staging.stg_products
    ON CONFLICT (product_id) DO UPDATE SET
        product_category_name_english = EXCLUDED.product_category_name_english;

    RAISE NOTICE 'dim_product chargée';

    -- dim_seller
    INSERT INTO dw.dim_seller (seller_id, seller_city, seller_state)
    SELECT seller_id, seller_city, seller_state
    FROM staging.stg_sellers
    ON CONFLICT (seller_id) DO UPDATE SET
        seller_city  = EXCLUDED.seller_city,
        seller_state = EXCLUDED.seller_state;

    RAISE NOTICE 'dim_seller chargée';
END;
$$;

CREATE OR REPLACE PROCEDURE dw.load_facts()
LANGUAGE plpgsql AS $$
BEGIN
    -- fact_orders
    INSERT INTO dw.fact_orders (
        order_id, customer_key, order_date_key, delivered_date_key,
        estimated_delivery_date_key, order_status,
        delivery_days, is_on_time, delay_days
    )
    SELECT
        o.order_id,
        c.customer_key,
        TO_CHAR(o.order_purchase_timestamp, 'YYYYMMDD')::INTEGER        AS order_date_key,
        TO_CHAR(o.order_delivered_customer_date, 'YYYYMMDD')::INTEGER   AS delivered_date_key,
        TO_CHAR(o.order_estimated_delivery_date, 'YYYYMMDD')::INTEGER   AS estimated_delivery_date_key,
        o.order_status,
        o.delivery_days,
        o.is_on_time,
        o.delay_days
    FROM staging.stg_orders o
    JOIN dw.dim_customer c ON o.customer_id = c.customer_id
    ON CONFLICT (order_id) DO UPDATE SET
        order_status  = EXCLUDED.order_status,
        delivery_days = EXCLUDED.delivery_days,
        is_on_time    = EXCLUDED.is_on_time,
        delay_days    = EXCLUDED.delay_days;

    RAISE NOTICE 'fact_orders chargée';

    -- fact_order_items
    INSERT INTO dw.fact_order_items (
        order_id, order_item_id, customer_key, product_key, seller_key,
        order_date_key, price, freight_value
    )
    SELECT
        i.order_id,
        i.order_item_id,
        c.customer_key,
        p.product_key,
        s.seller_key,
        TO_CHAR(o.order_purchase_timestamp, 'YYYYMMDD')::INTEGER AS order_date_key,
        i.price,
        i.freight_value
    FROM staging.stg_order_items i
    JOIN staging.stg_orders o       ON i.order_id   = o.order_id
    JOIN dw.dim_customer c          ON o.customer_id = c.customer_id
    JOIN dw.dim_product  p          ON i.product_id  = p.product_id
    JOIN dw.dim_seller   s          ON i.seller_id   = s.seller_id
    ON CONFLICT (order_id, order_item_id) DO NOTHING;

    RAISE NOTICE 'fact_order_items chargée';

    -- fact_payments
    INSERT INTO dw.fact_payments (
        order_id, payment_sequential, order_date_key,
        payment_type, payment_installments, payment_value
    )
    SELECT
        p.order_id,
        p.payment_sequential,
        TO_CHAR(o.order_purchase_timestamp, 'YYYYMMDD')::INTEGER AS order_date_key,
        p.payment_type,
        p.payment_installments,
        p.payment_value
    FROM staging.stg_payments p
    JOIN staging.stg_orders o ON p.order_id = o.order_id
    ON CONFLICT (order_id, payment_sequential) DO NOTHING;

    RAISE NOTICE 'fact_payments chargée';

    -- fact_reviews
    INSERT INTO dw.fact_reviews (
        review_id, order_id, customer_key, review_date_key,
        review_score, has_comment
    )
    SELECT
        r.review_id,
        r.order_id,
        c.customer_key,
        TO_CHAR(r.review_creation_date, 'YYYYMMDD')::INTEGER AS review_date_key,
        r.review_score,
        (r.review_comment_message IS NOT NULL AND r.review_comment_message != '') AS has_comment
    FROM staging.stg_reviews r
    JOIN staging.stg_orders o   ON r.order_id   = o.order_id
    JOIN dw.dim_customer c      ON o.customer_id = c.customer_id
    ON CONFLICT (review_id) DO NOTHING;

    RAISE NOTICE 'fact_reviews chargée';
END;
$$;

-- ── Vérification du modèle ────────────────────────────────────────────────────
SELECT
    t.table_schema  AS schema,
    t.table_name    AS table_name,
    c.column_name   AS primary_key
FROM information_schema.tables t
LEFT JOIN information_schema.table_constraints tc
    ON tc.table_schema = t.table_schema AND tc.table_name = t.table_name
    AND tc.constraint_type = 'PRIMARY KEY'
LEFT JOIN information_schema.key_column_usage c
    ON c.constraint_name = tc.constraint_name
WHERE t.table_schema = 'dw'
ORDER BY t.table_name;
