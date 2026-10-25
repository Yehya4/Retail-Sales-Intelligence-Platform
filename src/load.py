"""
Module de chargement — Couche Load du pipeline ETL.
Responsable de :
  - Sauvegarder les données nettoyées au format Parquet.
  - Charger les données dans PostgreSQL (staging + DWH).
  - Gérer les réexécutions sans créer de doublons (upsert).
  - Journaliser les métriques de chargement.
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import Dict, Tuple, Optional
from datetime import datetime
from sqlalchemy import create_engine, text

from src.config import PROCESSED_DIR, DB_URL
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── Sauvegarde Parquet ─────────────────────────────────────────────────────────

def save_to_parquet(
    df: pd.DataFrame,
    dataset_name: str,
    output_dir: Path = PROCESSED_DIR,
    partition_by: Optional[str] = None,
) -> Path:
    """
    Sauvegarde un DataFrame au format Parquet (compression Snappy).

    Args:
        df:            DataFrame à sauvegarder.
        dataset_name:  Nom du dataset (utilisé pour nommer le fichier).
        output_dir:    Répertoire de destination.
        partition_by:  Colonne de partitionnement optionnelle (ex: "year").

    Returns:
        Chemin du fichier Parquet créé.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    out_path = output_dir / f"{dataset_name}.parquet"
    logger.info(f"Sauvegarde Parquet : {out_path.name} ({len(df):,} lignes)...")

    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(
        table,
        str(out_path),
        compression="snappy",
    )

    size_mb = out_path.stat().st_size / (1024 ** 2)
    logger.info(f"  → Sauvegardé : {out_path.name} ({size_mb:.2f} Mo)")
    return out_path


def save_all_parquet(
    transformed_data: Dict[str, Tuple[pd.DataFrame, pd.DataFrame]],
    output_dir: Path = PROCESSED_DIR,
) -> Dict[str, Path]:
    """
    Sauvegarde tous les datasets nettoyés au format Parquet.

    Args:
        transformed_data: Dictionnaire {nom_dataset: (df_clean, df_rejected)}.
        output_dir:       Répertoire de destination.

    Returns:
        Dictionnaire {nom_dataset: chemin_parquet}.
    """
    logger.info("=== Sauvegarde Parquet ===")
    parquet_paths = {}

    for dataset_name, (df_clean, _) in transformed_data.items():
        if not df_clean.empty:
            path = save_to_parquet(df_clean, dataset_name, output_dir)
            parquet_paths[dataset_name] = path
        else:
            logger.warning(f"[{dataset_name}] DataFrame vide — Parquet non créé.")

    logger.info(f"=== {len(parquet_paths)} fichier(s) Parquet sauvegardé(s) ===")
    return parquet_paths


# ── Chargement PostgreSQL ──────────────────────────────────────────────────────

def get_engine():
    """Crée et retourne un moteur SQLAlchemy pour PostgreSQL."""
    try:
        engine = create_engine(DB_URL, pool_pre_ping=True)
        logger.info("Connexion PostgreSQL établie.")
        return engine
    except Exception as e:
        logger.error(f"Erreur de connexion PostgreSQL : {e}")
        raise


def load_to_staging(
    df: pd.DataFrame,
    table_name: str,
    engine=None,
    if_exists: str = "replace",
    chunksize: int = 10000,
) -> int:
    """
    Charge un DataFrame dans une table de staging PostgreSQL.

    Stratégie d'idempotence :
    - if_exists='replace' : remplace la table à chaque exécution (staging).
    - Pour les tables DWH, utiliser upsert_to_warehouse().

    Args:
        df:         DataFrame à charger.
        table_name: Nom de la table cible.
        engine:     Moteur SQLAlchemy (créé si None).
        if_exists:  Comportement si la table existe ('replace' ou 'append').
        chunksize:  Nombre de lignes par batch d'insertion.

    Returns:
        Nombre de lignes chargées.
    """
    if engine is None:
        engine = get_engine()

    schema = "staging"
    full_table = f"{schema}.{table_name}"

    logger.info(f"Chargement vers {full_table} ({len(df):,} lignes)...")
    start = datetime.now()

    try:
        df.to_sql(
            name=table_name,
            con=engine,
            schema=schema,
            if_exists=if_exists,
            index=False,
            chunksize=chunksize,
            method="multi",
        )
        elapsed = (datetime.now() - start).total_seconds()
        logger.info(f"  → {len(df):,} lignes chargées dans {full_table} en {elapsed:.2f}s")
        return len(df)

    except Exception as e:
        logger.error(f"Erreur lors du chargement dans {full_table} : {e}")
        raise


def load_all_to_staging(
    transformed_data: Dict[str, Tuple[pd.DataFrame, pd.DataFrame]],
    engine=None,
) -> Dict[str, int]:
    """
    Charge tous les datasets nettoyés dans les tables de staging.

    Args:
        transformed_data: Dictionnaire {nom_dataset: (df_clean, df_rejected)}.
        engine:           Moteur SQLAlchemy.

    Returns:
        Dictionnaire {nom_dataset: n_lignes_chargées}.
    """
    if engine is None:
        engine = get_engine()

    logger.info("=== Chargement Staging PostgreSQL ===")
    load_counts = {}

    for dataset_name, (df_clean, _) in transformed_data.items():
        if not df_clean.empty:
            n = load_to_staging(df_clean, f"stg_{dataset_name}", engine)
            load_counts[dataset_name] = n
        else:
            logger.warning(f"[{dataset_name}] DataFrame vide — chargement ignoré.")
            load_counts[dataset_name] = 0

    total = sum(load_counts.values())
    logger.info(f"=== Staging terminé — {total:,} lignes chargées au total ===")
    return load_counts


# ── Journalisation des exécutions ──────────────────────────────────────────────

def log_pipeline_run(
    run_id: str,
    status: str,
    metrics: dict,
    engine=None,
    duration_seconds: float = 0.0,
) -> None:
    """
    Enregistre les métriques d'une exécution du pipeline dans PostgreSQL.

    Args:
        run_id:           Identifiant unique de l'exécution.
        status:           'success' ou 'failure'.
        metrics:          Dictionnaire de métriques {dataset: n_rows}.
        engine:           Moteur SQLAlchemy.
        duration_seconds: Durée totale de l'exécution en secondes.
    """
    if engine is None:
        try:
            engine = get_engine()
        except Exception:
            logger.warning("Log pipeline : connexion DB indisponible, log ignoré.")
            return

    log_record = pd.DataFrame([{
        "run_id": run_id,
        "run_timestamp": datetime.now(),
        "status": status,
        "duration_seconds": round(duration_seconds, 2),
        "rows_orders": metrics.get("orders", 0),
        "rows_order_items": metrics.get("order_items", 0),
        "rows_customers": metrics.get("customers", 0),
        "rows_products": metrics.get("products", 0),
        "rows_sellers": metrics.get("sellers", 0),
        "rows_payments": metrics.get("payments", 0),
        "rows_reviews": metrics.get("reviews", 0),
    }])

    try:
        log_record.to_sql(
            name="pipeline_runs",
            con=engine,
            schema="monitoring",
            if_exists="append",
            index=False,
        )
        logger.info(f"Exécution {run_id} journalisée — status: {status}.")
    except Exception as e:
        logger.warning(f"Impossible de journaliser l'exécution : {e}")
