# Architecture technique
## Retail & Sales Intelligence Platform

---

## Vue d'ensemble

```
┌──────────────────────────────────────────────────────────────────────┐
│                   RETAIL & SALES INTELLIGENCE PLATFORM               │
│                                                                      │
│  ┌─────────────────┐                                                 │
│  │  COUCHE 1       │  Fichiers CSV Olist (data/raw/)                 │
│  │  Sources        │  → Conservation intacte des données brutes      │
│  └────────┬────────┘                                                 │
│           │                                                          │
│           ▼                                                          │
│  ┌─────────────────┐                                                 │
│  │  COUCHE 2       │  src/extract.py                                 │
│  │  Extraction     │  → Vérification des fichiers attendus           │
│  │  & Inspection   │  → Chargement pandas                           │
│  │                 │  → Validation des colonnes & inspection         │
│  └────────┬────────┘                                                 │
│           │                                                          │
│           ▼                                                          │
│  ┌─────────────────┐                                                 │
│  │  COUCHE 3       │  src/transform.py + src/data_quality.py         │
│  │  Transformation │  → Nettoyage (doublons, nulls, formats)         │
│  │  & Qualité      │  → Validation (clés, plages, intégrité)         │
│  │                 │  → Calculs dérivés (delivery_days, on_time…)    │
│  │                 │  → Isolation des rejets (data/rejected/)         │
│  └────────┬────────┘                                                 │
│           │                                                          │
│           ▼                                                          │
│  ┌─────────────────┐   ┌───────────────────────────────┐            │
│  │  COUCHE 4a      │   │  COUCHE 4b                    │            │
│  │  Data Lake      │   │  Data Warehouse               │            │
│  │  Parquet        │   │  PostgreSQL                   │            │
│  │  data/processed │   │                               │            │
│  │  Format Snappy  │   │  staging.*  → dw.*            │            │
│  │  Columnar       │   │  Star Schema                  │            │
│  └────────┬────────┘   └───────────────┬───────────────┘            │
│           │                            │                             │
│           └────────────┬───────────────┘                             │
│                        │                                             │
│                        ▼                                             │
│  ┌─────────────────────────────────────┐                            │
│  │  COUCHE 5 — Restitution             │                            │
│  │  Power BI Desktop                   │                            │
│  │  5 pages de dashboard               │                            │
│  │  Mesures DAX                        │                            │
│  └─────────────────────────────────────┘                            │
│                                                                      │
│  ┌─────────────────────────────────────┐                            │
│  │  COUCHE 6 — Qualité & Monitoring    │                            │
│  │  logs/ + monitoring.pipeline_runs   │                            │
│  │  tests/ (pytest)                    │                            │
│  │  Git / GitHub                       │                            │
│  └─────────────────────────────────────┘                            │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Modèle en étoile (Star Schema)

```
                         ┌──────────────┐
                         │  dim_date    │
                         │  date_key PK │
                         │  full_date   │
                         │  day/month/  │
                         │  quarter/year│
                         └──────┬───────┘
                                │ (rôle: order_date,
                                │  delivered_date,
                                │  estimated_date)
┌──────────────┐                │               ┌──────────────┐
│ dim_customer │                │               │  dim_product │
│ customer_key │◄───┐           │           ┌──►│  product_key │
│ customer_id  │    │           │           │   │  product_id  │
│ city / state │    │           │           │   │  category    │
└──────────────┘    │           │           │   │  weight/dims │
                    │     ┌─────┴──────┐    │   └──────────────┘
                    │     │fact_order_ │    │
                    ├────►│   items    │◄───┤
                    │     │ order_id   │    │
                    │     │ price      │    │   ┌──────────────┐
                    │     │ freight    │    └──►│  dim_seller  │
                    │     └─────┬──────┘        │  seller_key  │
                    │           │               │  seller_id   │
                    │     ┌─────┴──────┐        │  city/state  │
                    ├────►│fact_orders │        └──────────────┘
                    │     │ order_id   │
                    │     │ status     │
                    │     │ deliv_days │
                    │     │ is_on_time │
                    │     └───────────┘
                    │
                    │     ┌───────────────┐
                    │     │ fact_payments │
                    │     │ order_id      │
                    │     │ payment_type  │
                    │     │ payment_value │
                    │     └───────────────┘
                    │
                    │     ┌───────────────┐
                    └────►│ fact_reviews  │
                          │ review_score  │
                          │ has_comment   │
                          └───────────────┘
```

---

## Stack technologique

| Couche | Technologie | Version | Rôle |
|---|---|---|---|
| Langage | Python | 3.11+ | Pipeline ETL |
| Exploration | Pandas | 2.2.x | Nettoyage & analyse |
| Big Data | PySpark | 3.5.x | Transformations distribuées (mode local) |
| Stockage | Parquet / PyArrow | - | Data Lake colonne |
| Base analytique | PostgreSQL | 15+ | Data Warehouse |
| Connexion DB | SQLAlchemy + psycopg2 | - | ORM / connexion |
| BI | Power BI Desktop | - | Reporting & dashboards |
| Mesures | DAX | - | KPI dans Power BI |
| Logging | Loguru | 0.7.x | Logs structurés |
| Tests | pytest | 8.x | Tests automatisés |
| Versionnement | Git + GitHub | - | Portfolio |

---

## Flux de données détaillé

```
[CSV Olist]
     │
     │ pd.read_csv()
     ▼
[DataFrame brut]  ──validate_columns()──► [log avertissements]
     │
     │ transform_*()
     ▼
[DataFrame clean]  ──────────────────────► [data/rejected/*.csv]
     │                                       (enregistrements invalides)
     ├──── save_to_parquet() ──────────────► [data/processed/*.parquet]
     │
     └──── load_to_staging() ─────────────► [PostgreSQL: staging.*]
                                                    │
                                              CALL dw.load_dimensions()
                                              CALL dw.load_facts()
                                                    │
                                                    ▼
                                             [PostgreSQL: dw.*]
                                                    │
                                            Power BI DirectQuery
                                                    │
                                                    ▼
                                            [Dashboards interactifs]
```

---

## Décisions d'architecture

### Idempotence du pipeline
- Les tables **staging** sont recréées (`REPLACE`) à chaque exécution.
- Les tables **DWH** utilisent `INSERT ... ON CONFLICT DO NOTHING/UPDATE` (upsert).
- Les fichiers Parquet sont écrasés à chaque run.
- Résultat : une réexécution ne crée pas de doublons.

### Séparation raw / processed / rejected
- `data/raw/` : jamais modifié — source de vérité.
- `data/processed/` : données prêtes, format Parquet compressé Snappy.
- `data/rejected/` : enregistrements invalides horodatés pour audit.

### PySpark en mode local
- PySpark est utilisé pour les transformations distribuables et l'apprentissage des concepts Big Data.
- Le dataset Olist (~100k commandes) ne justifie pas un cluster : les gains de PySpark sont documentés séparément avec des données synthétiques.
- La configuration `local[*]` utilise tous les cœurs disponibles.

### Sécurité
- Aucun credential dans le code ou le dépôt.
- Configuration via `.env` (ignoré par `.gitignore`).
- `.env.example` fourni comme template.
