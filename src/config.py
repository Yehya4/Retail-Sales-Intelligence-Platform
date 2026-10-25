"""
Retail & Sales Intelligence Platform
=====================================
Configuration centralisée du projet.
Charge les variables d'environnement et définit les constantes globales.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Charger le fichier .env si présent
load_dotenv()

# ── Répertoires racine ─────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / os.getenv("DATA_RAW_PATH", "raw")
PROCESSED_DIR = DATA_DIR / os.getenv("DATA_PROCESSED_PATH", "processed")
REJECTED_DIR = DATA_DIR / os.getenv("DATA_REJECTED_PATH", "rejected")
LOGS_DIR = PROJECT_ROOT / os.getenv("LOGS_PATH", "logs")

# ── PostgreSQL ─────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "database": os.getenv("POSTGRES_DB", "retail_dw"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}

DB_URL = (
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# ── PySpark ────────────────────────────────────────────────────────────────────
SPARK_CONFIG = {
    "master": os.getenv("SPARK_MASTER", "local[*]"),
    "app_name": os.getenv("SPARK_APP_NAME", "RetailSalesIntelligence"),
    "driver_memory": os.getenv("SPARK_DRIVER_MEMORY", "4g"),
}

# ── Fichiers sources attendus ──────────────────────────────────────────────────
EXPECTED_CSV_FILES = {
    "orders":        "olist_orders_dataset.csv",
    "order_items":   "olist_order_items_dataset.csv",
    "customers":     "olist_customers_dataset.csv",
    "products":      "olist_products_dataset.csv",
    "sellers":       "olist_sellers_dataset.csv",
    "payments":      "olist_order_payments_dataset.csv",
    "reviews":       "olist_order_reviews_dataset.csv",
    "geolocation":   "olist_geolocation_dataset.csv",
    "translations":  "product_category_name_translation.csv",
}

# ── Schémas des colonnes attendues par fichier ─────────────────────────────────
EXPECTED_COLUMNS = {
    "orders": [
        "order_id", "customer_id", "order_status",
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": [
        "order_id", "order_item_id", "product_id", "seller_id",
        "shipping_limit_date", "price", "freight_value",
    ],
    "customers": [
        "customer_id", "customer_unique_id", "customer_zip_code_prefix",
        "customer_city", "customer_state",
    ],
    "products": [
        "product_id", "product_category_name",
        "product_name_lenght", "product_description_lenght",
        "product_photos_qty", "product_weight_g",
        "product_length_cm", "product_height_cm", "product_width_cm",
    ],
    "sellers": [
        "seller_id", "seller_zip_code_prefix",
        "seller_city", "seller_state",
    ],
    "payments": [
        "order_id", "payment_sequential", "payment_type",
        "payment_installments", "payment_value",
    ],
    "reviews": [
        "review_id", "order_id", "review_score",
        "review_comment_title", "review_comment_message",
        "review_creation_date", "review_answer_timestamp",
    ],
    "geolocation": [
        "geolocation_zip_code_prefix", "geolocation_lat",
        "geolocation_lng", "geolocation_city", "geolocation_state",
    ],
    "translations": [
        "product_category_name", "product_category_name_english",
    ],
}

# ── Colonnes date par table ────────────────────────────────────────────────────
DATE_COLUMNS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
}

# ── Statuts de commandes valides ───────────────────────────────────────────────
VALID_ORDER_STATUSES = {
    "delivered", "shipped", "canceled", "invoiced",
    "processing", "approved", "created", "unavailable",
}

# ── Pipeline ───────────────────────────────────────────────────────────────────
PIPELINE_CONFIG = {
    "batch_size": int(os.getenv("PIPELINE_BATCH_SIZE", 100000)),
    "log_level": os.getenv("PIPELINE_LOG_LEVEL", "INFO"),
}

# Créer les répertoires nécessaires au démarrage
for directory in [RAW_DIR, PROCESSED_DIR, REJECTED_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
