-- ============================================================
-- Retail & Sales Intelligence Platform
-- kpi_queries.sql — Requêtes analytiques & KPI
-- ============================================================
-- Chaque requête est documentée avec sa définition métier.
-- Source : schéma dw (Data Warehouse)
-- ============================================================


-- ════════════════════════════════════════════════════════════
-- KPI 1 — COMMERCIAUX
-- ════════════════════════════════════════════════════════════

-- ── 1.1 Chiffre d'affaires des articles (hors frais de livraison) ─────────────
-- Définition : Somme des prix de vente des articles des commandes livrées.
-- Exclut les frais de livraison (freight_value) qui sont traités séparément.
SELECT
    SUM(foi.price)                                    AS revenue_items,
    SUM(foi.freight_value)                            AS total_freight,
    SUM(foi.price + foi.freight_value)                AS gross_revenue,
    COUNT(DISTINCT foi.order_id)                      AS nb_orders,
    ROUND(SUM(foi.price) / NULLIF(COUNT(DISTINCT foi.order_id), 0), 2) AS avg_basket
FROM dw.fact_order_items foi
JOIN dw.fact_orders fo ON foi.order_id = fo.order_id
WHERE fo.order_status = 'delivered';


-- ── 1.2 Évolution mensuelle du CA ────────────────────────────────────────────
-- Définition : CA par mois et variation % vs. mois précédent.
WITH monthly_revenue AS (
    SELECT
        d.year,
        d.month_number,
        TO_CHAR(d.full_date, 'YYYY-MM')                AS month_label,
        SUM(foi.price)                                  AS revenue
    FROM dw.fact_order_items foi
    JOIN dw.fact_orders fo  ON foi.order_id    = fo.order_id
    JOIN dw.dim_date d      ON foi.order_date_key = d.date_key
    WHERE fo.order_status = 'delivered'
    GROUP BY d.year, d.month_number, TO_CHAR(d.full_date, 'YYYY-MM')
)
SELECT
    month_label,
    revenue,
    LAG(revenue) OVER (ORDER BY year, month_number) AS prev_revenue,
    CASE
        WHEN LAG(revenue) OVER (ORDER BY year, month_number) IS NULL
            OR LAG(revenue) OVER (ORDER BY year, month_number) = 0
        THEN NULL
        ELSE ROUND(
            (revenue - LAG(revenue) OVER (ORDER BY year, month_number))
            / LAG(revenue) OVER (ORDER BY year, month_number) * 100,
            2
        )
    END AS revenue_growth_pct
FROM monthly_revenue
ORDER BY year, month_number;


-- ── 1.3 Top 10 catégories par CA ─────────────────────────────────────────────
SELECT
    COALESCE(p.product_category_name_english, 'Unknown')    AS category,
    COUNT(DISTINCT foi.order_id)                            AS nb_orders,
    SUM(foi.price)                                          AS revenue,
    ROUND(SUM(foi.price) * 100.0 / SUM(SUM(foi.price)) OVER (), 2) AS revenue_pct
FROM dw.fact_order_items foi
JOIN dw.dim_product p       ON foi.product_key    = p.product_key
JOIN dw.fact_orders fo      ON foi.order_id       = fo.order_id
WHERE fo.order_status = 'delivered'
GROUP BY p.product_category_name_english
ORDER BY revenue DESC
LIMIT 10;


-- ── 1.4 Performance des vendeurs ─────────────────────────────────────────────
SELECT
    s.seller_state,
    s.seller_city,
    COUNT(DISTINCT foi.order_id)    AS nb_orders,
    COUNT(DISTINCT foi.product_key) AS nb_products_sold,
    SUM(foi.price)                  AS revenue,
    ROUND(AVG(foi.price), 2)        AS avg_price
FROM dw.fact_order_items foi
JOIN dw.dim_seller s    ON foi.seller_key = s.seller_key
JOIN dw.fact_orders fo  ON foi.order_id   = fo.order_id
WHERE fo.order_status = 'delivered'
GROUP BY s.seller_state, s.seller_city
ORDER BY revenue DESC
LIMIT 20;


-- ════════════════════════════════════════════════════════════
-- KPI 2 — CLIENTS
-- ════════════════════════════════════════════════════════════

