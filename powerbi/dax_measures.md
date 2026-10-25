# DAX Measures — Retail & Sales Intelligence Platform
## Référence des mesures Power BI

Ce fichier documente toutes les mesures DAX utilisées dans le rapport Power BI.  
Copier-coller dans l'éditeur de mesures Power BI Desktop.

---

## 📁 Table : _Measures (table de mesures dédiée)

### 💰 Commerciaux

```dax
-- Chiffre d'affaires des articles (commandes livrées)
Revenue Items =
CALCULATE(
    SUM(fact_order_items[price]),
    fact_orders[order_status] = "delivered"
)

-- Frais de livraison totaux
Total Freight =
CALCULATE(
    SUM(fact_order_items[freight_value]),
    fact_orders[order_status] = "delivered"
)

-- Nombre de commandes distinctes
Nb Orders =
DISTINCTCOUNT(fact_orders[order_id])

-- Panier moyen (CA / nb commandes)
Avg Basket =
DIVIDE(
    [Revenue Items],
    [Nb Orders],
    BLANK()
)

-- CA du mois précédent
Revenue PM =
CALCULATE(
    [Revenue Items],
    DATEADD(dim_date[full_date], -1, MONTH)
)

-- Évolution mensuelle (%)
Revenue Growth % =
VAR prev = [Revenue PM]
RETURN
IF(
    ISBLANK(prev) || prev = 0,
    BLANK(),
    DIVIDE([Revenue Items] - prev, prev)
)
```

---

### 👥 Clients

```dax
-- Nombre de clients uniques (customer_unique_id)
Nb Unique Customers =
DISTINCTCOUNT(dim_customer[customer_unique_id])

-- Clients avec plus d'une commande
Repeat Customers =
CALCULATE(
    DISTINCTCOUNT(dim_customer[customer_unique_id]),
    FILTER(
        VALUES(dim_customer[customer_unique_id]),
        CALCULATE(DISTINCTCOUNT(fact_orders[order_id])) > 1
    )
)

-- Taux de fidélisation
Repeat Rate % =
DIVIDE([Repeat Customers], [Nb Unique Customers])

-- Score moyen des avis
Avg Review Score =
AVERAGE(fact_reviews[review_score])
```

---

### 🚚 Logistiques

```dax
-- Délai moyen de livraison (jours)
Avg Delivery Days =
CALCULATE(
    AVERAGE(fact_orders[delivery_days]),
    fact_orders[order_status] = "delivered",
    NOT ISBLANK(fact_orders[delivery_days])
)

-- Taux de livraison à temps
On Time Rate % =
CALCULATE(
    DIVIDE(
        COUNTROWS(FILTER(fact_orders, fact_orders[is_on_time] = 1)),
        COUNTROWS(FILTER(fact_orders, NOT ISBLANK(fact_orders[is_on_time])))
    ),
    fact_orders[order_status] = "delivered"
)

-- Retard moyen (jours, commandes en retard seulement)
Avg Delay Days =
CALCULATE(
    AVERAGE(fact_orders[delay_days]),
    fact_orders[order_status] = "delivered",
    fact_orders[is_on_time] = 0
)

-- Nombre de commandes en retard
Nb Late Orders =
CALCULATE(
    COUNTROWS(fact_orders),
    fact_orders[order_status] = "delivered",
    fact_orders[is_on_time] = 0
)
```

---

### 📊 Monitoring Pipeline

```dax
-- Date de dernière actualisation
Last Refresh =
MAX(monitoring_pipeline_runs[run_timestamp])

-- Lignes chargées (dernier run)
Last Run Rows =
CALCULATE(
    MAX(monitoring_pipeline_runs[rows_orders])
        + MAX(monitoring_pipeline_runs[rows_order_items])
        + MAX(monitoring_pipeline_runs[rows_customers])
        + MAX(monitoring_pipeline_runs[rows_products])
        + MAX(monitoring_pipeline_runs[rows_sellers])
        + MAX(monitoring_pipeline_runs[rows_payments])
        + MAX(monitoring_pipeline_runs[rows_reviews]),
    TOPN(1, monitoring_pipeline_runs, monitoring_pipeline_runs[run_timestamp], DESC)
)

-- Statut dernier run
Last Run Status =
CALCULATE(
    FIRSTNONBLANK(monitoring_pipeline_runs[status], 1),
    TOPN(1, monitoring_pipeline_runs, monitoring_pipeline_runs[run_timestamp], DESC)
)
```

---

## 📋 Relations Power BI recommandées

| Table Source | Colonne | → | Table Cible | Colonne | Cardinalité |
|---|---|---|---|---|---|
| fact_order_items | customer_key | → | dim_customer | customer_key | *:1 |
| fact_order_items | product_key | → | dim_product | product_key | *:1 |
| fact_order_items | seller_key | → | dim_seller | seller_key | *:1 |
| fact_order_items | order_date_key | → | dim_date | date_key | *:1 |
| fact_orders | customer_key | → | dim_customer | customer_key | *:1 |
| fact_orders | order_date_key | → | dim_date | date_key | *:1 (rôle) |
| fact_orders | delivered_date_key | → | dim_date | date_key | *:1 (rôle) |
| fact_orders | order_id | → | fact_order_items | order_id | 1:* |
| fact_orders | order_id | → | fact_payments | order_id | 1:* |
| fact_orders | order_id | → | fact_reviews | order_id | 1:* |

> ⚠️ Ne pas joindre fact_payments directement à fact_order_items dans Power BI  
> pour éviter le double comptage des montants.
