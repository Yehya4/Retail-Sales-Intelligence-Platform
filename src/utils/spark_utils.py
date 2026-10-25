"""
Utilitaires PySpark.
Création et configuration de la SparkSession pour le traitement distribué local.
"""

from pyspark.sql import SparkSession
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_spark_session(
    app_name: str = "RetailSalesIntelligence",
    master: str = "local[*]",
    driver_memory: str = "4g",
) -> SparkSession:
    """
    Crée et retourne une SparkSession configurée pour le mode local.

    Args:
        app_name:       Nom de l'application Spark.
        master:         URL du master Spark (ex: "local[*]" pour local).
        driver_memory:  Mémoire allouée au driver (ex: "4g").

    Returns:
        SparkSession initialisée.
    """
    logger.info(f"Initialisation SparkSession — master={master}, app={app_name}")

    spark = (
        SparkSession.builder
        .appName(app_name)
        .master(master)
        .config("spark.driver.memory", driver_memory)
        .config("spark.sql.shuffle.partitions", "8")        # Adapté au mode local
        .config("spark.sql.adaptive.enabled", "true")       # Adaptive Query Execution
        .config("spark.sql.parquet.compression.codec", "snappy")
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")
    logger.info(f"SparkSession créée — version Spark : {spark.version}")
    return spark


def stop_spark_session(spark: SparkSession) -> None:
    """
    Arrête proprement la SparkSession.

    Args:
        spark: SparkSession à arrêter.
    """
    if spark:
        spark.stop()
        logger.info("SparkSession arrêtée.")
