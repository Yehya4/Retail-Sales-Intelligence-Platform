"""
Module de qualité des données.
Contrôles formels sur les DataFrames transformés avant chargement.
Calcule les métriques de qualité et produit un rapport structuré.
"""

import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── Contrôles unitaires ────────────────────────────────────────────────────────

def check_null_rate(df: pd.DataFrame, column: str, threshold_pct: float = 10.0) -> dict:
    """
    Vérifie le taux de valeurs nulles d'une colonne.

    Args:
        df:            DataFrame à analyser.
        column:        Nom de la colonne.
        threshold_pct: Seuil d'alerte en pourcentage.

    Returns:
        Dictionnaire de résultats {column, null_count, null_pct, passed}.
    """
    n_total = len(df)
    n_null = df[column].isnull().sum()
    null_pct = (n_null / n_total * 100) if n_total > 0 else 0.0
    passed = bool(null_pct <= threshold_pct)

    return {
        "check": "null_rate",
        "column": column,
        "null_count": int(n_null),
        "total_rows": n_total,
        "null_pct": round(float(null_pct), 2),
        "threshold_pct": threshold_pct,
        "passed": passed,
    }


def check_uniqueness(df: pd.DataFrame, columns: List[str]) -> dict:
    """
    Vérifie que la combinaison de colonnes est unique (contrainte de clé).

    Args:
        df:      DataFrame à vérifier.
        columns: Liste de colonnes formant la clé.

    Returns:
        Dictionnaire de résultats {columns, n_duplicates, passed}.
    """
    n_total = len(df)
    n_distinct = df.drop_duplicates(subset=columns).shape[0]
    n_duplicates = n_total - n_distinct
    passed = bool(n_duplicates == 0)

    return {
        "check": "uniqueness",
        "columns": columns,
        "total_rows": n_total,
        "distinct_rows": n_distinct,
        "n_duplicates": int(n_duplicates),
        "passed": passed,
    }


def check_referential_integrity(
    df_child: pd.DataFrame,
    df_parent: pd.DataFrame,
    child_col: str,
    parent_col: str,
) -> dict:
    """
    Vérifie l'intégrité référentielle entre deux DataFrames.
    Détecte les valeurs dans df_child[child_col] absentes de df_parent[parent_col].

    Args:
        df_child:   DataFrame enfant (ex: order_items).
        df_parent:  DataFrame parent (ex: orders).
        child_col:  Colonne clé étrangère dans l'enfant.
        parent_col: Colonne clé primaire dans le parent.

    Returns:
        Dictionnaire de résultats.
    """
    orphans = ~df_child[child_col].isin(df_parent[parent_col])
    n_orphans = orphans.sum()
    passed = bool(n_orphans == 0)

    return {
        "check": "referential_integrity",
        "child_column": child_col,
        "parent_column": parent_col,
        "n_orphans": int(n_orphans),
        "orphan_pct": round(float(n_orphans) / len(df_child) * 100, 2) if len(df_child) > 0 else 0.0,
        "passed": passed,
    }


def check_value_range(
    df: pd.DataFrame,
    column: str,
    min_val: float = None,
    max_val: float = None,
) -> dict:
    """
    Vérifie qu'une colonne numérique est dans une plage acceptable.

    Args:
        df:      DataFrame à vérifier.
        column:  Colonne numérique.
        min_val: Valeur minimale acceptable (inclusive).
        max_val: Valeur maximale acceptable (inclusive).

    Returns:
        Dictionnaire de résultats.
    """
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    violations = 0

    if min_val is not None:
        violations += (series < min_val).sum()
    if max_val is not None:
        violations += (series > max_val).sum()

    passed = bool(violations == 0)

    return {
        "check": "value_range",
        "column": column,
        "min_val": min_val,
        "max_val": max_val,
        "n_violations": int(violations),
        "passed": passed,
    }


# ── Rapport de qualité global ──────────────────────────────────────────────────

