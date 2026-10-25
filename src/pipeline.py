"""
Orchestrateur principal du pipeline ETL.
Exécute les étapes Extract → Transform → Load dans l'ordre.
Gère les erreurs, les réexécutions idempotentes et la journalisation.

Usage :
    python src/pipeline.py
    python src/pipeline.py --dry-run      # Test sans écriture en DB
    python src/pipeline.py --steps etl    # Étapes spécifiques
"""

import sys
from pathlib import Path

# Assure que la racine du projet est dans le sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uuid
import argparse
from datetime import datetime

from src.config import (
    RAW_DIR, PROCESSED_DIR, LOGS_DIR,
    SPARK_CONFIG, PIPELINE_CONFIG,
)
from src.extract import load_all_sources, validate_columns, inspect_dataframe
from src.transform import transform_all
from src.load import save_all_parquet, load_all_to_staging, log_pipeline_run, get_engine
from src.utils.logger import setup_logger, get_logger

logger = get_logger(__name__)


def run_pipeline(dry_run: bool = False) -> dict:
    """
    Exécute le pipeline ETL complet.

    Args:
        dry_run: Si True, effectue Extract + Transform mais n'écrit pas en DB.

    Returns:
        Dictionnaire de résultats (métriques, status, durée).
    """
    run_id = str(uuid.uuid4())[:8]
    start_time = datetime.now()
    status = "failure"
    metrics = {}

    logger.info("=" * 60)
    logger.info(f" RETAIL & SALES INTELLIGENCE PLATFORM — Pipeline ETL")
    logger.info(f" Run ID : {run_id} | {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f" Dry Run : {dry_run}")
    logger.info("=" * 60)

    try:
        # ── ÉTAPE 1 : EXTRACT ─────────────────────────────────────────────────
        logger.info("── ÉTAPE 1 : EXTRACTION ──────────────────────────────────")
        raw_data = load_all_sources(RAW_DIR)

        if not raw_data:
            logger.error("Aucune donnée source chargée. Vérifier le répertoire data/raw/")
            return {"status": "failure", "run_id": run_id, "metrics": {}}

        # Inspection et validation
        for dataset_name, df in raw_data.items():
            inspect_dataframe(df, dataset_name)
            validate_columns(df, dataset_name)

        # ── ÉTAPE 2 : TRANSFORM ───────────────────────────────────────────────
        logger.info("── ÉTAPE 2 : TRANSFORMATION ──────────────────────────────")
        transformed_data = transform_all(raw_data)

        # Métriques de transformation
        for dataset_name, (df_clean, df_rejected) in transformed_data.items():
            metrics[dataset_name] = len(df_clean)
            if not df_rejected.empty:
                logger.warning(f"  [{dataset_name}] {len(df_rejected):,} lignes rejetées")

        # ── ÉTAPE 3 : LOAD ────────────────────────────────────────────────────
        if not dry_run:
            logger.info("── ÉTAPE 3 : CHARGEMENT ──────────────────────────────────")

            # 3a. Parquet
            parquet_paths = save_all_parquet(transformed_data, PROCESSED_DIR)
            logger.info(f"  {len(parquet_paths)} fichiers Parquet sauvegardés.")

            # 3b. PostgreSQL Staging
            try:
                engine = get_engine()
                load_counts = load_all_to_staging(transformed_data, engine)
                logger.info(f"  Staging PostgreSQL chargé : {sum(load_counts.values()):,} lignes.")
            except Exception as e:
                logger.warning(f"  Chargement PostgreSQL ignoré : {e}")
                logger.warning("  Vérifiez la connexion dans .env et que PostgreSQL est démarré.")

        else:
            logger.info("── ÉTAPE 3 : CHARGEMENT (ignoré — mode dry-run) ──────────")

        status = "success"
        logger.info("✔ Pipeline terminé avec succès.")

    except Exception as e:
        logger.error(f"✘ Erreur pipeline : {e}", exc_info=True)
        status = "failure"

    finally:
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"  Durée totale : {duration:.2f}s")

        # Journalisation du run
        if not dry_run:
            try:
                engine = get_engine()
                log_pipeline_run(run_id, status, metrics, engine, duration)
            except Exception:
                pass  # Ne pas planter si la DB est indisponible

    result = {
        "run_id": run_id,
        "status": status,
        "duration_seconds": round(duration, 2),
        "metrics": metrics,
        "timestamp": start_time.isoformat(),
    }

    logger.info("=" * 60)
    logger.info(f" Résultat : {status.upper()} | Run ID : {run_id}")
    logger.info("=" * 60)

    return result


def main():
    """Point d'entrée CLI du pipeline."""
    parser = argparse.ArgumentParser(
        description="Retail & Sales Intelligence Platform — Pipeline ETL"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Exécuter sans écriture en base de données.",
    )
    parser.add_argument(
        "--log-level",
        default=PIPELINE_CONFIG["log_level"],
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Niveau de log (défaut: INFO).",
    )
    args = parser.parse_args()

    setup_logger(log_level=args.log_level, log_dir=LOGS_DIR)
    run_pipeline(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