-- ── 2.1 Nombre de clients distincts & fréquence d'achat ──────────────────────
SELECT
    COUNT(DISTINCT c.customer_unique_id)                AS nb_unique_customers,
    COUNT(DISTINCT fo.order_id)                         AS nb_orders,
    ROUND(
        COUNT(DISTINCT fo.order_id)::NUMERIC
        / NULLIF(COUNT(DISTINCT c.customer_unique_id), 0),
        2
    )                                                   AS avg_orders_per_customer,
    SUM(CASE WHEN freq.nb_orders > 1 THEN 1 ELSE 0 END) AS repeat_customers,
    ROUND(
        SUM(CASE WHEN freq.nb_orders > 1 THEN 1 ELSE 0 END)::NUMERIC
        / NULLIF(COUNT(DISTINCT c.customer_unique_id), 0) * 100,
        2
    )                                                   AS repeat_rate_pct
FROM dw.fact_orders fo
JOIN dw.dim_customer c ON fo.customer_key = c.customer_key
JOIN (
    SELECT c2.customer_unique_id, COUNT(*) AS nb_orders
    FROM dw.fact_orders fo2
    JOIN dw.dim_customer c2 ON fo2.customer_key = c2.customer_key
    WHERE fo2.order_status = 'delivered'
    GROUP BY c2.customer_unique_id
) freq ON c.customer_unique_id = freq.customer_unique_id
WHERE fo.order_status = 'delivered';


-- ── 2.2 Segmentation RFM ─────────────────────────────────────────────────────
-- Définition métier :
--   R (Récence)  : jours depuis la dernière commande (référence = date max du dataset).
--   F (Fréquence): nombre de commandes du client.
--   M (Montant)  : CA total (price) des articles commandés.
-- Scoring : quintiles 1-5 (5 = meilleur pour F et M, 1 = meilleur pour R).
WITH rfm_base AS (
    SELECT
        c.customer_unique_id,
        MAX(d.full_date)                                AS last_order_date,
        COUNT(DISTINCT fo.order_id)                     AS frequency,
        SUM(foi.price)                                  AS monetary
    FROM dw.fact_orders fo
    JOIN dw.dim_customer c      ON fo.customer_key      = c.customer_key
    JOIN dw.fact_order_items foi ON foi.order_id        = fo.order_id
    JOIN dw.dim_date d          ON fo.order_date_key    = d.date_key
    WHERE fo.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),
ref_date AS (SELECT MAX(last_order_date) AS max_date FROM rfm_base),
rfm_scores AS (
    SELECT
        r.customer_unique_id,
        (ref.max_date - r.last_order_date)::INTEGER         AS recency_days,
        r.frequency,
        ROUND(r.monetary, 2)                                AS monetary,
        NTILE(5) OVER (ORDER BY (ref.max_date - r.last_order_date) DESC) AS r_score,
        NTILE(5) OVER (ORDER BY r.frequency)                AS f_score,
        NTILE(5) OVER (ORDER BY r.monetary)                 AS m_score
    FROM rfm_base r
    CROSS JOIN ref_date ref
)
SELECT
    customer_unique_id,
    recency_days,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    (r_score + f_score + m_score)                   AS rfm_total,
    CASE
        WHEN r_score >= 4 AND f_score >= 4          THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3          THEN 'Loyal Customers'
        WHEN r_score >= 4 AND f_score <= 2          THEN 'Recent Customers'
        WHEN r_score <= 2 AND f_score >= 3          THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2          THEN 'Lost'
        ELSE 'Potential Loyalists'
    END                                             AS rfm_segment
FROM rfm_scores
ORDER BY rfm_total DESC;


-- ── 2.3 Répartition géographique des clients ──────────────────────────────────
SELECT
    c.customer_state,
    COUNT(DISTINCT c.customer_unique_id)    AS nb_customers,
    COUNT(DISTINCT fo.order_id)             AS nb_orders,
    SUM(foi.price)                          AS revenue
FROM dw.fact_orders fo
JOIN dw.dim_customer c      ON fo.customer_key  = c.customer_key
JOIN dw.fact_order_items foi ON fo.order_id     = foi.order_id
WHERE fo.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY revenue DESC;


-- ════════════════════════════════════════════════════════════
-- KPI 3 — LOGISTIQUES
-- ════════════════════════════════════════════════════════════

