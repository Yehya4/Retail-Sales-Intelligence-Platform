"""
Module d'extraction — Couche Extract du pipeline ETL.
Responsable de :
  - Vérifier la présence des fichiers CSV sources.
  - Charger les fichiers avec pandas.
  - Vérifier les colonnes attendues.
  - Journaliser les fichiers traités.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from src.config import RAW_DIR, EXPECTED_CSV_FILES, EXPECTED_COLUMNS
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── Vérification des sources ───────────────────────────────────────────────────

def check_source_files(raw_dir: Path = RAW_DIR) -> Dict[str, bool]:
    """
    Vérifie la présence des fichiers CSV attendus dans le répertoire source.

    Args:
        raw_dir: Chemin vers le répertoire contenant les fichiers bruts.

    Returns:
        Dictionnaire {nom_dataset: fichier_présent}.
    """
    logger.info(f"Vérification des fichiers sources dans : {raw_dir}")
    status = {}

    for dataset_name, filename in EXPECTED_CSV_FILES.items():
        filepath = raw_dir / filename
        exists = filepath.exists()
        status[dataset_name] = exists
        if exists:
            size_mb = filepath.stat().st_size / (1024 ** 2)
            logger.info(f"  ✔ {filename} ({size_mb:.1f} Mo)")
        else:
            logger.warning(f"  ✘ {filename} — MANQUANT")

    missing = [k for k, v in status.items() if not v]
    if missing:
        logger.warning(f"{len(missing)} fichier(s) manquant(s) : {missing}")
    else:
        logger.info("Tous les fichiers sources sont présents.")

    return status


# ── Chargement des données ─────────────────────────────────────────────────────

def load_csv(
    dataset_name: str,
    raw_dir: Path = RAW_DIR,
    dtype: Optional[dict] = None,
    **kwargs,
) -> Optional[pd.DataFrame]:
    """
    Charge un fichier CSV source en DataFrame pandas.

    Args:
        dataset_name: Clé du dataset (ex: "orders", "customers").
        raw_dir:      Répertoire source.
        dtype:        Dictionnaire de types optionnel pour pandas.
        **kwargs:     Arguments supplémentaires passés à pd.read_csv().

    Returns:
        DataFrame pandas ou None si le fichier est absent.
    """
    filename = EXPECTED_CSV_FILES.get(dataset_name)
    if not filename:
        logger.error(f"Dataset inconnu : '{dataset_name}'")
        return None

    filepath = raw_dir / filename
    if not filepath.exists():
        logger.error(f"Fichier non trouvé : {filepath}")
        return None

    logger.info(f"Chargement de '{dataset_name}' depuis {filepath.name}...")
    start = datetime.now()

    try:
        df = pd.read_csv(
            filepath,
            dtype=dtype,
            low_memory=False,
            **kwargs,
        )
        elapsed = (datetime.now() - start).total_seconds()
        logger.info(
            f"  → {len(df):,} lignes × {len(df.columns)} colonnes "
            f"chargées en {elapsed:.2f}s"
        )
        return df

    except Exception as e:
        logger.error(f"Erreur lors du chargement de '{dataset_name}' : {e}")
        return None


def load_all_sources(raw_dir: Path = RAW_DIR) -> Dict[str, pd.DataFrame]:
    """
    Charge tous les fichiers CSV sources disponibles.

    Args:
        raw_dir: Répertoire source.

    Returns:
        Dictionnaire {nom_dataset: DataFrame}.
    """
    logger.info("=== Chargement de toutes les sources ===")
    file_status = check_source_files(raw_dir)
    dataframes = {}

    for dataset_name, present in file_status.items():
        if present:
            df = load_csv(dataset_name, raw_dir)
            if df is not None:
                dataframes[dataset_name] = df
        else:
            logger.warning(f"Dataset '{dataset_name}' ignoré (fichier manquant).")

    logger.info(f"=== {len(dataframes)} dataset(s) chargé(s) ===")
    return dataframes


# ── Validation des colonnes ────────────────────────────────────────────────────

def validate_columns(
    df: pd.DataFrame,
    dataset_name: str,
) -> Dict[str, list]:
    """
    Vérifie que le DataFrame contient les colonnes attendues.

    Args:
        df:           DataFrame à valider.
        dataset_name: Nom du dataset pour récupérer le schéma attendu.

    Returns:
        Dictionnaire avec listes 'missing' et 'extra' colonnes.
    """
    expected = set(EXPECTED_COLUMNS.get(dataset_name, []))
    actual = set(df.columns)

    missing = sorted(expected - actual)
    extra = sorted(actual - expected)

    if missing:
        logger.warning(f"[{dataset_name}] Colonnes manquantes : {missing}")
    if extra:
        logger.debug(f"[{dataset_name}] Colonnes supplémentaires : {extra}")
    if not missing:
        logger.info(f"[{dataset_name}] Toutes les colonnes attendues sont présentes.")

    return {"missing": missing, "extra": extra}


# ── Résumé d'inspection ────────────────────────────────────────────────────────

def inspect_dataframe(df: pd.DataFrame, dataset_name: str) -> dict:
    """
    Produit un résumé de qualité d'un DataFrame pour journalisation.

    Args:
        df:           DataFrame à inspecter.
        dataset_name: Nom du dataset.

    Returns:
        Dictionnaire de métriques de qualité.
    """
    n_rows, n_cols = df.shape
    n_duplicates = df.duplicated().sum()
    missing_counts = df.isnull().sum()
    missing_pct = (missing_counts / n_rows * 100).round(2)

    summary = {
        "dataset": dataset_name,
        "n_rows": n_rows,
        "n_cols": n_cols,
        "n_duplicates": int(n_duplicates),
        "missing_by_column": missing_pct[missing_pct > 0].to_dict(),
        "dtypes": df.dtypes.astype(str).to_dict(),
    }

    logger.info(f"[{dataset_name}] Résumé d'inspection :")
    logger.info(f"  Lignes     : {n_rows:,}")
    logger.info(f"  Colonnes   : {n_cols}")
    logger.info(f"  Doublons   : {n_duplicates:,}")
    if summary["missing_by_column"]:
        logger.info(f"  Valeurs manquantes : {summary['missing_by_column']}")
    else:
        logger.info("  Aucune valeur manquante détectée.")

    return summary
