"""
Module de transformation — Couche Transform du pipeline ETL.
Responsable de :
  - Nettoyage des données (doublons, valeurs manquantes, formats).
  - Validation des contraintes (clés, statuts, dates).
  - Séparation des enregistrements invalides (rejected).
  - Production des DataFrames prêts au chargement.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict
from datetime import datetime

from src.config import (
    DATE_COLUMNS,
    VALID_ORDER_STATUSES,
    REJECTED_DIR,
    PROCESSED_DIR,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── Utilitaires génériques ─────────────────────────────────────────────────────

def _save_rejected(df_rejected: pd.DataFrame, dataset_name: str, reason: str) -> None:
    """Sauvegarde les enregistrements rejetés pour analyse ultérieure."""
    if df_rejected.empty:
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = REJECTED_DIR / f"{dataset_name}_{reason}_{timestamp}.csv"
    df_rejected.to_csv(out_path, index=False, encoding="utf-8")
    logger.warning(f"  → {len(df_rejected):,} rejets '{reason}' sauvegardés : {out_path.name}")


def _parse_dates(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """Convertit les colonnes de dates connues au format datetime."""
    date_cols = DATE_COLUMNS.get(dataset_name, [])
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


# ── Transformation : Orders ────────────────────────────────────────────────────

def transform_orders(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Nettoie et transforme le dataset orders.

    Règles appliquées :
    - Suppression des doublons sur order_id.
    - Conversion des colonnes date.
    - Rejet des lignes sans order_id ou customer_id.
    - Rejet des statuts invalides.
    - Calcul du délai de livraison (delivered - purchase).
    - Indicateur de livraison à temps.

    Args:
        df: DataFrame brut orders.

    Returns:
        Tuple (df_clean, df_rejected).
    """
    logger.info("[orders] Début de la transformation...")
    df = df.copy()
    rejected_frames = []

    # 1. Suppression des doublons
    dupes = df[df.duplicated(subset=["order_id"], keep="first")]
    if not dupes.empty:
        dupes["reject_reason"] = "duplicate_order_id"
        rejected_frames.append(dupes)
        df = df.drop_duplicates(subset=["order_id"], keep="first")
        logger.info(f"  Doublons supprimés : {len(dupes):,}")

    # 2. Rejet des lignes sans clés obligatoires
    mask_null_keys = df["order_id"].isnull() | df["customer_id"].isnull()
    if mask_null_keys.any():
        rejected = df[mask_null_keys].copy()
        rejected["reject_reason"] = "null_primary_key"
        rejected_frames.append(rejected)
        df = df[~mask_null_keys]
        logger.warning(f"  Rejets (clé nulle) : {len(rejected):,}")

    # 3. Conversion des dates
    df = _parse_dates(df, "orders")

    # 4. Rejet des statuts invalides
    mask_invalid_status = ~df["order_status"].isin(VALID_ORDER_STATUSES)
    if mask_invalid_status.any():
        rejected = df[mask_invalid_status].copy()
        rejected["reject_reason"] = "invalid_order_status"
        rejected_frames.append(rejected)
        df = df[~mask_invalid_status]
        logger.warning(f"  Rejets (statut invalide) : {len(rejected):,}")

    # 5. Calcul du délai de livraison (en jours)
    delivered_mask = df["order_delivered_customer_date"].notna() & df["order_purchase_timestamp"].notna()
    df.loc[delivered_mask, "delivery_days"] = (
        df.loc[delivered_mask, "order_delivered_customer_date"]
        - df.loc[delivered_mask, "order_purchase_timestamp"]
    ).dt.days

    # 6. Indicateur de livraison à temps (1 = à temps, 0 = en retard)
    on_time_mask = (
        df["order_delivered_customer_date"].notna()
        & df["order_estimated_delivery_date"].notna()
    )
    df.loc[on_time_mask, "is_on_time"] = (
        df.loc[on_time_mask, "order_delivered_customer_date"]
        <= df.loc[on_time_mask, "order_estimated_delivery_date"]
    ).astype(int)

    # 7. Calcul du retard en jours
    late_mask = on_time_mask & (df.get("is_on_time", pd.Series(dtype=float)) == 0)
    if late_mask.any():
        df.loc[late_mask, "delay_days"] = (
            df.loc[late_mask, "order_delivered_customer_date"]
            - df.loc[late_mask, "order_estimated_delivery_date"]
        ).dt.days

    # Consolidation des rejets
    df_rejected = pd.concat(rejected_frames, ignore_index=True) if rejected_frames else pd.DataFrame()
    _save_rejected(df_rejected, "orders", "transform")

    logger.info(f"[orders] Transformation terminée — {len(df):,} lignes valides, {len(df_rejected):,} rejets.")
    return df, df_rejected