-- ── 3.1 KPI logistiques globaux ──────────────────────────────────────────────
-- Définition :
--   Délai moyen  : moyenne de delivery_days sur commandes livrées avec date valide.
--   Taux on-time : (livrées <= date estimée) / (livrées avec date estimée valide) × 100.
--   Retard moyen : moyenne de delay_days sur commandes en retard.
SELECT
    COUNT(*)                                                            AS nb_delivered,
    ROUND(AVG(delivery_days), 1)                                        AS avg_delivery_days,
    ROUND(AVG(CASE WHEN is_on_time IS NOT NULL THEN is_on_time END) * 100, 2) AS on_time_rate_pct,
    ROUND(AVG(CASE WHEN delay_days > 0 THEN delay_days END), 1)        AS avg_delay_days,
    COUNT(CASE WHEN delay_days > 0 THEN 1 END)                         AS nb_late_orders
FROM dw.fact_orders
WHERE order_status = 'delivered'
  AND delivery_days IS NOT NULL;


-- ── 3.2 Délais de livraison par état (région) ─────────────────────────────────
SELECT
    c.customer_state,
    COUNT(fo.order_id)              AS nb_orders,
    ROUND(AVG(fo.delivery_days), 1) AS avg_delivery_days,
    ROUND(AVG(fo.delay_days), 1)    AS avg_delay_days,
    ROUND(AVG(fo.is_on_time) * 100, 2) AS on_time_pct
FROM dw.fact_orders fo
JOIN dw.dim_customer c ON fo.customer_key = c.customer_key
WHERE fo.order_status = 'delivered'
  AND fo.delivery_days IS NOT NULL
GROUP BY c.customer_state
ORDER BY avg_delivery_days DESC;


-- ── 3.3 Relation délais et satisfaction client ────────────────────────────────
SELECT
    fo.is_on_time,
    ROUND(AVG(fr.review_score), 2)      AS avg_review_score,
    COUNT(*)                            AS nb_orders
FROM dw.fact_orders fo
JOIN dw.fact_reviews fr ON fo.order_id = fr.order_id
WHERE fo.order_status = 'delivered'
  AND fo.is_on_time IS NOT NULL
GROUP BY fo.is_on_time
ORDER BY fo.is_on_time;


-- ── 3.4 Évolution mensuelle des délais ────────────────────────────────────────
SELECT
    d.year,
    d.month_number,
    TO_CHAR(d.full_date, 'YYYY-MM')         AS month_label,
    COUNT(fo.order_id)                      AS nb_orders,
    ROUND(AVG(fo.delivery_days), 1)         AS avg_delivery_days,
    ROUND(AVG(fo.is_on_time) * 100, 2)      AS on_time_pct
FROM dw.fact_orders fo
JOIN dw.dim_date d ON fo.order_date_key = d.date_key
WHERE fo.order_status = 'delivered'
  AND fo.delivery_days IS NOT NULL
GROUP BY d.year, d.month_number, TO_CHAR(d.full_date, 'YYYY-MM')
ORDER BY d.year, d.month_number;


-- ════════════════════════════════════════════════════════════
-- KPI 4 — QUALITÉ DES DONNÉES & MONITORING
-- ════════════════════════════════════════════════════════════

-- ── 4.1 Historique des exécutions du pipeline ─────────────────────────────────
SELECT
    run_id,
    run_timestamp,
    status,
    duration_seconds,
    rows_orders,
    rows_order_items,
    rows_customers,
    rows_products,
    rows_sellers,
    rows_payments,
    rows_reviews,
    (rows_orders + rows_order_items + rows_customers
     + rows_products + rows_sellers + rows_payments + rows_reviews) AS total_rows
FROM monitoring.pipeline_runs
ORDER BY run_timestamp DESC
LIMIT 20;


-- ── 4.2 Dernière exécution ────────────────────────────────────────────────────
SELECT
    run_id,
    run_timestamp                           AS last_run_at,
    status,
    duration_seconds,
    (rows_orders + rows_order_items + rows_customers
     + rows_products + rows_sellers + rows_payments + rows_reviews) AS total_rows_loaded
FROM monitoring.pipeline_runs
WHERE run_timestamp = (SELECT MAX(run_timestamp) FROM monitoring.pipeline_runs);


-- ── 4.3 Volume des tables DWH ─────────────────────────────────────────────────
SELECT
    schemaname,
    tablename,
    n_live_tup                              AS row_count,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS table_size
FROM pg_stat_user_tables
WHERE schemaname = 'dw'
ORDER BY n_live_tup DESC;
