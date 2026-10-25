"""
Module de transformation PySpark.
Utilise Apache Spark en mode local pour les transformations distribuées.
Même logique que transform.py mais exploitant l'API DataFrame de Spark.

Usage :
    Appeler depuis pipeline.py en passant spark=True
    ou exécuter directement : python src/spark_transform.py
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType, DateType
from pathlib import Path
from typing import Dict, Tuple
import time

from src.config import RAW_DIR, PROCESSED_DIR, EXPECTED_CSV_FILES, SPARK_CONFIG
from src.utils.logger import get_logger
from src.utils.spark_utils import create_spark_session, stop_spark_session

logger = get_logger(__name__)


# ── Chargement Spark ───────────────────────────────────────────────────────────

def load_csv_spark(
    spark: SparkSession,
    dataset_name: str,
    raw_dir: Path = RAW_DIR,
) -> DataFrame:
    """
    Charge un fichier CSV en Spark DataFrame.

    Args:
        spark:        SparkSession active.
        dataset_name: Nom du dataset (clé dans EXPECTED_CSV_FILES).
        raw_dir:      Répertoire source.

    Returns:
        Spark DataFrame ou None si fichier absent.
    """
    filename = EXPECTED_CSV_FILES.get(dataset_name)
    if not filename:
        logger.error(f"[Spark] Dataset inconnu : '{dataset_name}'")
        return None

    filepath = raw_dir / filename
    if not filepath.exists():
        logger.error(f"[Spark] Fichier non trouvé : {filepath}")
        return None

    logger.info(f"[Spark] Chargement de '{dataset_name}' : {filename}")
    df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .option("encoding", "UTF-8")
        .option("multiLine", "true")
        .csv(str(filepath))
    )
    logger.info(f"  → {df.count():,} lignes × {len(df.columns)} colonnes")
    return df


# ── Transformation Spark : Orders ──────────────────────────────────────────────

def transform_orders_spark(df: DataFrame) -> Tuple[DataFrame, DataFrame]:
    """
    Transforme le dataset orders avec PySpark.

    Opérations :
    - Suppression des doublons sur order_id.
    - Cast des colonnes de dates.
    - Filtrage des lignes sans clés obligatoires.
    - Calcul du délai de livraison.
    - Indicateur de livraison à temps.

    Args:
        df: Spark DataFrame brut des orders.

    Returns:
        Tuple (df_clean, df_rejected) de Spark DataFrames.
    """
    logger.info("[Spark/orders] Transformation...")
    start = time.time()

    # Cast des colonnes de dates
    date_cols = [
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for col in date_cols:
        if col in df.columns:
            df = df.withColumn(col, F.to_timestamp(F.col(col)))

    # Identification des rejets
    df_rejected = df.filter(
        F.col("order_id").isNull() | F.col("customer_id").isNull()
    ).withColumn("reject_reason", F.lit("null_primary_key"))

    # Données valides (sans doublons, sans clés nulles)
    df_clean = (
        df.filter(F.col("order_id").isNotNull() & F.col("customer_id").isNotNull())
        .dropDuplicates(["order_id"])
    )

    # Calcul du délai de livraison
    df_clean = df_clean.withColumn(
        "delivery_days",
        F.when(
            F.col("order_delivered_customer_date").isNotNull()
            & F.col("order_purchase_timestamp").isNotNull(),
            F.datediff(
                F.col("order_delivered_customer_date"),
                F.col("order_purchase_timestamp"),
            )
        ).otherwise(F.lit(None).cast(DoubleType()))
    )

    # Indicateur on_time
    df_clean = df_clean.withColumn(
        "is_on_time",
        F.when(
            F.col("order_delivered_customer_date").isNotNull()
            & F.col("order_estimated_delivery_date").isNotNull(),
            (F.col("order_delivered_customer_date") <= F.col("order_estimated_delivery_date")).cast(IntegerType())
        ).otherwise(F.lit(None).cast(IntegerType()))
    )

    # Jours de retard
    df_clean = df_clean.withColumn(
        "delay_days",
        F.when(
            F.col("is_on_time") == 0,
            F.datediff(
                F.col("order_delivered_customer_date"),
                F.col("order_estimated_delivery_date"),
            )
        ).otherwise(F.lit(None).cast(IntegerType()))
    )

    elapsed = time.time() - start
    logger.info(f"[Spark/orders] ✔ {df_clean.count():,} lignes en {elapsed:.2f}s")
    return df_clean, df_rejected


# ── Transformation Spark : Order Items ────────────────────────────────────────

def transform_order_items_spark(df: DataFrame) -> Tuple[DataFrame, DataFrame]:
    """Transforme le dataset order_items avec PySpark."""
    logger.info("[Spark/order_items] Transformation...")

    df_rejected = df.filter(
        F.col("order_id").isNull()
        | F.col("product_id").isNull()
        | F.col("seller_id").isNull()
        | (F.col("price") < 0)
        | (F.col("freight_value") < 0)
    ).withColumn("reject_reason", F.lit("invalid_data"))

    df_clean = df.filter(
        F.col("order_id").isNotNull()
        & F.col("product_id").isNotNull()
        & F.col("seller_id").isNotNull()
        & (F.col("price") >= 0)
        & (F.col("freight_value") >= 0)
    )

    logger.info(f"[Spark/order_items] ✔ {df_clean.count():,} lignes valides")
    return df_clean, df_rejected


# ── Sauvegarde Parquet via Spark ───────────────────────────────────────────────

def save_parquet_spark(
    df: DataFrame,
    dataset_name: str,
    output_dir: Path = PROCESSED_DIR,
    mode: str = "overwrite",
) -> str:
    """
    Sauvegarde un Spark DataFrame au format Parquet.

    Args:
        df:           Spark DataFrame à sauvegarder.
        dataset_name: Nom du dataset.
        output_dir:   Répertoire de destination.
        mode:         Mode d'écriture ('overwrite' ou 'append').

    Returns:
        Chemin de sortie.
    """
    out_path = str(output_dir / dataset_name)
    logger.info(f"[Spark] Sauvegarde Parquet → {out_path}")

    (
        df.write
        .mode(mode)
        .option("compression", "snappy")
        .parquet(out_path)
    )

    logger.info(f"[Spark] ✔ {dataset_name} sauvegardé en Parquet")
    return out_path


# ── Pipeline Spark complet ─────────────────────────────────────────────────────

def run_spark_pipeline(raw_dir: Path = RAW_DIR, output_dir: Path = PROCESSED_DIR) -> dict:
    """
    Exécute le pipeline ETL complet avec PySpark.

    Note : Ce pipeline démontre l'usage de Spark en mode local.
    Pour ce dataset (~100k lignes), les performances sont comparables
    à pandas. L'intérêt de Spark apparaît à partir de plusieurs millions
    de lignes ou en cluster distribué.

    Args:
        raw_dir:    Répertoire source CSV.
        output_dir: Répertoire de destination Parquet.

    Returns:
        Dictionnaire de métriques d'exécution.
    """
    logger.info("=== Démarrage du pipeline PySpark ===")
    start_total = time.time()
    metrics = {}

    spark = create_spark_session(
        app_name=SPARK_CONFIG["app_name"],
        master=SPARK_CONFIG["master"],
        driver_memory=SPARK_CONFIG["driver_memory"],
    )

    try:
        datasets_to_process = ["orders", "order_items", "customers", "products", "sellers", "payments"]

        for dataset_name in datasets_to_process:
            df_raw = load_csv_spark(spark, dataset_name, raw_dir)
            if df_raw is None:
                logger.warning(f"[Spark] '{dataset_name}' ignoré.")
                continue

            # Transformation (seulement orders et order_items ont des règles spécifiques Spark)
            if dataset_name == "orders":
                df_clean, _ = transform_orders_spark(df_raw)
            elif dataset_name == "order_items":
                df_clean, _ = transform_order_items_spark(df_raw)
            else:
                df_clean = df_raw  # Transformations simples → pandas suffisant

            # Sauvegarde Parquet
            save_parquet_spark(df_clean, f"{dataset_name}_spark", output_dir)
            metrics[dataset_name] = df_clean.count()

        total_elapsed = time.time() - start_total
        logger.info(f"=== Pipeline PySpark terminé en {total_elapsed:.2f}s ===")

    finally:
        stop_spark_session(spark)

    return {"status": "success", "metrics": metrics, "duration_seconds": round(total_elapsed, 2)}


if __name__ == "__main__":
    results = run_spark_pipeline()
    print(f"\nRésultats PySpark : {results}")