# ── Transformation : Order Items ───────────────────────────────────────────────

def transform_order_items(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Nettoie et transforme le dataset order_items.

    Règles :
    - Rejet des lignes sans order_id ou product_id.
    - Rejet des lignes avec price ou freight_value négatif/nul.
    - Conversion de shipping_limit_date.
    """
    logger.info("[order_items] Début de la transformation...")
    df = df.copy()
    rejected_frames = []

    # 1. Clés obligatoires
    mask_null = df["order_id"].isnull() | df["product_id"].isnull() | df["seller_id"].isnull()
    if mask_null.any():
        r = df[mask_null].copy(); r["reject_reason"] = "null_key"
        rejected_frames.append(r); df = df[~mask_null]

    # 2. Valeurs numériques invalides
    mask_neg_price = df["price"] < 0
    if mask_neg_price.any():
        r = df[mask_neg_price].copy(); r["reject_reason"] = "negative_price"
        rejected_frames.append(r); df = df[~mask_neg_price]

    mask_neg_freight = df["freight_value"] < 0
    if mask_neg_freight.any():
        r = df[mask_neg_freight].copy(); r["reject_reason"] = "negative_freight"
        rejected_frames.append(r); df = df[~mask_neg_freight]

    # 3. Conversion date
    df = _parse_dates(df, "order_items")

    df_rejected = pd.concat(rejected_frames, ignore_index=True) if rejected_frames else pd.DataFrame()
    _save_rejected(df_rejected, "order_items", "transform")

    logger.info(f"[order_items] {len(df):,} lignes valides, {len(df_rejected):,} rejets.")
    return df, df_rejected


# ── Transformation : Customers ─────────────────────────────────────────────────

def transform_customers(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Nettoie le dataset customers."""
    logger.info("[customers] Début de la transformation...")
    df = df.copy()
    rejected_frames = []

    # Doublons sur customer_id
    dupes = df[df.duplicated(subset=["customer_id"], keep="first")]
    if not dupes.empty:
        d = dupes.copy(); d["reject_reason"] = "duplicate_customer_id"
        rejected_frames.append(d)
        df = df.drop_duplicates(subset=["customer_id"], keep="first")

    # Clé nulle
    mask_null = df["customer_id"].isnull()
    if mask_null.any():
        r = df[mask_null].copy(); r["reject_reason"] = "null_customer_id"
        rejected_frames.append(r); df = df[~mask_null]

    # Normalisation des champs texte
    for col in ["customer_city", "customer_state"]:
        if col in df.columns:
            df[col] = df[col].str.strip().str.lower()

    df_rejected = pd.concat(rejected_frames, ignore_index=True) if rejected_frames else pd.DataFrame()
    _save_rejected(df_rejected, "customers", "transform")
    logger.info(f"[customers] {len(df):,} lignes valides, {len(df_rejected):,} rejets.")
    return df, df_rejected


# ── Transformation : Products ──────────────────────────────────────────────────

def transform_products(
    df: pd.DataFrame,
    df_translations: pd.DataFrame = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Nettoie le dataset products et joint les traductions de catégories.
    
    Args:
        df:              DataFrame brut products.
        df_translations: DataFrame des traductions catégories (optionnel).
    """
    logger.info("[products] Début de la transformation...")
    df = df.copy()
    rejected_frames = []

    # Doublons
    dupes = df[df.duplicated(subset=["product_id"], keep="first")]
    if not dupes.empty:
        d = dupes.copy(); d["reject_reason"] = "duplicate_product_id"
        rejected_frames.append(d)
        df = df.drop_duplicates(subset=["product_id"], keep="first")

    # Clé nulle
    mask_null = df["product_id"].isnull()
    if mask_null.any():
        r = df[mask_null].copy(); r["reject_reason"] = "null_product_id"
        rejected_frames.append(r); df = df[~mask_null]

    # Jointure traductions
    if df_translations is not None and not df_translations.empty:
        df = df.merge(
            df_translations[["product_category_name", "product_category_name_english"]],
            on="product_category_name",
            how="left",
        )
        logger.info("  Traductions catégories jointes.")

    # Dimensions numériques (valeurs aberrantes → NULL documenté)
    for col in ["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df_rejected = pd.concat(rejected_frames, ignore_index=True) if rejected_frames else pd.DataFrame()
    _save_rejected(df_rejected, "products", "transform")
    logger.info(f"[products] {len(df):,} lignes valides, {len(df_rejected):,} rejets.")
    return df, df_rejected


# ── Transformation : Payments ──────────────────────────────────────────────────

def transform_payments(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Nettoie le dataset payments."""
    logger.info("[payments] Début de la transformation...")
    df = df.copy()
    rejected_frames = []

    mask_null = df["order_id"].isnull()
    if mask_null.any():
        r = df[mask_null].copy(); r["reject_reason"] = "null_order_id"
        rejected_frames.append(r); df = df[~mask_null]

    mask_neg = df["payment_value"] < 0
    if mask_neg.any():
        r = df[mask_neg].copy(); r["reject_reason"] = "negative_payment_value"
        rejected_frames.append(r); df = df[~mask_neg]

    df_rejected = pd.concat(rejected_frames, ignore_index=True) if rejected_frames else pd.DataFrame()
    _save_rejected(df_rejected, "payments", "transform")
    logger.info(f"[payments] {len(df):,} lignes valides, {len(df_rejected):,} rejets.")
    return df, df_rejected


# ── Transformation : Reviews ───────────────────────────────────────────────────

def transform_reviews(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Nettoie le dataset reviews."""
    logger.info("[reviews] Début de la transformation...")
    df = df.copy()
    rejected_frames = []

    # Doublons sur review_id
    dupes = df[df.duplicated(subset=["review_id"], keep="first")]
    if not dupes.empty:
        d = dupes.copy(); d["reject_reason"] = "duplicate_review_id"
        rejected_frames.append(d)
        df = df.drop_duplicates(subset=["review_id"], keep="first")

    # Score invalide (doit être entre 1 et 5)
    df["review_score"] = pd.to_numeric(df["review_score"], errors="coerce")
    mask_invalid_score = ~df["review_score"].isin([1, 2, 3, 4, 5])
    if mask_invalid_score.any():
        r = df[mask_invalid_score].copy(); r["reject_reason"] = "invalid_review_score"
        rejected_frames.append(r); df = df[~mask_invalid_score]

    df = _parse_dates(df, "reviews")

    df_rejected = pd.concat(rejected_frames, ignore_index=True) if rejected_frames else pd.DataFrame()
    _save_rejected(df_rejected, "reviews", "transform")
    logger.info(f"[reviews] {len(df):,} lignes valides, {len(df_rejected):,} rejets.")
    return df, df_rejected


# ── Transformation : Sellers ───────────────────────────────────────────────────

def transform_sellers(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Nettoie le dataset sellers."""
    logger.info("[sellers] Début de la transformation...")
    df = df.copy()
    rejected_frames = []

    dupes = df[df.duplicated(subset=["seller_id"], keep="first")]
    if not dupes.empty:
        d = dupes.copy(); d["reject_reason"] = "duplicate_seller_id"
        rejected_frames.append(d)
        df = df.drop_duplicates(subset=["seller_id"], keep="first")

    for col in ["seller_city", "seller_state"]:
        if col in df.columns:
            df[col] = df[col].str.strip().str.lower()

    df_rejected = pd.concat(rejected_frames, ignore_index=True) if rejected_frames else pd.DataFrame()
    _save_rejected(df_rejected, "sellers", "transform")
    logger.info(f"[sellers] {len(df):,} lignes valides, {len(df_rejected):,} rejets.")
    return df, df_rejected


# ── Orchestrateur global ───────────────────────────────────────────────────────

def transform_all(
    raw_data: Dict[str, pd.DataFrame],
) -> Dict[str, Tuple[pd.DataFrame, pd.DataFrame]]:
    """
    Applique toutes les transformations sur l'ensemble des datasets chargés.

    Args:
        raw_data: Dictionnaire {nom_dataset: DataFrame brut}.

    Returns:
        Dictionnaire {nom_dataset: (df_clean, df_rejected)}.
    """
    logger.info("=== Début des transformations ===")
    results = {}

    transform_map = {
        "orders":      transform_orders,
        "order_items": transform_order_items,
        "customers":   transform_customers,
        "payments":    transform_payments,
        "reviews":     transform_reviews,
        "sellers":     transform_sellers,
    }

    for dataset_name, transform_fn in transform_map.items():
        if dataset_name in raw_data:
            if dataset_name == "products":
                df_clean, df_rejected = transform_products(
                    raw_data["products"],
                    raw_data.get("translations"),
                )
            else:
                df_clean, df_rejected = transform_fn(raw_data[dataset_name])
            results[dataset_name] = (df_clean, df_rejected)
        else:
            logger.warning(f"Dataset '{dataset_name}' absent — transformation ignorée.")

    # Cas spécial : products avec translations
    if "products" in raw_data and "products" not in results:
        df_clean, df_rejected = transform_products(
            raw_data["products"],
            raw_data.get("translations"),
        )
        results["products"] = (df_clean, df_rejected)

    total_clean = sum(len(v[0]) for v in results.values())
    total_rejected = sum(len(v[1]) for v in results.values())
    logger.info(f"=== Transformations terminées — {total_clean:,} lignes valides, {total_rejected:,} rejets ===")

    return results
