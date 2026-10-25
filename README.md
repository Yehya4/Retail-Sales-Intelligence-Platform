# 🛍️ Retail & Sales Intelligence Platform

> **Plateforme décisionnelle d'analyse des ventes et d'ingénierie des données**  
> Portfolio Project · Data Analytics · Business Intelligence · Data Engineering

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![PySpark](https://img.shields.io/badge/PySpark-3.5-E25A1C?style=flat&logo=apache-spark&logoColor=white)](https://spark.apache.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Power BI](https://img.shields.io/badge/Power%20BI-Desktop-F2C811?style=flat&logo=powerbi&logoColor=black)](https://powerbi.microsoft.com)

---

## 📋 Description

Ce projet est une **plateforme décisionnelle complète** transformant des données commerciales brutes en indicateurs analytiques exploitables. Il s'appuie sur le **Brazilian E-Commerce Public Dataset by Olist** (~100k commandes, 2016–2018) et couvre l'intégralité d'un pipeline Data Engineering moderne.

### Ce que ce projet démontre

| Compétence | Technologie |
|---|---|
| Ingestion & exploration | Python, Pandas |
| Traitement distribué | PySpark (mode local) |
| Stockage analytique | Parquet, PostgreSQL |
| Modélisation dimensionnelle | Star Schema (DWH) |
| Visualisation & reporting | Power BI Desktop, DAX |
| Qualité des données | Tests automatisés (pytest) |
| DevOps & portfolio | Git, GitHub, Docker (optionnel) |

---

## 🏗️ Architecture

```
Sources CSV (Olist)
       │
       ▼
  [Couche 1] Raw Data Layer
  data/raw/          ← CSV sources intacts
       │
       ▼
  [Couche 2] Data Lake
  data/processed/    ← Parquet nettoyés
  data/rejected/     ← Enregistrements invalides
       │
       ▼
  [Couche 3] Traitement ETL
  src/extract.py     ← Extraction
  src/transform.py   ← Nettoyage & transformation
  src/load.py        ← Chargement PostgreSQL
       │
       ▼
  [Couche 4] Data Warehouse (PostgreSQL)
  Staging → Star Schema (faits + dimensions)
       │
       ▼
  [Couche 5] Restitution
  Power BI Desktop   ← 5 pages de dashboard
       │
       ▼
  [Couche 6] Qualité & Monitoring
  logs/, tests/      ← Suivi & validation
```

---

## 📁 Structure du projet

```
retail-sales-intelligence/
│
├── data/
│   ├── raw/                    ← Fichiers CSV Olist (non versionnés)
│   ├── processed/              ← Fichiers Parquet préparés
│   ├── rejected/               ← Enregistrements invalides
│   └── README.md
│
├── notebooks/
│   └── 01_exploratory_analysis.ipynb
│
├── src/
│   ├── __init__.py
│   ├── config.py               ← Configuration centralisée
│   ├── extract.py              ← Module d'extraction
│   ├── transform.py            ← Module de transformation
│   ├── load.py                 ← Module de chargement
│   ├── pipeline.py             ← Orchestrateur principal
│   ├── data_quality.py         ← Contrôles de qualité
│   └── utils/
│       ├── __init__.py
│       ├── logger.py           ← Logging centralisé
│       └── spark_utils.py      ← Utilitaires PySpark
│
├── sql/
│   ├── staging_schema.sql      ← Tables de staging
│   ├── warehouse_schema.sql    ← Star Schema DWH
│   └── kpi_queries.sql         ← Requêtes analytiques
│
├── tests/
│   ├── conftest.py
│   ├── test_transformations.py
│   └── test_data_quality.py
│
├── powerbi/
│   └── retail_sales_intelligence.pbix
│
├── docs/
│   ├── architecture.md
│   ├── data_dictionary.md
│   └── screenshots/
│
├── logs/                       ← Logs d'exécution (non versionnés)
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md                   ← Ce fichier
```

---

## 🚀 Installation & Démarrage

### Prérequis

- Python 3.11+
- PostgreSQL 15+
- Java 11+ (requis par PySpark)
- Power BI Desktop (Windows)

### 1. Cloner le dépôt

```bash
git clone https://github.com/votre-username/retail-sales-intelligence.git
cd retail-sales-intelligence
```

### 2. Créer l'environnement virtuel

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

```bash
cp .env.example .env
# Éditer .env avec vos paramètres PostgreSQL
```

### 5. Télécharger les données Olist

Télécharger depuis [Kaggle - Brazilian E-Commerce by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) et placer les CSV dans `data/raw/`.

### 6. Initialiser la base de données

```bash
psql -U postgres -f sql/staging_schema.sql
psql -U postgres -f sql/warehouse_schema.sql
```

### 7. Exécuter le pipeline ETL

```bash
python src/pipeline.py
```

### 8. Lancer les tests

```bash
pytest tests/ -v
```

---

## 📊 KPI & Indicateurs

### Commerciaux
- 💰 Chiffre d'affaires des articles
- 🛒 Nombre de commandes & panier moyen
- 📈 Évolution mensuelle
- 🏆 Top produits & catégories

### Clients
- 👥 Nombre de clients distincts
- 🔄 Taux de fidélisation
- 🎯 Segmentation RFM (Récence · Fréquence · Valeur)

### Logistiques
- ⏱️ Délai moyen de livraison
- ✅ Taux de livraison à temps
- ⚠️ Retard moyen

### Qualité des données
- 📋 Lignes traitées / rejetées
- 🔍 Taux de valeurs manquantes
- ⏳ Durée d'exécution du pipeline

---

## 📄 Dataset

| Fichier | Contenu | Lignes (approx.) |
|---|---|---|
| `olist_orders_dataset.csv` | Commandes & statuts | ~100k |
| `olist_order_items_dataset.csv` | Lignes de commande | ~112k |
| `olist_customers_dataset.csv` | Clients & localisation | ~100k |
| `olist_products_dataset.csv` | Produits & catégories | ~33k |
| `olist_sellers_dataset.csv` | Vendeurs | ~3k |
| `olist_order_payments_dataset.csv` | Paiements | ~104k |
| `olist_order_reviews_dataset.csv` | Avis & notes | ~100k |
| `olist_geolocation_dataset.csv` | Géolocalisation | ~1M |

**Source :** [Olist Brazilian E-Commerce Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — Licence CC BY-NC-SA 4.0

---

## 📅 Plan de réalisation

| Semaine | Focus | Livrables |
|---|---|---|
| **S1** | Préparation & Exploration | Notebook EDA, dictionnaire des données |
| **S2** | SQL & PostgreSQL | Schéma SQL, scripts d'importation |
| **S3** | Pipeline ETL | Pipeline fonctionnel, fichiers Parquet |
| **S4** | Data Warehouse & Power BI | Modèle analytique, premier dashboard |
| **S5** | Analyse métier | Dashboard complet, recommandations |
| **S6** | Tests & Portfolio | README finalisé, démo prête |

---

## 🔒 Sécurité

- Aucun secret, mot de passe ou credential dans le dépôt
- Configuration via fichier `.env` (ignoré par Git)
- Accès PostgreSQL limité au strict nécessaire

---

## 👤 Auteur

**Étudiant en Ingénierie Informatique**  
Projet de portfolio — Préparation stage PFE pré-embauche

---

## 📜 Licence & Attribution

Les données utilisées sont issues du **Brazilian E-Commerce Public Dataset by Olist**, disponible sur [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), sous licence **CC BY-NC-SA 4.0**.

Ce projet est présenté comme une étude de cas à but pédagogique.