def run_quality_checks(
    transformed_data: Dict[str, Tuple[pd.DataFrame, pd.DataFrame]],
) -> dict:
    """
    Exécute l'ensemble des contrôles de qualité sur les données transformées.

    Args:
        transformed_data: Dictionnaire {nom_dataset: (df_clean, df_rejected)}.

    Returns:
        Rapport complet de qualité.
    """
    logger.info("=== Contrôles de qualité des données ===")
    start = datetime.now()
    all_checks = []
    summary = {
        "timestamp": start.isoformat(),
        "datasets": {},
        "checks": [],
        "n_passed": 0,
        "n_failed": 0,
    }

    dfs = {k: v[0] for k, v in transformed_data.items()}

    # ── Orders ────────────────────────────────────────────────────────────────
    if "orders" in dfs:
        df = dfs["orders"]
        checks = [
            check_uniqueness(df, ["order_id"]),
            check_null_rate(df, "customer_id", threshold_pct=0),
            check_null_rate(df, "order_purchase_timestamp", threshold_pct=1),
            check_null_rate(df, "order_delivered_customer_date", threshold_pct=50),  # Normal : non livrées
        ]
        for c in checks:
            c["dataset"] = "orders"
            all_checks.append(c)
            _log_check(c)

    # ── Order Items ───────────────────────────────────────────────────────────
    if "order_items" in dfs:
        df = dfs["order_items"]
        checks = [
            check_uniqueness(df, ["order_id", "order_item_id"]),
            check_value_range(df, "price", min_val=0),
            check_value_range(df, "freight_value", min_val=0),
        ]
        # Intégrité référentielle order_items → orders
        if "orders" in dfs:
            checks.append(
                check_referential_integrity(df, dfs["orders"], "order_id", "order_id")
            )
        for c in checks:
            c["dataset"] = "order_items"
            all_checks.append(c)
            _log_check(c)

    # ── Customers ─────────────────────────────────────────────────────────────
    if "customers" in dfs:
        df = dfs["customers"]
        checks = [
            check_uniqueness(df, ["customer_id"]),
            check_null_rate(df, "customer_state", threshold_pct=1),
        ]
        for c in checks:
            c["dataset"] = "customers"
            all_checks.append(c)
            _log_check(c)

    # ── Products ──────────────────────────────────────────────────────────────
    if "products" in dfs:
        df = dfs["products"]
        checks = [
            check_uniqueness(df, ["product_id"]),
            check_null_rate(df, "product_category_name", threshold_pct=5),
            check_value_range(df, "product_weight_g", min_val=0),
        ]
        for c in checks:
            c["dataset"] = "products"
            all_checks.append(c)
            _log_check(c)

    # ── Payments ──────────────────────────────────────────────────────────────
    if "payments" in dfs:
        df = dfs["payments"]
        checks = [
            check_value_range(df, "payment_value", min_val=0),
        ]
        if "orders" in dfs:
            checks.append(
                check_referential_integrity(df, dfs["orders"], "order_id", "order_id")
            )
        for c in checks:
            c["dataset"] = "payments"
            all_checks.append(c)
            _log_check(c)

    # ── Résumé ────────────────────────────────────────────────────────────────
    summary["checks"] = all_checks
    summary["n_passed"] = sum(1 for c in all_checks if c.get("passed"))
    summary["n_failed"] = sum(1 for c in all_checks if not c.get("passed"))
    summary["duration_seconds"] = round((datetime.now() - start).total_seconds(), 2)

    # Métriques par dataset
    for name, (df_clean, df_rejected) in transformed_data.items():
        summary["datasets"][name] = {
            "rows_clean": len(df_clean),
            "rows_rejected": len(df_rejected),
            "rejection_rate_pct": round(
                len(df_rejected) / max(len(df_clean) + len(df_rejected), 1) * 100, 2
            ),
        }

    failed_checks = [c for c in all_checks if not c.get("passed")]
    if failed_checks:
        logger.warning(f"=== {summary['n_failed']} contrôle(s) échoué(s) ===")
        for c in failed_checks:
            logger.warning(f"  ✘ [{c.get('dataset', '?')}] {c['check']} — {c}")
    else:
        logger.info(f"=== Tous les contrôles passés ({summary['n_passed']}/{len(all_checks)}) ===")

    return summary


def _log_check(check: dict) -> None:
    """Affiche le résultat d'un contrôle dans les logs."""
    icon = "✔" if check.get("passed") else "✘"
    level = "info" if check.get("passed") else "warning"
    msg = f"  {icon} [{check.get('dataset', '?')}] {check['check']}"

    if check["check"] == "null_rate":
        msg += f" '{check['column']}' → {check['null_pct']}% nulls (seuil: {check['threshold_pct']}%)"
    elif check["check"] == "uniqueness":
        msg += f" {check['columns']} → {check['n_duplicates']} doublons"
    elif check["check"] == "referential_integrity":
        msg += f" {check['child_column']} → {check['n_orphans']} orphelins"
    elif check["check"] == "value_range":
        msg += f" '{check['column']}' → {check['n_violations']} violations"

    getattr(logger, level)(msg)
